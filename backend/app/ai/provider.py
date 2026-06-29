import asyncio

import httpx
from google import genai
from google.genai import (
    errors,
    types,
)

from app.ai.exceptions import (
    LLMConfigurationError,
    LLMServiceError,
)
from app.ai.prompts import FINANCIAL_ADVISOR_INSTRUCTIONS


class GeminiProvider:
    """Generate advisor replies through the Gemini Developer API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self.model = model
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds
        self._client = genai.Client(
            api_key=self._api_key or "missing-api-key",
        )

    async def generate_reply(
        self,
        message: str,
    ) -> str:
        if not self._api_key:
            raise LLMConfigurationError(
                "The Gemini API key is not configured."
            )

        try:
            async with asyncio.timeout(
                self._timeout_seconds
            ):
                response = (
                    await self._client.aio.models.generate_content(
                        model=self.model,
                        contents=message, # Send the user-entered message to Gemini
                        config=types.GenerateContentConfig(
                            system_instruction=(
                                FINANCIAL_ADVISOR_INSTRUCTIONS
                            ),
                            temperature=0.3, # Controlling the Randomness of Responses: The lower the value, the more stable and conservative the response will be.
                        ),
                    )
                )
        except (
            TimeoutError,
            httpx.TransportError,
        ) as error:
            raise LLMServiceError(
                "The AI provider is temporarily unavailable."
            ) from error
        except errors.APIError as error:
            raise LLMServiceError(
                "The AI provider rejected the request."
            ) from error

        answer = (response.text or "").strip()

        if not answer:
            raise LLMServiceError(
                "The AI provider returned an empty response."
            )

        return answer
