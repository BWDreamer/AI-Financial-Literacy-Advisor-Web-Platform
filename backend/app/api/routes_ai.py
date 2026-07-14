import re

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    status,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.ai.dependencies import get_ai_advisor_service
from app.ai.exceptions import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMServiceError,
)
from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.config import settings
from app.models.financial_rule import FinancialRule
from app.models.user import User
from app.repositories.rule_repository import get_financial_rule_by_id
from app.repositories.chat_repository import add_message, get_conversation
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
    AIPdfChatResponse,
)
from app.services.ai_advisor_service import AIAdvisorService
from app.services.memory_service import (
    build_memory_context,
    remember_from_message,
    retrieve_relevant_memories,
)
from app.services.pdf_asset_classifier import (
    ASSET_CLASSIFICATION_RESPONSE_SCHEMA,
    AssetCandidate,
    build_asset_classification_prompt,
    normalize_asset_classification_payload,
)
from app.services.pdf_financial_service import (
    AmbiguousTransactionCandidate,
    PdfExtractionError,
    build_pdf_ai_context,
    build_transaction_classification_prompt,
    imported_records_to_api,
    parse_transaction_classification_response,
    process_financial_pdf,
)
from app.services.financial_rule_intents import (
    FINANCIAL_RULE_INTENT_RESPONSE_SCHEMA,
    build_financial_rule_intent_prompt,
    normalize_financial_rule_intent_payload,
)
from app.services.rule_lookup_service import (
    build_financial_rule_context_from_intent,
)

router = APIRouter()
PDF_MODEL_CONTEXT = "pdf-financial-parser"


@router.get("/ping")
def ping_ai():
    return {
        "module": "ai",
        "status": "ok",
    }


def _build_selected_rule_context(rule: FinancialRule) -> str:
    return "\n".join(
        [
            (
                "Verified financial rule context from the structured "
                "rules knowledge base:"
            ),
            f"Rule value: {rule.rule_value}",
            f"Region: {rule.region}.",
            f"Category: {rule.category}.",
            f"Financial year: {rule.rule_year}.",
            f"Rule key: {rule.rule_key}.",
            (
                f"Source: {rule.source_name or 'Not provided'} "
                f"({rule.source_url or 'Not provided'})."
            ),
            (
                "When answering, use this verified rule context as "
                "the source of truth, include a brief rationale, "
                "cite the source, and keep the answer educational."
            ),
        ]
    )


def _build_grounded_message(
    *,
    user_message: str,
    memory_context: str | None,
    rule_context: str | None,
) -> str:
    context_sections = [
        context
        for context in (memory_context, rule_context)
        if context is not None
    ]

    if not context_sections:
        return user_message

    return "\n\n".join(
        context_sections
        + [
            "User question:",
            user_message,
        ]
    )


def _raise_llm_http_error(error: Exception) -> None:
    if isinstance(error, LLMConfigurationError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The AI service is not configured. "
                "Set GEMINI_API_KEY on the backend."
            ),
        ) from error

    if isinstance(error, LLMRateLimitError):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "The AI provider rate limit was reached. "
                "Please wait a moment and try again."
            ),
        ) from error

    if isinstance(error, LLMServiceError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The AI service could not generate a response. "
                "Please try again."
            ),
        ) from error


def _plain_text_answer(answer: str) -> str:
    cleaned_lines: list[str] = []

    for raw_line in answer.splitlines():
        line = raw_line.strip()

        if not line:
            if cleaned_lines and cleaned_lines[-1]:
                cleaned_lines.append("")
            continue

        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^\s*[-*+]\s+", "", line)
        line = re.sub(r"^\s*\d+[.)]\s+", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        line = line.replace("**", "")
        line = line.replace("__", "")
        line = line.replace("`", "")
        line = line.replace("*", "")

        if re.fullmatch(r"[-_]{3,}", line):
            continue

        if re.fullmatch(r"(?i)ai analysis[:：]?", line):
            continue

        line = re.sub(
            r"(?i)^ai analysis\s*[:：-]?\s*",
            "",
            line,
        ).strip()

        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def _validate_pdf_upload(file: UploadFile, content: bytes) -> None:
    filename = file.filename or "uploaded.pdf"
    content_type = (file.content_type or "").lower()
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported.",
        )

    if content_type and content_type not in {
        "application/pdf",
        "application/octet-stream",
    }:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported.",
        )

    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "The uploaded PDF is too large. "
                f"Maximum size is {settings.max_upload_size_mb} MB."
            ),
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF is empty.",
        )


async def _classify_pdf_transactions(
    advisor_service: AIAdvisorService,
    candidates: list[AmbiguousTransactionCandidate],
):
    response = await advisor_service.reply(
        build_transaction_classification_prompt(
            candidates,
        )
    )

    return parse_transaction_classification_response(
        response,
        candidates,
    )


