from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.ai import dependencies
from app.core.config import Settings, settings
from app.services.pdf_financial_service import (
    PdfFinancialImportResult,
    build_pdf_ai_context,
)


def test_runtime_tuning_values_are_parsed_from_configuration():
    configured = Settings(
        _env_file=None,
        llm_temperature="0.45",
        llm_structured_temperature="0.1",
        llm_retry_attempts="3",
        llm_retry_delay_seconds="0.25",
        chat_context_max_messages="20",
        chat_context_max_message_characters="1500",
        goal_context_max_messages="80",
        goal_context_max_message_characters="500",
        pdf_context_max_characters="7000",
        goal_priority_high_weight="4.5",
        goal_priority_medium_weight="2",
        goal_priority_low_weight="0.5",
    )

    assert configured.llm_temperature == 0.45
    assert configured.llm_structured_temperature == 0.1
    assert configured.llm_retry_attempts == 3
    assert configured.llm_retry_delay_seconds == 0.25
    assert configured.chat_context_max_messages == 20
    assert configured.goal_context_max_messages == 80
    assert configured.pdf_context_max_characters == 7000
    assert configured.goal_priority_high_weight == Decimal("4.5")
    assert configured.goal_priority_low_weight == Decimal("0.5")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("llm_temperature", 2.1),
        ("llm_structured_temperature", -0.1),
        ("llm_retry_attempts", -1),
        ("llm_retry_delay_seconds", -0.1),
        ("chat_context_max_messages", 0),
        ("chat_context_max_message_characters", 3),
        ("goal_context_max_messages", 0),
        ("goal_context_max_message_characters", 3),
        ("pdf_context_max_characters", 0),
        ("goal_priority_high_weight", 0),
        ("goal_priority_medium_weight", -1),
        ("goal_priority_low_weight", 0),
    ],
)
def test_runtime_tuning_rejects_invalid_values(field: str, value: Any):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


@pytest.mark.parametrize(
    ("provider_name", "provider_attribute"),
    [
        ("gemini", "GeminiProvider"),
        ("openrouter", "OpenRouterProvider"),
    ],
)
def test_provider_factory_passes_runtime_tuning(
    monkeypatch,
    provider_name: str,
    provider_attribute: str,
):
    captured: dict[str, Any] = {}

    def capture_provider(**kwargs):
        captured.update(kwargs)
        return kwargs

    monkeypatch.setattr(dependencies, provider_attribute, capture_provider)
    monkeypatch.setattr(settings, "llm_provider", provider_name)
    monkeypatch.setattr(settings, "llm_temperature", 0.55)
    monkeypatch.setattr(settings, "llm_structured_temperature", 0.05)
    monkeypatch.setattr(settings, "llm_retry_attempts", 4)
    monkeypatch.setattr(settings, "llm_retry_delay_seconds", 0.2)

    dependencies._build_llm_provider()

    assert captured["temperature"] == 0.55
    assert captured["structured_temperature"] == 0.05
    assert captured["retry_attempts"] == 4
    assert captured["retry_delay_seconds"] == 0.2


def test_pdf_context_uses_configured_character_limit(monkeypatch):
    monkeypatch.setattr(settings, "pdf_context_max_characters", 4)
    result = PdfFinancialImportResult(
        filename="statement.pdf",
        extracted_text="abcdefghij",
        facts=[],
        transactions=[],
        assets=[],
        imported_records=[],
        low_confidence=False,
        ocr_used=False,
        fallback_reason=None,
    )

    context = build_pdf_ai_context(
        user_message="Summarise it.",
        results=[result],
    )

    assert "Extracted PDF text excerpt:\nabcd" in context
    assert "abcde" not in context
