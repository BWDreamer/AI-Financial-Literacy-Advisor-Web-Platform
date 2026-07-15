from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
import logging
import json
from pathlib import Path
import re
from collections.abc import Awaitable, Callable
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.orm import Session

from app.repositories.financial_repository import (
    get_asset_by_type_and_name,
    get_cash_flow_by_identity,
    save_asset,
    save_cash_flow,
)
from app.schemas.financial import AssetRequest, CashFlowRequest
from app.services.pdf_asset_classifier import (
    ASSET_TYPES,
    AssetCandidate,
    AssetClassifier,
    ExtractedAsset,
    select_classified_assets,
)


logger = logging.getLogger(__name__)
MONEY_PRECISION = Decimal("0.01")
MAX_CONTEXT_TEXT_CHARS = 6000
MIN_TEXT_CONFIDENCE_CHARS = 30
OCR_RENDER_SCALE = 2
IMPORTED_CASH_BALANCE_NAME = "Imported cash balance"
IMPORTED_MONTHLY_INCOME_NAME = "Imported monthly income"
IMPORTED_MONTHLY_EXPENSES_NAME = "Imported monthly expenses"
MAX_ASSET_NAME_CHARS = 100

MONEY_PATTERN = re.compile(
    r"""
    (?<![\d.,])
    (?P<open>\()?
    (?P<prefix>[+-])?
    \s*(?:aud\s*)?\$?\s*
    (?P<whole>[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)
    (?:\.(?P<cents>[0-9]{1,2}))?
    \s*(?P<suffix>[+-])?
    \s*(?P<direction>cr|dr|credit|debit)?
    (?P<close>\))?
    (?![\d.,])
    """,
    re.IGNORECASE | re.VERBOSE,
)

FIELD_PATTERNS = {
    "cash_balance": (
        "cash savings",
        "current savings",
        "cash balance",
        "bank balance",
        "available balance",
        "closing balance",
        "account balance",
        "opening balance",
        "ending balance",
        "current balance",
    ),
    "monthly_income": (
        "monthly income",
        "total income",
        "income received",
        "regular income",
        "deposits",
        "total deposits",
        "deposit total",
        "credits",
        "total credits",
        "credit total",
    ),
    "monthly_expenses": (
        "monthly expenses",
        "total expenses",
        "total spending",
        "spending total",
        "total withdrawals",
        "withdrawals total",
        "total payments",
        "payments total",
        "debits",
        "total debits",
        "debit total",
        "bills paid",
        "regular expenses",
    ),
}

BALANCE_EXCLUSIONS = (
    "credit card",
    "loan",
    "debt",
    "amount owing",
    "minimum repayment",
)

TRANSACTION_EXCLUSION_PHRASES = tuple(
    phrase
    for phrases in FIELD_PATTERNS.values()
    for phrase in phrases
) + (
    "balance brought forward",
    "balance carried forward",
    "statement period",
)
TRANSACTION_TYPES = {
    "income",
    "expense",
    "transfer",
    "refund",
    "balance",
    "unknown",
}
TRANSACTION_DIRECTIONS = {
    "inflow",
    "outflow",
    "none",
}
MIN_TRANSACTION_CLASSIFICATION_CONFIDENCE = 0.55

OCR_NOISE_TRANSLATION = str.maketrans(
    {
        "\u00a0": " ",
        "\u200b": "",
        "\u2022": " ",
        "\u00b7": " ",
        "\ufeff": "",
        "\r": "\n",
    }
)


@dataclass(frozen=True)
class ExtractedFinancialFact:
    field: str
    amount: Decimal
    source_line: str


@dataclass(frozen=True)
class ExtractedTransaction:
    description: str
    amount: Decimal
    source_line: str
    transaction_type: str = "unknown"
    direction: str = "none"


@dataclass(frozen=True)
class AmbiguousTransactionCandidate:
    transaction_id: str
    description: str
    amount: Decimal
    source_line: str


@dataclass(frozen=True)
class TransactionClassification:
    transaction_id: str
    direction: str
    transaction_type: str
    confidence: float


AmbiguousTransactionClassifier = Callable[
    [list[AmbiguousTransactionCandidate]],
    Awaitable[list[TransactionClassification]],
]


