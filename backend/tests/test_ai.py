import asyncio
import json

import httpx

from app.ai.dependencies import get_ai_advisor_service
from app.ai.exceptions import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMServiceError,
)
from app.ai.prompts import FINANCIAL_ADVISOR_INSTRUCTIONS
from app.ai.provider import GeminiProvider
from app.main import app
from app.models.financial_rule import FinancialRule


class SuccessfulTestAdvisorService:
    model = "test-model"

    async def reply(
        self,
        message: str,
    ) -> str:
        return f"Educational response for: {message}"


class UnconfiguredTestAdvisorService:
    model = "test-model"

    async def reply(
        self,
        message: str,
    ) -> str:
        del message

        raise LLMConfigurationError(
            "Test provider is not configured."
        )


class RateLimitedTestAdvisorService:
    model = "test-model"

    async def reply(
        self,
        message: str,
    ) -> str:
        del message

        raise LLMRateLimitError(
            "Test provider rate limit."
        )


class FailingTestAdvisorService:
    model = "test-model"

    async def reply(
        self,
        message: str,
    ) -> str:
        del message

        raise LLMServiceError(
            "Test provider failure."
        )


class FakeGeminiResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class RetryThenSuccessModels:
    def __init__(self) -> None:
        self.calls = 0

    async def generate_content(self, **kwargs):
        del kwargs
        self.calls += 1

        if self.calls == 1:
            raise httpx.TransportError(
                "Temporary test transport failure."
            )

        return FakeGeminiResponse("Recovered response.")


class FakeGeminiAioClient:
    def __init__(self, models: RetryThenSuccessModels) -> None:
        self.models = models


class FakeGeminiClient:
    def __init__(self, models: RetryThenSuccessModels) -> None:
        self.aio = FakeGeminiAioClient(models)


ATO_TAX_RATES_URL = (
    "https://www.ato.gov.au/tax-rates-and-codes/"
    "tax-rates-australian-residents"
)
ATO_SUPER_GUARANTEE_URL = (
    "https://www.ato.gov.au/tax-rates-and-codes/"
    "key-superannuation-rates-and-thresholds/"
    "super-guarantee"
)
ATO_SUPER_CAPS_URL = (
    "https://www.ato.gov.au/tax-rates-and-codes/"
    "key-superannuation-rates-and-thresholds/"
    "contributions-caps"
)


