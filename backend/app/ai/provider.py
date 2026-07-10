import asyncio
import json
import logging
from typing import Any

import httpx
from google import genai
from google.genai import (
    errors,
    types,
)

from app.ai.exceptions import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMServiceError,
)
from app.ai.prompts import FINANCIAL_ADVISOR_INSTRUCTIONS


logger = logging.getLogger(__name__)

TRANSIENT_PROVIDER_STATUS_CODES = {
    500,
    502,
    503,
    504,
}
DEFAULT_RETRY_ATTEMPTS = 1
DEFAULT_RETRY_DELAY_SECONDS = 0.75


def _api_error_status(error: errors.APIError) -> int | None:
    status = getattr(error, "code", None)

    if isinstance(status, int):
        return status

    status = getattr(error, "status", None)

    if isinstance(status, int):
        return status

    return None


class GeminiProvider:
    """Generate advisor replies through the Gemini Developer API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
    ) -> None:
        self.model = model
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds
        self._retry_attempts = max(0, retry_attempts)
        self._retry_delay_seconds = max(
            0.0,
            retry_delay_seconds,
        )
        self._client = genai.Client(
            api_key=self._api_key or "missing-api-key",
        )

    def _safe_error_message(self, error: Exception) -> str:
        message = str(error)

        if self._api_key:
            message = message.replace(
                self._api_key,
                "[REDACTED_API_KEY]",
            )

        return message[:500]

    async def _generate_once(
        self,
        message: str,
        *,
        response_schema: dict[str, Any] | None = None,
    ):
        config_kwargs: dict[str, Any] = {
            "system_instruction": FINANCIAL_ADVISOR_INSTRUCTIONS,
            "temperature": 0.3,
        }

        if response_schema is not None:
            config_kwargs.update(
                {
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                    "temperature": 0,
                }
            )

        async with asyncio.timeout(
            self._timeout_seconds
        ):
            return await self._client.aio.models.generate_content(
                model=self.model,
                contents=message,
                config=types.GenerateContentConfig(**config_kwargs),
            )

    async def _sleep_before_retry(
        self,
        attempt_index: int,
    ) -> None:
        if self._retry_delay_seconds == 0:
            return

        await asyncio.sleep(
            self._retry_delay_seconds * (2 ** attempt_index)
        )

    async def _generate_with_retries(
        self,
        message: str,
        *,
        response_schema: dict[str, Any] | None = None,
    ):
        if not self._api_key:
            raise LLMConfigurationError(
                "The Gemini API key is not configured."
            )

        max_attempts = self._retry_attempts + 1

        for attempt_index in range(max_attempts):
            try:
                response = await self._generate_once(
                    message,
                    response_schema=response_schema,
                )
                break
            except (
                TimeoutError,
                httpx.TransportError,
            ) as error:
                can_retry = attempt_index < self._retry_attempts
                logger.warning(
                    "Gemini transport failure on attempt %s/%s "
                    "(retry=%s): %s",
                    attempt_index + 1,
                    max_attempts,
                    can_retry,
                    self._safe_error_message(error),
                )

                if not can_retry:
                    raise LLMServiceError(
                        "The AI provider is temporarily unavailable."
                    ) from error

                await self._sleep_before_retry(attempt_index)
            except errors.APIError as error:
                status = _api_error_status(error)
                can_retry = (
                    status in TRANSIENT_PROVIDER_STATUS_CODES
                    and attempt_index < self._retry_attempts
                )
                logger.warning(
                    "Gemini API failure on attempt %s/%s "
                    "(status=%s, retry=%s): %s",
                    attempt_index + 1,
                    max_attempts,
                    status,
                    can_retry,
                    self._safe_error_message(error),
                )

                if can_retry:
                    await self._sleep_before_retry(attempt_index)
                    continue

                if status == 429:
                    raise LLMRateLimitError(
                        "The AI provider rate limit was reached."
                    ) from error

                raise LLMServiceError(
                    "The AI provider rejected the request."
                ) from error

        return response

    async def generate_reply(
        self,
        message: str,
    ) -> str:
        response = await self._generate_with_retries(message)
        answer = (response.text or "").strip()

        if not answer:
            raise LLMServiceError(
                "The AI provider returned an empty response."
            )

        return answer

    async def generate_json(
        self,
        message: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        response = await self._generate_with_retries(
            message,
            response_schema=response_schema,
        )
        parsed = getattr(response, "parsed", None)

        if isinstance(parsed, dict):
            return parsed

        answer = (response.text or "").strip()
        if not answer:
            raise LLMServiceError(
                "The AI provider returned an empty JSON response."
            )

        try:
            payload = json.loads(answer)
        except json.JSONDecodeError as error:
            raise LLMServiceError(
                "The AI provider returned invalid structured JSON."
            ) from error

        if not isinstance(payload, dict):
            raise LLMServiceError(
                "The AI provider returned a non-object JSON response."
            )

        return payload