@dataclass(frozen=True)
class ImportedFinancialRecord:
    record_type: str
    name: str
    amount: Decimal
    asset_type: str | None = None
    flow_type: str | None = None
    date: Date | None = None


@dataclass(frozen=True)
class PdfFinancialImportResult:
    filename: str
    extracted_text: str
    facts: list[ExtractedFinancialFact]
    transactions: list[ExtractedTransaction]
    assets: list[ExtractedAsset]
    imported_records: list[ImportedFinancialRecord]
    low_confidence: bool
    ocr_used: bool
    fallback_reason: str | None


class PdfExtractionError(ValueError):
    pass


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(
        MONEY_PRECISION,
        rounding=ROUND_HALF_UP,
    )


def _match_amount(match: re.Match[str]) -> Decimal:
    whole = match.group("whole").replace(",", "")
    cents = match.group("cents") or "00"

    return _round_money(
        Decimal(f"{whole}.{cents[:2].ljust(2, '0')}")
    )


def _match_sign(match: re.Match[str]) -> int | None:
    prefix = match.group("prefix")
    suffix = match.group("suffix")
    direction = (match.group("direction") or "").lower()
    is_parenthesized = bool(
        match.group("open") and match.group("close")
    )

    if prefix == "-" or suffix == "-" or direction in {
        "dr",
        "debit",
    } or is_parenthesized:
        return -1

    if prefix == "+" or suffix == "+" or direction in {
        "cr",
        "credit",
    }:
        return 1

    return None


def _parse_money_amount(text: str) -> Decimal | None:
    matches = list(MONEY_PATTERN.finditer(text))
    if not matches:
        return None

    match = matches[-1]

    return _match_amount(match)


def _parse_signed_money_amount(text: str) -> Decimal | None:
    matches = list(MONEY_PATTERN.finditer(text))

    for match in reversed(matches):
        sign = _match_sign(match)
        if sign is None:
            continue

        return _round_money(_match_amount(match) * sign)

    return None


def _matches_phrase(line: str, phrases: tuple[str, ...]) -> bool:
    normalized_line = line.lower()

    return any(
        re.search(
            rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])",
            normalized_line,
        )
        is not None
        for phrase in phrases
    )


def _field_priority(field: str, line: str) -> int:
    lowered_line = line.lower()

    if field == "cash_balance":
        if any(
            phrase in lowered_line
            for phrase in (
                "closing balance",
                "ending balance",
                "current balance",
                "available balance",
            )
        ):
            return 30

        if "opening balance" in lowered_line:
            return 10

        return 20

    if any(
        phrase in lowered_line
        for phrase in (
            "total",
            "monthly",
            "deposits",
            "credits",
            "debits",
        )
    ):
        return 20

    return 10


def _store_fact(
    facts_by_field: dict[str, tuple[int, ExtractedFinancialFact]],
    *,
    field: str,
    amount: Decimal,
    source_line: str,
) -> None:
    priority = _field_priority(field, source_line)
    current = facts_by_field.get(field)

    if current is not None and current[0] > priority:
        return

    facts_by_field[field] = (
        priority,
        ExtractedFinancialFact(
            field=field,
            amount=amount,
            source_line=source_line,
        ),
    )


def _is_summary_or_balance_line(line: str) -> bool:
    lowered_line = line.lower()

    return any(
        re.search(
            rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])",
            lowered_line,
        )
        is not None
        for phrase in TRANSACTION_EXCLUSION_PHRASES
    )


def _transaction_description(line: str) -> str:
    description = MONEY_PATTERN.sub("", line, count=1).strip()
    description = re.sub(r"\s{2,}", " ", description)
    description = description.strip(" :-+$")

    return description or "Imported transaction"


def _asset_description(line: str) -> str:
    matches = list(MONEY_PATTERN.finditer(line))
    if not matches:
        return line

    amount_match = matches[-1]
    description = " ".join(
        [
            line[: amount_match.start()].strip(),
            line[amount_match.end() :].strip(),
        ]
    ).strip()
    description = re.sub(r"\s{2,}", " ", description)
    description = description.strip(" :-+$")

    return description or "Imported asset"


def _normalize_extracted_text(text: str) -> str:
    normalized = text.translate(OCR_NOISE_TRANSLATION)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    return normalized.strip()