async def _classify_pdf_assets(
    advisor_service: AIAdvisorService,
    candidates: list[AssetCandidate],
):
    payload = await advisor_service.reply_json(
        build_asset_classification_prompt(candidates),
        ASSET_CLASSIFICATION_RESPONSE_SCHEMA,
    )

    classifications = normalize_asset_classification_payload(
        payload,
        candidates,
    )
    if len(classifications) != len(candidates):
        raise LLMServiceError(
            "The AI provider returned incomplete PDF asset classifications."
        )

    return classifications


@router.post(
    "/chat",
    response_model=AIChatResponse,
)
async def chat_with_advisor(
    request: AIChatRequest,
    current_user: User = Depends(
        get_current_user
    ),
    advisor_service: AIAdvisorService = Depends(
        get_ai_advisor_service
    ),
    db: Session = Depends(get_db),
):
    """Return an educational reply from the configured LLM."""
    try:
        memory_context = None
        rule_context = None
        conversation = None
        if request.conversation_id is not None:
            conversation = get_conversation(
                db, current_user.id, request.conversation_id
            )
            if conversation is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation was not found.",
                )
        if request.rule_id is not None:
            rule = get_financial_rule_by_id(db, request.rule_id)
            if rule is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Financial rule was not found.",
                )
            rule_context = _build_selected_rule_context(rule)

        if conversation is not None:
            add_message(db, conversation, "user", request.message)

        if request.rule_id is None:
            reply_json = getattr(advisor_service, "reply_json", None)
            if reply_json is not None:
                intent_payload = await reply_json(
                    build_financial_rule_intent_prompt(
                        request.message,
                    ),
                    FINANCIAL_RULE_INTENT_RESPONSE_SCHEMA,
                )
                rule_intent = normalize_financial_rule_intent_payload(
                    intent_payload,
                )
                rule_context = build_financial_rule_context_from_intent(
                    db=db,
                    intent=rule_intent,
                )

        memory_context = build_memory_context(
            retrieve_relevant_memories(
                db,
                current_user.id,
                request.message,
            )
        )

        message = _build_grounded_message(
            user_message=request.message,
            memory_context=memory_context,
            rule_context=rule_context,
        )
        answer = _plain_text_answer(
            await advisor_service.reply(message)
        )

        remember_from_message(db, current_user.id, request.message)

        if conversation is not None:
            add_message(db, conversation, "assistant", answer)
    except (
        LLMConfigurationError,
        LLMRateLimitError,
        LLMServiceError,
    ) as error:
        _raise_llm_http_error(error)

    return AIChatResponse(
        answer=answer,
        model=advisor_service.model,
    )


@router.post(
    "/chat/pdf",
    response_model=AIPdfChatResponse,
)
async def chat_with_pdf_upload(
    message: str = Form(default=""),
    conversation_id: int | None = Form(default=None),
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    advisor_service: AIAdvisorService = Depends(
        get_ai_advisor_service
    ),
    db: Session = Depends(get_db),
):
    """Classify uploaded PDF assets and update HomePage financial data."""

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload at least one PDF file.",
        )

    conversation = None
    if conversation_id is not None:
        conversation = get_conversation(
            db,
            current_user.id,
            conversation_id,
        )
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation was not found.",
            )

    results = []
    for file in files:
        content = await file.read()
        _validate_pdf_upload(file, content)
        try:
            results.append(
                await process_financial_pdf(
                    db,
                    current_user.id,
                    filename=file.filename or "uploaded.pdf",
                    content=content,
                    classify_ambiguous_transactions=(
                        lambda candidates: _classify_pdf_transactions(
                            advisor_service,
                            candidates,
                        )
                    ),
                    classify_asset_candidates=(
                        lambda candidates: _classify_pdf_assets(
                            advisor_service,
                            candidates,
                        )
                    ),
                )
            )
        except PdfExtractionError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error
        except (
            LLMConfigurationError,
            LLMRateLimitError,
            LLMServiceError,
        ) as error:
            _raise_llm_http_error(error)

    user_message = (
        message.strip()
        or "Extract financial information from the uploaded PDF."
    )
    filenames = ", ".join(
        result.filename
        for result in results
    )

    if conversation is not None:
        add_message(
            db,
            conversation,
            "user",
            (
                f"Uploaded PDF(s): {filenames}\n"
                f"Request: {user_message}"
            ),
        )

    context = build_pdf_ai_context(
        user_message=user_message,
        results=results,
    )

    try:
        answer = _plain_text_answer(
            await advisor_service.reply(context)
        )
    except (
        LLMConfigurationError,
        LLMRateLimitError,
        LLMServiceError,
    ) as error:
        _raise_llm_http_error(error)

    if conversation is not None:
        add_message(
            db,
            conversation,
            "assistant",
            answer,
        )

    imported_records = [
        record
        for result in results
        for record in result.imported_records
    ]
    fallback_reason = "; ".join(
        result.fallback_reason
        for result in results
        if result.fallback_reason
    ) or None

    return AIPdfChatResponse(
        answer=answer,
        model=advisor_service.model or PDF_MODEL_CONTEXT,
        low_confidence=any(result.low_confidence for result in results),
        extracted_text_characters=sum(
            len(result.extracted_text)
            for result in results
        ),
        imported_records=imported_records_to_api(imported_records),
        fallback_reason=fallback_reason,
    )
