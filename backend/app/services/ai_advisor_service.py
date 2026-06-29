from typing import Protocol


class LLMProvider(Protocol):
    model: str

    async def generate_reply(
        self,
        message: str,
    ) -> str:
        """Generate one assistant reply for a user message."""


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
    ) -> str:
        return await self._provider.generate_reply(
            message
        )