def _json_object_from_text(text: str) -> dict[str, Any]:
    stripped_text = text.strip()
    fenced_match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        stripped_text,
        re.IGNORECASE | re.DOTALL,
    )

    if fenced_match:
        stripped_text = fenced_match.group(1)
    elif "{" in stripped_text and "}" in stripped_text:
        stripped_text = stripped_text[
            stripped_text.find("{") : stripped_text.rfind("}") + 1
        ]

    parsed = json.loads(stripped_text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM transaction classification must be an object.")

    return parsed


def build_transaction_classification_prompt(
    candidates: list[AmbiguousTransactionCandidate],
) -> str:
    rows = [
        {
            "transaction_id": candidate.transaction_id,
            "description": candidate.description,
            "source_line": candidate.source_line,
            "amount_from_backend": f"{candidate.amount:.2f}",
        }
        for candidate in candidates
    ]

    return "\n".join(
        [
            "Classify ambiguous personal finance transaction lines.",
            "The backend has already extracted the amount. Do not change, infer, add, or remove amounts.",
            "Return JSON only. Do not explain.",
            "Allowed direction values: inflow, outflow, none.",
            "Allowed transaction_type values: income, expense, transfer, refund, balance, unknown.",
            "Use transfer for movements between the user's own accounts. Use balance for opening, closing, or carried-forward balance lines.",
            "Use unknown when the line cannot be classified confidently.",
            "Return this exact shape:",
            '{"transactions":[{"transaction_id":"txn_1","direction":"inflow","transaction_type":"income","confidence":0.96}]}',
            "Transactions:",
            json.dumps(rows),
        ]
    )


def parse_transaction_classification_response(
    response: str,
    candidates: list[AmbiguousTransactionCandidate],
) -> list[TransactionClassification]:
    candidate_ids = {
        candidate.transaction_id
        for candidate in candidates
    }

    try:
        payload = _json_object_from_text(response)
    except (json.JSONDecodeError, ValueError):
        return []

    rows = payload.get("transactions")
    if not isinstance(rows, list):
        return []

    classifications: list[TransactionClassification] = []
    seen_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue

        transaction_id = str(row.get("transaction_id") or "")
        if transaction_id not in candidate_ids or transaction_id in seen_ids:
            continue

        direction = str(row.get("direction") or "none").strip().lower()
        transaction_type = (
            str(row.get("transaction_type") or "unknown")
            .strip()
            .lower()
        )
        if direction not in TRANSACTION_DIRECTIONS:
            direction = "none"
        if transaction_type not in TRANSACTION_TYPES:
            transaction_type = "unknown"

        try:
            confidence = float(row.get("confidence"))
        except (TypeError, ValueError):
            confidence = 0.0

        classifications.append(
            TransactionClassification(
                transaction_id=transaction_id,
                direction=direction,
                transaction_type=transaction_type,
                confidence=max(0.0, min(confidence, 1.0)),
            )
        )
        seen_ids.add(transaction_id)

    return classifications


def _classified_ambiguous_transactions(
    candidates: list[AmbiguousTransactionCandidate],
    classifications: list[TransactionClassification],
) -> list[ExtractedTransaction]:
    classifications_by_id = {
        classification.transaction_id: classification
        for classification in classifications
    }
    transactions: list[ExtractedTransaction] = []

    for candidate in candidates:
        classification = classifications_by_id.get(
            candidate.transaction_id
        )
        if classification is None:
            continue

        if (
            classification.confidence
            < MIN_TRANSACTION_CLASSIFICATION_CONFIDENCE
        ):
            continue

        if classification.transaction_type in {
            "transfer",
            "balance",
            "unknown",
        }:
            continue

        if classification.direction == "inflow":
            amount = candidate.amount
        elif classification.direction == "outflow":
            amount = -candidate.amount
        else:
            continue

        transactions.append(
            ExtractedTransaction(
                description=candidate.description,
                amount=amount,
                source_line=candidate.source_line,
                transaction_type=classification.transaction_type,
                direction=classification.direction,
            )
        )

    return transactions


def extract_signed_transactions(
    text: str,
) -> list[ExtractedTransaction]:
    transactions: list[ExtractedTransaction] = []

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line or _is_summary_or_balance_line(line):
            continue

        amount = _parse_signed_money_amount(line)
        if amount is None or amount == 0:
            continue

        transactions.append(
            ExtractedTransaction(
                description=_transaction_description(line),
                amount=amount,
                source_line=line,
                transaction_type=(
                    "income" if amount > 0 else "expense"
                ),
                direction=(
                    "inflow" if amount > 0 else "outflow"
                ),
            )
        )

    return transactions


def extract_ambiguous_transaction_candidates(
    text: str,
) -> list[AmbiguousTransactionCandidate]:
    candidates: list[AmbiguousTransactionCandidate] = []

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line or _is_summary_or_balance_line(line):
            continue

        if _parse_signed_money_amount(line) is not None:
            continue

        amount = _parse_money_amount(line)
        if amount is None or amount == 0:
            continue

        candidates.append(
            AmbiguousTransactionCandidate(
                transaction_id=f"txn_{len(candidates) + 1}",
                description=_transaction_description(line),
                amount=amount,
                source_line=line,
            )
        )

    return candidates


def extract_asset_candidates(
    text: str,
) -> list[AssetCandidate]:
    candidates: list[AssetCandidate] = []
    seen_items: set[tuple[str, Decimal]] = set()

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue

        amount = _parse_money_amount(line)
        if amount is None or amount == 0:
            continue

        item_identity = (line, amount)
        if item_identity in seen_items:
            continue

        candidates.append(
            AssetCandidate(
                candidate_id=f"asset_{len(candidates) + 1}",
                description=_asset_description(line),
                amount=amount,
                source_line=line,
            )
        )
        seen_items.add(item_identity)

    return candidates


def _transaction_sources(
    transactions: list[ExtractedTransaction],
) -> str:
    preview = "; ".join(
        transaction.source_line
        for transaction in transactions[:5]
    )

    if len(transactions) > 5:
        preview = f"{preview}; and {len(transactions) - 5} more"

    return preview


def _facts_with_transaction_totals(
    facts: list[ExtractedFinancialFact],
    transactions: list[ExtractedTransaction],
) -> list[ExtractedFinancialFact]:
    facts_by_field = {
        fact.field: fact
        for fact in facts
    }
    calculated_facts = list(facts)
    income_transactions = [
        transaction
        for transaction in transactions
        if transaction.amount > 0
    ]
    expense_transactions = [
        transaction
        for transaction in transactions
        if transaction.amount < 0
    ]

    if (
        "monthly_income" not in facts_by_field
        and income_transactions
    ):
        income_total = sum(
            transaction.amount
            for transaction in income_transactions
        )
        calculated_facts.append(
            ExtractedFinancialFact(
                field="monthly_income",
                amount=_round_money(income_total),
                source_line=(
                    "Calculated from positive transactions: "
                    f"{_transaction_sources(income_transactions)}"
                ),
            )
        )

    if (
        "monthly_expenses" not in facts_by_field
        and expense_transactions
    ):
        expenses_total = sum(
            -transaction.amount
            for transaction in expense_transactions
        )
        calculated_facts.append(
            ExtractedFinancialFact(
                field="monthly_expenses",
                amount=_round_money(expenses_total),
                source_line=(
                    "Calculated from negative transactions: "
                    f"{_transaction_sources(expense_transactions)}"
                ),
            )
        )

    return calculated_facts


def extract_text_from_pdf_bytes(
    content: bytes,
) -> str:
    try:
        reader = PdfReader(BytesIO(content))
    except PdfReadError as error:
        raise PdfExtractionError(
            "The uploaded file could not be read as a PDF."
        ) from error

    if reader.is_encrypted:
        raise PdfExtractionError(
            "Encrypted PDFs are not supported for this demo."
        )

    page_text: list[str] = []
    for page in reader.pages:
        page_text.append(page.extract_text() or "")

    return _normalize_extracted_text("\n".join(page_text))


def extract_ocr_text_from_pdf_bytes(
    content: bytes,
) -> str:
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as error:
        logger.info(
            "PDF OCR dependencies are not installed: %s",
            error,
        )
        return ""

    try:
        document = fitz.open(
            stream=content,
            filetype="pdf",
        )
    except Exception as error:
        logger.warning(
            "Unable to render PDF pages for OCR: %s",
            error,
        )
        return ""

    ocr_pages: list[str] = []
    matrix = fitz.Matrix(
        OCR_RENDER_SCALE,
        OCR_RENDER_SCALE,
    )

    try:
        for page in document:
            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False,
            )
            image = Image.open(
                BytesIO(pixmap.tobytes("png"))
            )
            page_text = pytesseract.image_to_string(
                image,
                config="--psm 6",
            ).strip()

            if page_text:
                ocr_pages.append(page_text)
    except Exception as error:
        logger.warning(
            "OCR failed while reading PDF image content: %s",
            error,
        )
        return ""
    finally:
        document.close()

    return _normalize_extracted_text("\n".join(ocr_pages))


