import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

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
OPENROUTER_ERROR_TYPE_STATUS_CODES = {
    "rate_limit_exceeded": 429,
    "provider_unavailable": 502,
    "provider_overloaded": 503,
    "timeout": 504,
    "server": 500,
    "unmapped": 500,
}
OPENROUTER_API_BASE_URL = "https://openrouter.ai/api/v1"

ProviderResponse = TypeVar("ProviderResponse")


class _ProviderResponseError(Exception):
    """Represent a provider failure delivered inside a successful HTTP response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        error_type: str,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type


def _api_error_status(error: Exception) -> int | None:
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code

    status = getattr(error, "status_code", None)

    if isinstance(status, int):
        return status

    status = getattr(error, "code", None)

    if isinstance(status, int):
        return status

    status = getattr(error, "status", None)

    if isinstance(status, int):
        return status

    return None


def _api_error_type(error: Exception) -> str | None:
    error_type = getattr(error, "error_type", None)
    return error_type if isinstance(error_type, str) else None


def _safe_error_message(
    error: Exception,
    api_key: str,
) -> str:
    message = str(error)

    if api_key:
        message = message.replace(
            api_key,
            "[REDACTED_API_KEY]",
        )

    return message[:500]


async def _run_with_retries(
    operation: Callable[[], Awaitable[ProviderResponse]],
    *,
    provider_name: str,
    api_key: str,
    retry_attempts: int,
    retry_delay_seconds: float,
) -> ProviderResponse:
    max_attempts = retry_attempts + 1

    for attempt_index in range(max_attempts):
        try:
            return await operation()
        except (
            TimeoutError,
            httpx.TransportError,
        ) as error:
            can_retry = attempt_index < retry_attempts
            logger.warning(
                "%s transport failure on attempt %s/%s "
                "(retry=%s): %s",
                provider_name,
                attempt_index + 1,
                max_attempts,
                can_retry,
                _safe_error_message(error, api_key),
            )

            if not can_retry:
                raise LLMServiceError(
                    "The AI provider is temporarily unavailable."
                ) from error
        except (
            errors.APIError,
            httpx.HTTPStatusError,
            _ProviderResponseError,
        ) as error:
            status = _api_error_status(error)
            error_type = _api_error_type(error)
            can_retry = (
                status in TRANSIENT_PROVIDER_STATUS_CODES
                and attempt_index < retry_attempts
            )
            logger.warning(
                "%s API failure on attempt %s/%s "
                "(status=%s, error_type=%s, retry=%s): %s",
                provider_name,
                attempt_index + 1,
                max_attempts,
                status,
                error_type,
                can_retry,
                _safe_error_message(error, api_key),
            )

            if not can_retry:
                if status == 429:
                    raise LLMRateLimitError(
                        "The AI provider rate limit was reached."
                    ) from error

                raise LLMServiceError(
                    "The AI provider rejected the request."
                ) from error

        if retry_delay_seconds:
            await asyncio.sleep(
                retry_delay_seconds * (2 ** attempt_index)
            )

    raise LLMServiceError(
        "The AI provider is temporarily unavailable."
    )


class GeminiProvider:
    """Generate advisor replies through the Gemini Developer API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        temperature: float,
        structured_temperature: float,
        retry_attempts: int,
        retry_delay_seconds: float,
    ) -> None:
        self.model = model
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._structured_temperature = structured_temperature
        self._retry_attempts = max(0, retry_attempts)
        self._retry_delay_seconds = max(
            0.0,
            retry_delay_seconds,
        )
        self._client = genai.Client(
            api_key=self._api_key or "missing-api-key",
        )

    async def _generate_once(
        self,
        message: str,
        *,
        response_schema: dict[str, Any] | None = None,
    ):
        config_kwargs: dict[str, Any] = {
            "system_instruction": FINANCIAL_ADVISOR_INSTRUCTIONS,
            "temperature": self._temperature,
        }

        if response_schema is not None:
            config_kwargs.update(
                {
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                    "temperature": self._structured_temperature,
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

        return await _run_with_retries(
            lambda: self._generate_once(
                message,
                response_schema=response_schema,
            ),
            provider_name="Gemini",
            api_key=self._api_key,
            retry_attempts=self._retry_attempts,
            retry_delay_seconds=self._retry_delay_seconds,
        )

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

        return _parse_json_object(answer)


def _parse_json_object(answer: str) -> dict[str, Any]:
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


def _openrouter_embedded_error(
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    top_level_error = payload.get("error")
    if isinstance(top_level_error, dict):
        return top_level_error

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None

    choice_error = first_choice.get("error")
    return choice_error if isinstance(choice_error, dict) else None


def _openrouter_error_status_and_type(
    error_payload: dict[str, Any],
) -> tuple[int, str]:
    metadata = error_payload.get("metadata")
    error_type = (
        metadata.get("error_type")
        if isinstance(metadata, dict)
        else None
    )
    if not isinstance(error_type, str) or not error_type:
        error_type = "unknown"

    raw_status = error_payload.get("code")
    if isinstance(raw_status, int) and not isinstance(raw_status, bool):
        status = raw_status
    elif isinstance(raw_status, str) and raw_status.isdigit():
        status = int(raw_status)
    else:
        status = OPENROUTER_ERROR_TYPE_STATUS_CODES.get(error_type, 502)

    return status, error_type


class OpenRouterProvider:
    """Generate advisor replies through OpenRouter's chat API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        temperature: float,
        structured_temperature: float,
        retry_attempts: int,
        retry_delay_seconds: float,
    ) -> None:
        self.model = model
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._structured_temperature = structured_temperature
        self._retry_attempts = max(0, retry_attempts)
        self._retry_delay_seconds = max(
            0.0,
            retry_delay_seconds,
        )
        self._client = httpx.AsyncClient(
            base_url=OPENROUTER_API_BASE_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "X-OpenRouter-Title": "AI Financial Literacy Advisor",
            },
            timeout=timeout_seconds,
        )

    def _build_request_payload(
        self,
        message: str,
        response_schema: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": FINANCIAL_ADVISOR_INSTRUCTIONS,
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
            "temperature": self._temperature,
        }

        if response_schema is not None:
            payload.update(
                {
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "financial_advisor_response",
                            "strict": True,
                            "schema": response_schema,
                        },
                    },
                    "provider": {
                        "require_parameters": True,
                    },
                    "temperature": self._structured_temperature,
                }
            )

        return payload

    async def _generate_once(
        self,
        message: str,
        *,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        async with asyncio.timeout(self._timeout_seconds):
            response = await self._client.post(
                "/chat/completions",
                json=self._build_request_payload(
                    message,
                    response_schema=response_schema,
                )
            )
            response.raise_for_status()

        try:
            payload = response.json()
        except (TypeError, ValueError) as error:
            raise _ProviderResponseError(
                "OpenRouter returned a non-JSON response.",
                status_code=502,
                error_type="invalid_response",
            ) from error

        if not isinstance(payload, dict):
            raise _ProviderResponseError(
                "OpenRouter returned a non-object response.",
                status_code=502,
                error_type="invalid_response",
            )

        embedded_error = _openrouter_embedded_error(payload)
        if embedded_error is not None:
            status_code, error_type = _openrouter_error_status_and_type(
                embedded_error
            )
            raise _ProviderResponseError(
                "OpenRouter returned an embedded provider error.",
                status_code=status_code,
                error_type=error_type,
            )

        try:
            choice = payload["choices"][0]
            if not isinstance(choice, dict):
                raise TypeError("OpenRouter choice must be an object.")
            if choice.get("finish_reason") == "error":
                raise _ProviderResponseError(
                    "OpenRouter ended generation with an error.",
                    status_code=502,
                    error_type="provider_unavailable",
                )
            message_payload = choice["message"]
            if not isinstance(message_payload, dict):
                raise TypeError("OpenRouter message must be an object.")
            content = message_payload["content"]
        except (
            IndexError,
            KeyError,
            TypeError,
        ) as error:
            raise _ProviderResponseError(
                "OpenRouter returned an invalid response shape.",
                status_code=502,
                error_type="invalid_response",
            ) from error

        if not isinstance(content, str) or not content.strip():
            raise _ProviderResponseError(
                "OpenRouter returned an empty response.",
                status_code=502,
                error_type="empty_response",
            )

        return content.strip()

    async def _generate_json_once(
        self,
        message: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        answer = await self._generate_once(
            message,
            response_schema=response_schema,
        )
        try:
            return _parse_json_object(answer)
        except LLMServiceError as error:
            raise _ProviderResponseError(
                "OpenRouter returned invalid structured JSON.",
                status_code=502,
                error_type="invalid_structured_json",
            ) from error

    async def _run_operation_with_retries(
        self,
        operation: Callable[[], Awaitable[ProviderResponse]],
    ) -> ProviderResponse:
        if not self._api_key:
            raise LLMConfigurationError(
                "The OpenRouter API key is not configured."
            )

        return await _run_with_retries(
            operation,
            provider_name="OpenRouter",
            api_key=self._api_key,
            retry_attempts=self._retry_attempts,
            retry_delay_seconds=self._retry_delay_seconds,
        )

    async def _generate_with_retries(
        self,
        message: str,
        *,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        return await self._run_operation_with_retries(
            lambda: self._generate_once(
                message,
                response_schema=response_schema,
            )
        )

    async def generate_reply(
        self,
        message: str,
    ) -> str:
        return await self._generate_with_retries(message)

    async def generate_json(
        self,
        message: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._run_operation_with_retries(
            lambda: self._generate_json_once(
                message,
                response_schema,
            )
        )
