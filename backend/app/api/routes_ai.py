import re

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
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
from app.models.financial_rule import FinancialRule
from app.models.user import User
from app.repositories.rule_repository import get_financial_rule_by_id
from app.repositories.chat_repository import add_message, get_conversation
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
)
from app.services.ai_advisor_service import AIAdvisorService
from app.services.financial_rule_intents import (
    FINANCIAL_RULE_INTENT_RESPONSE_SCHEMA,
    build_financial_rule_intent_prompt,
    normalize_financial_rule_intent_payload,
)
from app.services.rule_lookup_service import (
    build_financial_rule_context_from_intent,
)

router = APIRouter()


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
    rule_context: str | None,
) -> str:
    if rule_context is None:
        return user_message

    return "\n\n".join(
        [
            rule_context,
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


@router.post(
    "/chat",
    response_model=AIChatResponse,
)
async def chat_with_advisor(
    request: AIChatRequest,
    _current_user: User = Depends(
        get_current_user
    ),
    advisor_service: AIAdvisorService = Depends(
        get_ai_advisor_service
    ),
    db: Session = Depends(get_db),
):
    """Return an educational reply from the configured LLM."""
    try:
        rule_context = None
        conversation = None
        if request.conversation_id is not None:
            conversation = get_conversation(
                db, _current_user.id, request.conversation_id
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
            intent_payload = await advisor_service.reply_json(
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

        message = _build_grounded_message(
            user_message=request.message,
            rule_context=rule_context,
        )
        answer = _plain_text_answer(
            await advisor_service.reply(message)
        )

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