def extract_financial_facts(
    text: str,
) -> list[ExtractedFinancialFact]:
    facts_by_field: dict[str, tuple[int, ExtractedFinancialFact]] = {}

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue

        lowered_line = line.lower()
        amount = _parse_money_amount(line)
        if amount is None:
            continue

        if _matches_phrase(line, FIELD_PATTERNS["cash_balance"]) and not any(
            exclusion in lowered_line
            for exclusion in BALANCE_EXCLUSIONS
        ):
            _store_fact(
                facts_by_field,
                field="cash_balance",
                amount=amount,
                source_line=line,
            )
            continue

        if _matches_phrase(line, FIELD_PATTERNS["monthly_income"]):
            _store_fact(
                facts_by_field,
                field="monthly_income",
                amount=amount,
                source_line=line,
            )
            continue

        if _matches_phrase(line, FIELD_PATTERNS["monthly_expenses"]):
            _store_fact(
                facts_by_field,
                field="monthly_expenses",
                amount=amount,
                source_line=line,
            )

    return [
        fact
        for _, fact in facts_by_field.values()
    ]


def _upsert_asset(
    db: Session,
    user_id: int,
    *,
    name: str,
    asset_type: str,
    amount: Decimal,
) -> ImportedFinancialRecord:
    existing_asset = get_asset_by_type_and_name(
        db,
        user_id,
        asset_type,
        name,
    )
    asset = save_asset(
        db,
        user_id,
        AssetRequest(
            asset_type=asset_type,
            name=name,
            amount=amount,
        ),
        existing_asset,
    )

    return ImportedFinancialRecord(
        record_type="asset",
        asset_type=asset.asset_type,
        name=asset.name,
        amount=asset.amount,
    )


