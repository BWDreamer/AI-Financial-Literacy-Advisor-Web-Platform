from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal
import json
import math
from typing import Any


ONGOING = "ongoing"
ONE_OFF = "one_off"
ALLOWED_CASH_FLOW_KINDS = (ONGOING, ONE_OFF)
MIN_CASH_FLOW_KIND_CONFIDENCE = 0.70


CASH_FLOW_KIND_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "classifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "string"},
                    "cash_flow_kind": {
                        "type": "string",
                        "enum": list(ALLOWED_CASH_FLOW_KINDS),
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                },
                "required": [
                    "candidate_id",
                    "cash_flow_kind",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["classifications"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class CashFlowKindCandidate:
    candidate_id: str
    description: str
    amount: Decimal
    transaction_type: str
    source_line: str


@dataclass(frozen=True)
class CashFlowKindClassification:
    candidate_id: str
    cash_flow_kind: str
    confidence: float


CashFlowKindClassifier = Callable[
    [list[CashFlowKindCandidate]],
    Awaitable[list[CashFlowKindClassification]],
]


def build_cash_flow_kind_prompt(
    candidates: list[CashFlowKindCandidate],
) -> str:
    rows = [
        {
            "candidate_id": candidate.candidate_id,
            "description": candidate.description,
            "transaction_type": candidate.transaction_type,
            "source_line": candidate.source_line,
            "amount_from_backend": f"{candidate.amount:.2f}",
        }
        for candidate in candidates
    ]

    return "\n".join(
        [
            (
                "Classify extracted personal finance transactions as ongoing "
                "or one-off cash flow."
            ),
            (
                "The backend has already parsed each amount and transaction "
                "type. Treat them as authoritative and do not change, split, "
                "combine, add, or remove transactions."
            ),
            (
                "Use ongoing only when the description supports a normal "
                "income or expense expected to continue, such as salary, "
                "regular wages, rent, utilities, groceries, or subscriptions."
            ),
            (
                "Use one_off for bonuses, gifts, refunds, asset sales, isolated "
                "purchases, and freelance or project payments unless the text "
                "explicitly establishes that they are regular."
            ),
            (
                "When recurrence is uncertain, use one_off so an isolated "
                "transaction is never presented as sustainable monthly capacity."
            ),
            (
                "Return exactly one classification for every candidate, "
                "matching the supplied JSON Schema. Do not answer the user."
            ),
            "Transactions:",
            json.dumps(rows),
        ]
    )


def normalize_cash_flow_kind_payload(
    payload: dict[str, Any],
    candidates: list[CashFlowKindCandidate],
) -> list[CashFlowKindClassification]:
    candidate_ids = {
        candidate.candidate_id
        for candidate in candidates
    }
    rows = payload.get("classifications")
    if not isinstance(rows, list):
        return []

    classifications: list[CashFlowKindClassification] = []
    seen_ids: set[str] = set()

    for row in rows:
        if not isinstance(row, dict):
            continue

        candidate_id = str(row.get("candidate_id") or "")
        if candidate_id not in candidate_ids or candidate_id in seen_ids:
            continue

        cash_flow_kind = (
            str(row.get("cash_flow_kind") or ONE_OFF)
            .strip()
            .lower()
        )
        if cash_flow_kind not in ALLOWED_CASH_FLOW_KINDS:
            cash_flow_kind = ONE_OFF

        try:
            confidence = float(row.get("confidence"))
        except (TypeError, ValueError):
            confidence = 0.0
        if not math.isfinite(confidence):
            confidence = 0.0

        classifications.append(
            CashFlowKindClassification(
                candidate_id=candidate_id,
                cash_flow_kind=cash_flow_kind,
                confidence=max(0.0, min(confidence, 1.0)),
            )
        )
        seen_ids.add(candidate_id)

    return classifications


def selected_cash_flow_kinds(
    candidates: list[CashFlowKindCandidate],
    classifications: list[CashFlowKindClassification],
) -> dict[str, str]:
    classifications_by_id = {
        classification.candidate_id: classification
        for classification in classifications
    }

    selected: dict[str, str] = {}
    for candidate in candidates:
        classification = classifications_by_id.get(candidate.candidate_id)
        if (
            classification is None
            or classification.confidence
            < MIN_CASH_FLOW_KIND_CONFIDENCE
        ):
            selected[candidate.candidate_id] = ONE_OFF
            continue

        selected[candidate.candidate_id] = classification.cash_flow_kind

    return selected
