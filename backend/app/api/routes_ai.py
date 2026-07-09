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
from app.models.user import User
from app.repositories.rule_repository import get_financial_rule_by_id
from app.repositories.chat_repository import add_message, get_conversation
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
)
from app.services.ai_advisor_service import AIAdvisorService
from app.services.memory_service import (
    build_memory_context,
    remember_from_message,
    retrieve_relevant_memories,
)
from app.services.rule_lookup_service import (
    build_financial_rule_answer,
    build_financial_rule_context,
)

router = APIRouter()
RULE_KNOWLEDGE_BASE_MODEL = "rules-knowledge-base"


@router.get("/ping")
def ping_ai():
    return {
        "module": "ai",
        "status": "ok",
    }


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
    """Return a basic educational reply from the configured LLM."""
    try:
        message = request.message
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
            memory_context = build_memory_context(
                retrieve_relevant_memories(
                    db,
                    current_user.id,
                    request.message,
                )
            )
            message = (
                f"Verified financial rule:\n{rule.rule_value}\n"
                f"Source: {rule.source_name or 'Not provided'} - "
                f"{rule.source_url or 'Not provided'}\n\n"
                f"User question: {request.message}"
            )
            if memory_context is not None:
                message = (
                    f"{memory_context}\n\n"
                    f"{message}"
                )
        else:
            rule_answer = build_financial_rule_answer(
                db,
                request.message,
            )

            if rule_answer is not None:
                if conversation is not None:
                    add_message(
                        db,
                        conversation,
                        "user",
                        request.message,
                    )
                    add_message(
                        db,
                        conversation,
                        "assistant",
                        rule_answer,
                    )

                remember_from_message(db, current_user.id, request.message)

                return AIChatResponse(
                    answer=rule_answer,
                    model=RULE_KNOWLEDGE_BASE_MODEL,
                )

            memory_context = build_memory_context(
                retrieve_relevant_memories(
                    db,
                    current_user.id,
                    request.message,
                )
            )
            rule_context = build_financial_rule_context(
                db,
                request.message,
            )

            if memory_context is not None and rule_context is not None:
                message = (
                    f"{memory_context}\n\n"
                    f"{rule_context}\n\n"
                    "User question:\n"
                    f"{request.message}"
                )
            elif memory_context is not None:
                message = (
                    f"{memory_context}\n\n"
                    "User question:\n"
                    f"{request.message}"
                )
            elif rule_context is not None:
                message = (
                    f"{rule_context}\n\n"
                    "User question:\n"
                    f"{request.message}"
                )

        if conversation is not None:
            add_message(db, conversation, "user", request.message)

        answer = await advisor_service.reply(message)

        remember_from_message(db, current_user.id, request.message)

        if conversation is not None:
            add_message(db, conversation, "assistant", answer)
    except LLMConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The AI service is not configured. "
                "Set GEMINI_API_KEY on the backend."
            ),
        ) from error
    except LLMRateLimitError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "The AI provider rate limit was reached. "
                "Please wait a moment and try again."
            ),
        ) from error
    except LLMServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The AI service could not generate a response. "
                "Please try again."
            ),
        ) from error

    return AIChatResponse(
        answer=answer,
        model=advisor_service.model,
    )