def _imported_asset_name(
    filename: str,
    asset_type: str,
) -> str:
    source_name = Path(filename).name.strip() or "uploaded.pdf"
    prefix = f"Imported {asset_type} from "
    available_source_chars = MAX_ASSET_NAME_CHARS - len(prefix)

    return f"{prefix}{source_name[:available_source_chars]}"


def import_classified_assets(
    db: Session,
    user_id: int,
    *,
    filename: str,
    assets: list[ExtractedAsset],
) -> list[ImportedFinancialRecord]:
    totals_by_type: dict[str, Decimal] = {}

    for asset in assets:
        current_total = totals_by_type.get(
            asset.asset_type,
            Decimal("0.00"),
        )
        totals_by_type[asset.asset_type] = _round_money(
            current_total + asset.amount
        )

    return [
        _upsert_asset(
            db,
            user_id,
            name=_imported_asset_name(filename, asset_type),
            asset_type=asset_type,
            amount=totals_by_type[asset_type],
        )
        for asset_type in ASSET_TYPES
        if asset_type in totals_by_type
    ]


def _upsert_cash_flow(
    db: Session,
    user_id: int,
    *,
    name: str,
    flow_type: str,
    amount: Decimal,
    flow_date: Date,
) -> ImportedFinancialRecord:
    existing_cash_flow = get_cash_flow_by_identity(
        db,
        user_id,
        flow_type,
        name,
        flow_date,
    )
    cash_flow = save_cash_flow(
        db,
        user_id,
        CashFlowRequest(
            flow_type=flow_type,
            name=name,
            amount=amount,
            date=flow_date,
        ),
        existing_cash_flow,
    )

    return ImportedFinancialRecord(
        record_type="cash_flow",
        flow_type=cash_flow.flow_type,
        name=cash_flow.name,
        amount=cash_flow.amount,
        date=cash_flow.date,
    )


