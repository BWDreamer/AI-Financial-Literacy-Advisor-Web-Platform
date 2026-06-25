from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.ai.dependencies import get_ai_advisor_service
from app.ai.exceptions import (
    LLMConfigurationError,
    LLMServiceError,
)
from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
)
from app.services.ai_advisor_service import AIAdvisorService

router = APIRouter()


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
    _current_user: User = Depends(
        get_current_user
    ),
    advisor_service: AIAdvisorService = Depends(
        get_ai_advisor_service
    ),
):
    """Return a basic educational reply from the configured LLM."""
    try:
        answer = await advisor_service.reply(
            request.message
        )
    except LLMConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The AI service is not configured. "
                "Set GEMINI_API_KEY on the backend."
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
