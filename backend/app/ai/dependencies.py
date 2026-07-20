from functools import lru_cache

from app.ai.exceptions import LLMConfigurationError
from app.ai.provider import GeminiProvider, OpenRouterProvider
from app.core.config import settings
from app.services.ai_advisor_service import AIAdvisorService, LLMProvider


def _build_llm_provider() -> LLMProvider:
    if settings.llm_provider == "gemini":
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            structured_temperature=settings.llm_structured_temperature,
            retry_attempts=settings.llm_retry_attempts,
            retry_delay_seconds=settings.llm_retry_delay_seconds,
        )

    if settings.llm_provider == "openrouter":
        return OpenRouterProvider(
            api_key=settings.openrouter_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            structured_temperature=settings.llm_structured_temperature,
            retry_attempts=settings.llm_retry_attempts,
            retry_delay_seconds=settings.llm_retry_delay_seconds,
        )

    raise LLMConfigurationError(
        f"Unsupported LLM provider: {settings.llm_provider}"
    )


@lru_cache
def get_ai_advisor_service() -> AIAdvisorService:
    return AIAdvisorService(_build_llm_provider())