def import_financial_facts(
    db: Session,
    user_id: int,
    facts: list[ExtractedFinancialFact],
    *,
    import_date: Date | None = None,
    include_cash_balance: bool = True,
) -> list[ImportedFinancialRecord]:
    flow_date = import_date or Date.today()
    imported_records: list[ImportedFinancialRecord] = []

    for fact in facts:
        if fact.field == "cash_balance":
            if include_cash_balance:
                imported_records.append(
                    _upsert_asset(
                        db,
                        user_id,
                        name=IMPORTED_CASH_BALANCE_NAME,
                        asset_type="cash",
                        amount=fact.amount,
                    )
                )
            continue

        if fact.field == "monthly_income":
            imported_records.append(
                _upsert_cash_flow(
                    db,
                    user_id,
                    name=IMPORTED_MONTHLY_INCOME_NAME,
                    flow_type="income",
                    amount=fact.amount,
                    flow_date=flow_date,
                )
            )
            continue

        if fact.field == "monthly_expenses":
            imported_records.append(
                _upsert_cash_flow(
                    db,
                    user_id,
                    name=IMPORTED_MONTHLY_EXPENSES_NAME,
                    flow_type="expense",
                    amount=fact.amount,
                    flow_date=flow_date,
                )
            )

    return imported_records


async def _extract_facts_and_transactions(
    text: str,
    classify_ambiguous_transactions: (
        AmbiguousTransactionClassifier | None
    ) = None,
    classify_asset_candidates: AssetClassifier | None = None,
) -> tuple[
    list[ExtractedFinancialFact],
    list[ExtractedTransaction],
    list[ExtractedAsset],
]:
    labelled_facts = extract_financial_facts(text)
    transactions = extract_signed_transactions(text)
    transaction_candidates = extract_ambiguous_transaction_candidates(text)
    asset_candidates = extract_asset_candidates(text)

    if (
        transaction_candidates
        and classify_ambiguous_transactions is not None
    ):
        classifications = await classify_ambiguous_transactions(
            transaction_candidates,
        )
        transactions.extend(
            _classified_ambiguous_transactions(
                transaction_candidates,
                classifications,
            )
        )

    assets: list[ExtractedAsset] = []
    if asset_candidates and classify_asset_candidates is not None:
        asset_classifications = await classify_asset_candidates(
            asset_candidates,
        )
        assets = select_classified_assets(
            asset_candidates,
            asset_classifications,
        )

    return (
        _facts_with_transaction_totals(
            labelled_facts,
            transactions,
        ),
        transactions,
        assets,
    )


def _combined_text(
    text: str,
    ocr_text: str,
) -> str:
    if text and ocr_text:
        return "\n\n".join(
            [
                text,
                "OCR text:",
                ocr_text,
            ]
        )

    return text or ocr_text


async def process_financial_pdf(
    db: Session,
    user_id: int,
    *,
    filename: str,
    content: bytes,
    classify_ambiguous_transactions: (
        AmbiguousTransactionClassifier | None
    ) = None,
    classify_asset_candidates: AssetClassifier | None = None,
) -> PdfFinancialImportResult:
    extracted_text = extract_text_from_pdf_bytes(content)
    facts, transactions, assets = await _extract_facts_and_transactions(
        extracted_text,
        classify_ambiguous_transactions,
        classify_asset_candidates,
    )
    ocr_used = False

    if not facts and not assets:
        ocr_text = extract_ocr_text_from_pdf_bytes(content)
        if ocr_text:
            ocr_used = True
            extracted_text = _combined_text(
                extracted_text,
                ocr_text,
            )
            (
                facts,
                transactions,
                assets,
            ) = await _extract_facts_and_transactions(
                extracted_text,
                classify_ambiguous_transactions,
                classify_asset_candidates,
            )

    low_confidence = (
        len(extracted_text) < MIN_TEXT_CONFIDENCE_CHARS
        or (not facts and not assets)
    )

    if low_confidence:
        fallback_reason = (
            "The PDF did not contain enough machine-readable financial "
            "text, OCR text, or supported financial fields."
        )
        imported_records: list[ImportedFinancialRecord] = []
    else:
        fallback_reason = None
        imported_records = []
        if classify_asset_candidates is not None:
            imported_records.extend(
                import_classified_assets(
                    db,
                    user_id,
                    filename=filename,
                    assets=assets,
                )
            )
        imported_records.extend(
            import_financial_facts(
                db,
                user_id,
                facts,
                include_cash_balance=(
                    classify_asset_candidates is None
                ),
            )
        )

    return PdfFinancialImportResult(
        filename=filename,
        extracted_text=extracted_text,
        facts=facts,
        transactions=transactions,
        assets=assets,
        imported_records=imported_records,
        low_confidence=low_confidence,
        ocr_used=ocr_used,
        fallback_reason=fallback_reason,
    )