def create_2025_2026_tax_rules(db_session) -> None:
    rules = [
        FinancialRule(
            region="Australia",
            category="tax",
            rule_year="2025-2026",
            rule_key="resident_income_tax_bracket_0_18200",
            rule_value=json.dumps(
                {
                    "bracket_label": "$0 – $18,200",
                    "income_from": 0,
                    "income_to": 18200,
                    "base_tax": 0,
                    "threshold": 0,
                    "marginal_rate": 0,
                    "formula": "Nil",
                    "medicare_levy_included": False,
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_TAX_RATES_URL,
        ),
        FinancialRule(
            region="Australia",
            category="tax",
            rule_year="2025-2026",
            rule_key="resident_income_tax_bracket_18201_45000",
            rule_value=json.dumps(
                {
                    "bracket_label": "$18,201 – $45,000",
                    "income_from": 18200.01,
                    "income_to": 45000,
                    "base_tax": 0,
                    "threshold": 18200,
                    "marginal_rate": 0.16,
                    "formula": "16c for each $1 over $18,200",
                    "medicare_levy_included": False,
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_TAX_RATES_URL,
        ),
        FinancialRule(
            region="Australia",
            category="tax",
            rule_year="2025-2026",
            rule_key="resident_income_tax_bracket_45001_135000",
            rule_value=json.dumps(
                {
                    "bracket_label": "$45,001 – $135,000",
                    "income_from": 45000.01,
                    "income_to": 135000,
                    "base_tax": 4288,
                    "threshold": 45000,
                    "marginal_rate": 0.30,
                    "formula": (
                        "$4,288 plus 30c for each $1 "
                        "over $45,000"
                    ),
                    "medicare_levy_included": False,
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_TAX_RATES_URL,
        ),
        FinancialRule(
            region="Australia",
            category="tax",
            rule_year="2025-2026",
            rule_key="resident_income_tax_bracket_135001_190000",
            rule_value=json.dumps(
                {
                    "bracket_label": "$135,001 – $190,000",
                    "income_from": 135000.01,
                    "income_to": 190000,
                    "base_tax": 31288,
                    "threshold": 135000,
                    "marginal_rate": 0.37,
                    "formula": (
                        "$31,288 plus 37c for each $1 "
                        "over $135,000"
                    ),
                    "medicare_levy_included": False,
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_TAX_RATES_URL,
        ),
        FinancialRule(
            region="Australia",
            category="tax",
            rule_year="2025-2026",
            rule_key="resident_income_tax_bracket_190001_over",
            rule_value=json.dumps(
                {
                    "bracket_label": "$190,001 and over",
                    "income_from": 190000.01,
                    "income_to": None,
                    "base_tax": 51638,
                    "threshold": 190000,
                    "marginal_rate": 0.45,
                    "formula": (
                        "$51,638 plus 45c for each $1 "
                        "over $190,000"
                    ),
                    "medicare_levy_included": False,
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_TAX_RATES_URL,
        ),
    ]
    db_session.add_all(rules)
    db_session.commit()


def create_current_superannuation_rules(db_session) -> None:
    rules = [
        FinancialRule(
            region="Australia",
            category="superannuation",
            rule_year="2025-2026",
            rule_key="employer_super_contribution",
            rule_value=json.dumps(
                {
                    "period": "1 July 2025 – 30 June 2026",
                    "general_super_guarantee_percent": 12.00,
                    "earnings_basis": "ordinary time earnings",
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_SUPER_GUARANTEE_URL,
        ),
        FinancialRule(
            region="Australia",
            category="superannuation",
            rule_year="2026-2027",
            rule_key="employer_super_contribution",
            rule_value=json.dumps(
                {
                    "period": "1 July 2026 – 30 June 2027",
                    "general_super_guarantee_percent": 12.00,
                    "earnings_basis": "qualifying earnings",
                    "payment_timing": "Payday Super from 1 July 2026",
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_SUPER_GUARANTEE_URL,
        ),
    ]
    db_session.add_all(rules)
    db_session.commit()


def create_super_contribution_cap_rules(db_session) -> None:
    rules = [
        FinancialRule(
            region="Australia",
            category="superannuation",
            rule_year="2025-2026",
            rule_key="concessional_contributions_cap",
            rule_value=json.dumps(
                {
                    "period": "1 July 2025 – 30 June 2026",
                    "cap_amount": 30000,
                    "cap_type": "concessional",
                    "applies_to": "all ages",
                    "includes": [
                        "employer contributions",
                        "salary sacrifice contributions",
                        (
                            "personal contributions claimed "
                            "as a tax deduction"
                        ),
                    ],
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_SUPER_CAPS_URL,
        ),
        FinancialRule(
            region="Australia",
            category="superannuation",
            rule_year="2026-2027",
            rule_key="concessional_contributions_cap",
            rule_value=json.dumps(
                {
                    "period": "1 July 2026 – 30 June 2027",
                    "cap_amount": 32500,
                    "cap_type": "concessional",
                    "applies_to": "all ages",
                    "includes": [
                        "employer contributions",
                        "salary sacrifice contributions",
                        (
                            "personal contributions claimed "
                            "as a tax deduction"
                        ),
                    ],
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_SUPER_CAPS_URL,
        ),
        FinancialRule(
            region="Australia",
            category="superannuation",
            rule_year="2025-2026",
            rule_key="non_concessional_contributions_cap",
            rule_value=json.dumps(
                {
                    "period": "1 July 2025 – 30 June 2026",
                    "cap_amount": 120000,
                    "cap_type": "non-concessional",
                    "applies_to": (
                        "personal contributions not claimed "
                        "as an income tax deduction"
                    ),
                    "important_condition": (
                        "The non-concessional cap can be nil "
                        "if total superannuation balance is "
                        "greater than or equal to the general "
                        "transfer balance cap at the end of "
                        "the previous financial year."
                    ),
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_SUPER_CAPS_URL,
        ),
        FinancialRule(
            region="Australia",
            category="superannuation",
            rule_year="2026-2027",
            rule_key="non_concessional_contributions_cap",
            rule_value=json.dumps(
                {
                    "period": "1 July 2026 – 30 June 2027",
                    "cap_amount": 130000,
                    "cap_type": "non-concessional",
                    "applies_to": (
                        "personal contributions not claimed "
                        "as an income tax deduction"
                    ),
                    "important_condition": (
                        "The non-concessional cap can be nil "
                        "if total superannuation balance is "
                        "greater than or equal to the general "
                        "transfer balance cap at the end of "
                        "the previous financial year."
                    ),
                }
            ),
            source_name="Australian Taxation Office",
            source_url=ATO_SUPER_CAPS_URL,
        ),
    ]
    db_session.add_all(rules)
    db_session.commit()


def test_gemini_provider_retries_transient_transport_error():
    models = RetryThenSuccessModels()
    provider = GeminiProvider(
        api_key="test-api-key",
        model="test-model",
        timeout_seconds=5,
        retry_attempts=1,
        retry_delay_seconds=0,
    )
    provider._client = FakeGeminiClient(models)

    answer = asyncio.run(
        provider.generate_reply(
            "What is budgeting?"
        )
    )

    assert answer == "Recovered response."
    assert models.calls == 2


def test_financial_advisor_prompt_requires_readable_lists():
    normalized_prompt = " ".join(
        FINANCIAL_ADVISOR_INSTRUCTIONS.split()
    )

    assert "Format responses for readability" in normalized_prompt
    assert "put each list item on its own separate line" in (
        normalized_prompt
    )
    assert "Do not compress multiple list items" in (
        normalized_prompt
    )


def create_authorization_headers(client) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "email": "advisor@example.com",
            "password": "Password123",
        },
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "advisor@example.com",
            "password": "Password123",
        },
    )

    access_token = login_response.json()[
        "access_token"
    ]

    return {
        "Authorization": f"Bearer {access_token}",
    }


def test_chat_requires_authentication(client):
    response = client.post(
        "/api/ai/chat",
        json={
            "message": "What is compound interest?",
        },
    )

    assert response.status_code == 401


def test_chat_returns_advisor_response(client):
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: SuccessfulTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(
                client
            ),
            json={
                "message": "  What is compound interest?  ",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json() == {
        "answer": (
            "Educational response for: "
            "What is compound interest?"
        ),
        "model": "test-model",
    }


def test_chat_rejects_blank_message(client):
    response = client.post(
        "/api/ai/chat",
        headers=create_authorization_headers(
            client
        ),
        json={
            "message": "   ",
        },
    )

    assert response.status_code == 422


def test_chat_reports_missing_api_configuration(client):
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: UnconfiguredTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(
                client
            ),
            json={
                "message": "What is compound interest?",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The AI service is not configured. "
        "Set GEMINI_API_KEY on the backend."
    )


def test_chat_reports_rate_limit_with_retry_guidance(client):
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: RateLimitedTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(
                client
            ),
            json={
                "message": "What is budgeting?",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "The AI provider rate limit was reached. "
        "Please wait a moment and try again."
    )


def test_chat_includes_selected_rule_context(client, db_session):
    rule = FinancialRule(
        region="Australia",
        category="tax",
        rule_year="2025-2026",
        rule_key="test_rule",
        rule_value="Verified test rule content.",
        source_name="Australian Taxation Office",
        source_url="https://www.ato.gov.au/",
    )
    db_session.add(rule)
    db_session.commit()

    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={"message": "Explain this rule", "rule_id": rule.id},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "Verified test rule content." in answer
    assert "Australian Taxation Office" in answer


def test_chat_automatically_injects_current_tax_table_context(
    client,
    db_session,
):
    create_2025_2026_tax_rules(db_session)
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: RateLimitedTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": "查询今年澳大利亚悉尼的税率。",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "rules-knowledge-base"
    answer = response.json()["answer"]
    assert "2025-2026" in answer
    assert "16c for each $1 over $18,200" in answer
    assert "Sydney/NSW does not use a separate" in answer
    assert ATO_TAX_RATES_URL in answer


def test_chat_automatically_injects_current_tax_bracket_context(
    client,
    db_session,
):
    create_2025_2026_tax_rules(db_session)
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: RateLimitedTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": "我的年薪是80,000澳元，今年要交多少税？",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "rules-knowledge-base"
    answer = response.json()["answer"]
    assert "2025-2026" in answer
    assert "taxable income $80,000.00 falls in" in answer
    assert "Marginal rate: 30%" in answer
    assert "$14,788.00" in answer
    assert ATO_TAX_RATES_URL in answer


def test_chat_warns_when_requested_tax_year_is_not_available(
    client,
    db_session,
):
    create_2025_2026_tax_rules(db_session)
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: RateLimitedTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": "查询2022年澳大利亚悉尼的税率。",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "rules-knowledge-base"
    answer = response.json()["answer"]
    assert "does not contain resident income tax rates" in answer
    assert "2021-2022" in answer
    assert "should not infer a specific rate from model memory" in answer
    assert "19c for each $1 over $18,200" not in answer


def test_chat_automatically_injects_payday_super_context(
    client,
    db_session,
):
    create_current_superannuation_rules(db_session)
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: RateLimitedTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": "2026年7月1日后雇主养老金比例是多少？",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "rules-knowledge-base"
    answer = response.json()["answer"]
    assert "2026-2027" in answer
    assert "General super guarantee rate: 12%" in answer
    assert "qualifying earnings" in answer
    assert "Payday Super from 1 July 2026" in answer
    assert ATO_SUPER_GUARANTEE_URL in answer


def test_chat_automatically_injects_super_contribution_cap_context(
    client,
    db_session,
):
    create_super_contribution_cap_rules(db_session)
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: RateLimitedTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": (
                    "2026-27 年我能额外存多少 super？"
                    " concessional 和 non-concessional cap 是多少？"
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "rules-knowledge-base"
    answer = response.json()["answer"]
    assert "2026-2027" in answer
    assert "Concessional contributions cap: $32,500" in answer
    assert "Non-Concessional contributions cap: $130,000" in answer
    assert "salary sacrifice contributions" in answer
    assert "The non-concessional cap can be nil" in answer
    assert ATO_SUPER_CAPS_URL in answer


def test_chat_summarizes_supported_rule_years(
    client,
    db_session,
):
    create_2025_2026_tax_rules(db_session)
    create_current_superannuation_rules(db_session)
    create_super_contribution_cap_rules(db_session)
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: RateLimitedTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": "你的规则知识库更新到哪一年？",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "rules-knowledge-base"
    answer = response.json()["answer"]
    assert "2025-2026" in answer
    assert "2026-2027" in answer
    assert "super contribution cap rules" in answer
    assert "2021-2022" not in answer
    assert "2022-2023" not in answer


def test_chat_rejects_missing_selected_rule(client):
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: SuccessfulTestAdvisorService()
    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={"message": "Explain this rule", "rule_id": 99999},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 404


def test_chat_saves_messages_to_selected_conversation(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations", headers=headers, json={}
    ).json()["conversation_id"]
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: SuccessfulTestAdvisorService()
    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "What is saving?",
                "conversation_id": conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    detail = client.get(
        f"/api/chat/conversations/{conversation_id}", headers=headers
    ).json()
    assert [message["role"] for message in detail["messages"]] == [
        "user",
        "assistant",
    ]


def test_chat_preserves_user_message_when_ai_generation_fails(
    client,
):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: FailingTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "Please explain emergency funds.",
                "conversation_id": conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 502

    detail = client.get(
        f"/api/chat/conversations/{conversation_id}",
        headers=headers,
    ).json()
    assert [message["role"] for message in detail["messages"]] == [
        "user",
    ]
    assert detail["messages"][0]["content"] == (
        "Please explain emergency funds."
    )
