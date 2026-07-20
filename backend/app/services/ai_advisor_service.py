from typing import Any, Protocol


class LLMProvider(Protocol):
    model: str

    async def generate_reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        """Generate one assistant reply for a user message."""

    async def generate_json(
        self,
        message: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate one JSON object using provider structured output."""


class AIAdvisorService:
    """Coordinate conversational responses from an LLM provider."""

    def __init__(
        self,
        provider: LLMProvider,
    ) -> None:
        self._provider = provider

    @property
    def model(self) -> str:
        return self._provider.model

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        return await self._provider.generate_reply(
            message,
            system_instruction=system_instruction,
        )

    async def reply_json(
        self,
        message: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._provider.generate_json(
            message,
            response_schema,
        )