def imported_records_to_api(
    records: list[ImportedFinancialRecord],
) -> list[dict]:
    return [
        {
            "record_type": record.record_type,
            "name": record.name,
            "amount": record.amount,
            "asset_type": record.asset_type,
            "flow_type": record.flow_type,
            "date": record.date.isoformat() if record.date else None,
        }
        for record in records
    ]


def build_pdf_ai_context(
    *,
    user_message: str,
    results: list[PdfFinancialImportResult],
) -> str:
    lines = [
        "The user uploaded PDF financial document(s) through the chat UI.",
        "The backend has already parsed the PDF text and either updated HomePage financial basics or selected fallback.",
        "Reply in English using plain text only. Do not use Markdown symbols, headings, bullet markers, bold markers, code backticks, or a visible AI analysis heading.",
        "Explain what was extracted, whether OCR was needed, and whether HomePage was updated.",
        f"User message: {user_message or 'Extract financial information from the uploaded PDF.'}",
        "",
    ]

    for result in results:
        lines.extend(
            [
                f"Document: {result.filename}",
                f"Extracted text characters: {len(result.extracted_text)}",
                f"OCR used: {result.ocr_used}",
                f"Low confidence: {result.low_confidence}",
            ]
        )

        if result.fallback_reason:
            lines.append(f"Fallback reason: {result.fallback_reason}")

        if result.facts:
            lines.append("Extracted financial facts:")
            for fact in result.facts:
                lines.append(
                    f"Fact {fact.field}: ${fact.amount:,.2f} "
                    f"from line '{fact.source_line}'"
                )

        if result.assets:
            lines.append("LLM-classified asset items:")
            for asset in result.assets:
                lines.append(
                    f"Asset {asset.asset_type}: ${asset.amount:,.2f} "
                    f"from line '{asset.source_line}'"
                )

        if result.transactions:
            income_total = sum(
                transaction.amount
                for transaction in result.transactions
                if transaction.amount > 0
            )
            expense_total = sum(
                -transaction.amount
                for transaction in result.transactions
                if transaction.amount < 0
            )
            lines.append(
                "Transaction summary: "
                f"income=${income_total:,.2f}; "
                f"expenses=${expense_total:,.2f}; "
                f"transaction_count={len(result.transactions)}"
            )
            lines.append("Transaction lines used:")
            for transaction in result.transactions[:8]:
                lines.append(
                    f"Transaction {transaction.description}: "
                    f"${transaction.amount:,.2f} "
                    f"type={transaction.transaction_type}; "
                    f"direction={transaction.direction}; "
                    f"from line '{transaction.source_line}'"
                )

        if result.imported_records:
            lines.append("HomePage financial basics updated:")
            for record in result.imported_records:
                details = [
                    f"type={record.record_type}",
                    f"name={record.name}",
                    f"amount=${record.amount:,.2f}",
                ]
                if record.asset_type:
                    details.append(f"asset_type={record.asset_type}")
                if record.flow_type:
                    details.append(f"flow_type={record.flow_type}")
                if record.date:
                    details.append(f"date={record.date.isoformat()}")
                lines.append(f"Record {'; '.join(details)}")

        clipped_text = result.extracted_text[:MAX_CONTEXT_TEXT_CHARS]
        if clipped_text:
            lines.append("Extracted PDF text excerpt:")
            lines.append(clipped_text)

        lines.append("")

    lines.append(
        "If confidence is low, ask the user to upload a clearer text or image PDF, or enter the values manually. Do not claim HomePage was updated unless imported records are listed."
    )

    return "\n".join(lines)
