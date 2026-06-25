from functools import lru_cache

from app.ai.provider import GeminiProvider
from app.core.config import settings
from app.services.ai_advisor_service import AIAdvisorService


@lru_cache
def get_ai_advisor_service() -> AIAdvisorService:
    provider = GeminiProvider(
        api_key=settings.gemini_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )

    return AIAdvisorService(provider)
