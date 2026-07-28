import asyncio
import json
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

import httpx
import pytest
from reportlab.pdfgen import canvas

from app.ai.dependencies import get_ai_advisor_service
from app.ai.exceptions import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMServiceError,
)
from app.ai.prompts import (
    FINANCIAL_ADVISOR_INSTRUCTIONS,
    build_advisory_topic_instructions,
)
from app.ai.provider import GeminiProvider, OpenRouterProvider
from app.main import app
from tests.helpers import register_verified_user
from app.models.advisory_settings import AdvisorySettings
from app.models.financial_rule import FinancialRule
from app.services import (
    pdf_asset_classifier,
    pdf_cash_flow_classifier,
    pdf_financial_service,
)


class SuccessfulTestAdvisorService:
    model = "test-model"

    def __init__(self) -> None:
        self.messages: list[str] = []
        self.system_instructions: list[str | None] = []
        self.rule_classification_messages: list[str] = []
        self.transaction_classification_messages: list[str] = []
        self.cash_flow_kind_classification_messages: list[str] = []
        self.asset_classification_messages: list[str] = []

    def _rule_classification(self, message: str) -> dict:
        user_question = message.rsplit(
            "User question:",
            maxsplit=1,
        )[-1]
        lowered_message = user_question.lower()

        if "which years" in lowered_message:
            intent = "knowledge_base_status"
            rule_year = None
            taxable_income = None
        elif (
            "contribution cap" in lowered_message
            or "contribution caps" in lowered_message
        ):
            intent = "super_contribution_caps"
            rule_year = (
                "2026-2027"
                if "2026" in lowered_message
                else None
            )
            taxable_income = None
        elif (
            "super guarantee" in lowered_message
            or "employer super" in lowered_message
        ):
            intent = "employer_super"
            rule_year = (
                "2026-2027"
                if "2026" in lowered_message
                else None
            )
            taxable_income = None
        elif (
            "taxable income" in lowered_message
            or "how much income tax" in lowered_message
            or "goes to the government" in lowered_message
        ):
            intent = "tax_calculation"
            rule_year = None
            taxable_income = 80000
        elif "tax rate" in lowered_message or "tax rates" in lowered_message:
            intent = "tax_brackets"
            rule_year = (
                "2021-2022"
                if "2022" in lowered_message
                else None
            )
            taxable_income = None
        else:
            intent = "out_of_scope"
            rule_year = None
            taxable_income = None

        return {
            "intent": intent,
            "rule_year": rule_year,
            "taxable_income": taxable_income,
            "confidence": 0.97,
        }

    def _transaction_classification(self, message: str) -> dict:
        rows = []

        if "School Scholarship" in message:
            rows.append(
                {
                    "transaction_id": "txn_1",
                    "direction": "inflow",
                    "transaction_type": "income",
                    "confidence": 0.96,
                }
            )

        if "Woolworths 120" in message:
            rows.extend(
                [
                    {
                        "transaction_id": "txn_1",
                        "direction": "inflow",
                        "transaction_type": "income",
                        "confidence": 0.96,
                    },
                    {
                        "transaction_id": "txn_2",
                        "direction": "outflow",
                        "transaction_type": "expense",
                        "confidence": 0.95,
                    },
                    {
                        "transaction_id": "txn_3",
                        "direction": "none",
                        "transaction_type": "transfer",
                        "confidence": 0.92,
                    },
                ]
            )

        return {
            "transactions": rows,
        }

    def _asset_classification(self, message: str) -> dict:
        encoded_rows = message.split(
            "Monetary items:\n",
            maxsplit=1,
        )[1]
        rows = json.loads(encoded_rows)
        classifications = []

        for row in rows:
            source_line = row["source_line"].lower()

            if (
                "cash savings" in source_line
                or "opening balance" in source_line
                or "money transfers from dad" in source_line
                or "payroll" in source_line
            ):
                classification = "cash"
            elif "mercedes-benz" in source_line:
                classification = "vehicle"
            elif "stock hit limit up" in source_line:
                classification = "stocks"
            else:
                classification = "not_asset"

            classifications.append(
                {
                    "candidate_id": row["candidate_id"],
                    "classification": classification,
                    "confidence": 0.96,
                }
            )

        return {
            "classifications": classifications,
        }

    def _cash_flow_kind_classification(self, message: str) -> dict:
        encoded_rows = message.split(
            "Transactions:\n",
            maxsplit=1,
        )[1]
        rows = json.loads(encoded_rows)
        ongoing_terms = (
            "salary",
            "wages",
            "rent",
            "woolworths",
            "electricity",
            "utilities",
            "subscription",
        )

        return {
            "classifications": [
                {
                    "candidate_id": row["candidate_id"],
                    "cash_flow_kind": (
                        "ongoing"
                        if any(
                            term in row["description"].lower()
                            for term in ongoing_terms
                        )
                        else "one_off"
                    ),
                    "confidence": 0.96,
                }
                for row in rows
            ],
        }

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        if message.startswith(
            "Classify the user's Australian personal finance rule question."
        ):
            self.rule_classification_messages.append(message)
            return json.dumps(
                self._rule_classification(message)
            )

        if message.startswith(
            "Classify ambiguous personal finance transaction lines."
        ):
            self.transaction_classification_messages.append(message)
            return json.dumps(
                self._transaction_classification(message)
            )

        self.messages.append(message)
        self.system_instructions.append(system_instruction)

        return f"Educational response for: {message}"

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del response_schema

        if message.startswith(
            "Classify the user's Australian personal finance "
            "rule lookup request."
        ):
            self.rule_classification_messages.append(message)
            return self._rule_classification(message)

        if message.startswith(
            "Classify extracted personal finance transactions as ongoing "
            "or one-off cash flow."
        ):
            self.cash_flow_kind_classification_messages.append(message)
            return self._cash_flow_kind_classification(message)

        if message.startswith(
            "Classify monetary items from a financial PDF into "
            "asset categories."
        ):
            self.asset_classification_messages.append(message)
            return self._asset_classification(message)

        return {
            "intent": "out_of_scope",
            "rule_year": None,
            "taxable_income": None,
            "confidence": 0.0,
        }


class SuccessfulPdfAdvisorService(SuccessfulTestAdvisorService):
    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        if message.startswith("Classify "):
            return await super().reply(
                message,
                system_instruction=system_instruction,
            )

        self.messages.append(message)
        self.system_instructions.append(system_instruction)

        return f"Financial document response for: {message}"


class ZeroMonthlyContributionGoalAdvisorService(
    SuccessfulTestAdvisorService
):
    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        if message.startswith(
            "Extract and complete the user's goal-planning state."
        ):
            return {
                "goal_count": 1,
                "goals": [
                    {
                        "category": "general_saving",
                        "goal_title": "Bicycle",
                        "target_amount": 1000,
                        "deadline": (
                            date.today() + timedelta(days=365)
                        ).isoformat(),
                        "current_amount": 0,
                        "monthly_contribution": 0,
                        "priority": "Low",
                    }
                ],
                "recommendation_status": "needs_recommendation",
            }

        return await super().reply_json(
            message,
            response_schema,
        )


class MarkdownTestAdvisorService:
    model = "test-model"

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del message, response_schema

        return {
            "intent": "out_of_scope",
            "rule_year": None,
            "taxable_income": None,
            "confidence": 0.0,
        }

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        del message, system_instruction

        return (
            "### AI analysis\n"
            "* **Cash balance:** $12,500\n"
            "`HomePage` was updated."
        )


class UnconfiguredTestAdvisorService:
    model = "test-model"

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del message, response_schema

        raise LLMConfigurationError(
            "Test provider is not configured."
        )

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        del message, system_instruction

        raise LLMConfigurationError(
            "Test provider is not configured."
        )


class RateLimitedTestAdvisorService:
    model = "test-model"

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del message, response_schema

        raise LLMRateLimitError(
            "Test provider rate limit."
        )

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        del message, system_instruction

        raise LLMRateLimitError(
            "Test provider rate limit."
        )


class FailingTestAdvisorService:
    model = "test-model"

    async def reply_json(
        self,
        message: str,
        response_schema: dict,
    ) -> dict:
        del message, response_schema

        raise LLMServiceError(
            "Test provider failure."
        )

    async def reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ) -> str:
        del message, system_instruction

        raise LLMServiceError(
            "Test provider failure."
        )


class StreamingTestAdvisorService(SuccessfulTestAdvisorService):
    async def stream_reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ):
        self.messages.append(message)
        self.system_instructions.append(system_instruction)
        yield "Streamed **financial "
        yield "guidance**."


class FailingStreamingTestAdvisorService(SuccessfulTestAdvisorService):
    async def stream_reply(
        self,
        message: str,
        system_instruction: str | None = None,
    ):
        self.messages.append(message)
        self.system_instructions.append(system_instruction)
        yield "Partial response."
        raise LLMServiceError("Test streaming provider failure.")


class FakeGeminiResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class RetryThenSuccessModels:
    def __init__(self) -> None:
        self.calls = 0
        self.requests: list[dict] = []

    async def generate_content(self, **kwargs):
        self.requests.append(kwargs)
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


class StreamingGeminiModels:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def generate_content_stream(self, **kwargs):
        self.requests.append(kwargs)

        async def responses():
            yield FakeGeminiResponse("Gemini ")
            yield FakeGeminiResponse("stream.")

        return responses()


class FakeOpenRouterResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class RecordingOpenRouterClient:
    def __init__(self, response_payloads: dict | list[dict]) -> None:
        self.response_payloads = (
            response_payloads
            if isinstance(response_payloads, list)
            else [response_payloads]
        )
        self.requests: list[tuple[str, dict]] = []

    async def post(self, path: str, *, json: dict):
        response_index = min(
            len(self.requests),
            len(self.response_payloads) - 1,
        )
        self.requests.append((path, json))
        return FakeOpenRouterResponse(
            self.response_payloads[response_index]
        )


class FakeOpenRouterStreamResponse:
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    def raise_for_status(self) -> None:
        return None

    async def aiter_lines(self):
        for line in self.lines:
            yield line


class RecordingStreamingOpenRouterClient:
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.requests: list[tuple[str, str, dict]] = []

    def stream(self, method: str, path: str, *, json: dict):
        self.requests.append((method, path, json))
        return FakeOpenRouterStreamResponse(self.lines)


def create_test_openrouter_provider(
    client: RecordingOpenRouterClient,
    retry_attempts: int = 1,
) -> OpenRouterProvider:
    provider = OpenRouterProvider(
        api_key="test-api-key",
        model="google/gemini-2.5-flash",
        timeout_seconds=5,
        temperature=0.65,
        structured_temperature=0.05,
        retry_attempts=retry_attempts,
        retry_delay_seconds=0,
    )
    provider._client = client
    return provider


TAX_RATES_SOURCE_URL = (
    "https://www.legislation.gov.au/"
    "C2025A00028/asmade"
)
ATO_SUPER_GUARANTEE_URL = (
    "https://www.ato.gov.au/businesses-and-organisations/"
    "super-for-employers/about-payday-super"
)
ATO_SUPER_CAPS_URL = (
    "https://www.ato.gov.au/tax-rates-and-codes/"
    "key-superannuation-rates-and-thresholds/"
    "contributions-caps"
)


def create_2026_2027_tax_rules(db_session) -> None:
    rules = [
        FinancialRule(
            region="Australia",
            category="tax",
            rule_year="2026-2027",
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
            source_name=(
                "Australian Government – Federal Register "
                "of Legislation"
            ),
            source_url=TAX_RATES_SOURCE_URL,
        ),
        FinancialRule(
            region="Australia",
            category="tax",
            rule_year="2026-2027",
            rule_key="resident_income_tax_bracket_18201_45000",
            rule_value=json.dumps(
                {
                    "bracket_label": "$18,201 – $45,000",
                    "income_from": 18200.01,
                    "income_to": 45000,
                    "base_tax": 0,
                    "threshold": 18200,
                    "marginal_rate": 0.15,
                    "formula": "15c for each $1 over $18,200",
                    "medicare_levy_included": False,
                }
            ),
            source_name=(
                "Australian Government – Federal Register "
                "of Legislation"
            ),
            source_url=TAX_RATES_SOURCE_URL,
        ),
        FinancialRule(
            region="Australia",
            category="tax",
            rule_year="2026-2027",
            rule_key="resident_income_tax_bracket_45001_135000",
            rule_value=json.dumps(
                {
                    "bracket_label": "$45,001 – $135,000",
                    "income_from": 45000.01,
                    "income_to": 135000,
                    "base_tax": 4020,
                    "threshold": 45000,
                    "marginal_rate": 0.30,
                    "formula": (
                        "$4,020 plus 30c for each $1 "
                        "over $45,000"
                    ),
                    "medicare_levy_included": False,
                }
            ),
            source_name=(
                "Australian Government – Federal Register "
                "of Legislation"
            ),
            source_url=TAX_RATES_SOURCE_URL,
        ),
        FinancialRule(
            region="Australia",
            category="tax",
            rule_year="2026-2027",
            rule_key="resident_income_tax_bracket_135001_190000",
            rule_value=json.dumps(
                {
                    "bracket_label": "$135,001 – $190,000",
                    "income_from": 135000.01,
                    "income_to": 190000,
                    "base_tax": 31020,
                    "threshold": 135000,
                    "marginal_rate": 0.37,
                    "formula": (
                        "$31,020 plus 37c for each $1 "
                        "over $135,000"
                    ),
                    "medicare_levy_included": False,
                }
            ),
            source_name=(
                "Australian Government – Federal Register "
                "of Legislation"
            ),
            source_url=TAX_RATES_SOURCE_URL,
        ),
        FinancialRule(
            region="Australia",
            category="tax",
            rule_year="2026-2027",
            rule_key="resident_income_tax_bracket_190001_over",
            rule_value=json.dumps(
                {
                    "bracket_label": "$190,001 and over",
                    "income_from": 190000.01,
                    "income_to": None,
                    "base_tax": 51370,
                    "threshold": 190000,
                    "marginal_rate": 0.45,
                    "formula": (
                        "$51,370 plus 45c for each $1 "
                        "over $190,000"
                    ),
                    "medicare_levy_included": False,
                }
            ),
            source_name=(
                "Australian Government – Federal Register "
                "of Legislation"
            ),
            source_url=TAX_RATES_SOURCE_URL,
        ),
    ]
    db_session.add_all(rules)
    db_session.commit()


def create_current_superannuation_rules(db_session) -> None:
    rules = [
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
                    "payment_timing": (
                        "Payday Super from 1 July 2026; contributions "
                        "must generally reach the employee's super fund "
                        "within 7 business days after payday"
                    ),
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
                        "The non-concessional cap is nil if the "
                        "total superannuation balance is "
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
        temperature=0.65,
        structured_temperature=0,
        retry_attempts=1,
        retry_delay_seconds=0,
    )
    provider._client = FakeGeminiClient(models)

    answer = asyncio.run(
        provider.generate_reply(
            "What is budgeting?",
            system_instruction="Enabled topics: Budgeting.",
        )
    )

    assert answer == "Recovered response."
    assert models.calls == 2
    assert models.requests[-1]["config"].temperature == 0.65
    assert "Enabled topics: Budgeting." in str(
        models.requests[-1]["config"].system_instruction
    )


def test_gemini_provider_streams_generated_chunks():
    models = StreamingGeminiModels()
    provider = GeminiProvider(
        api_key="test-api-key",
        model="test-model",
        timeout_seconds=5,
        temperature=0.65,
        structured_temperature=0,
        retry_attempts=1,
        retry_delay_seconds=0,
    )
    provider._client = FakeGeminiClient(models)

    async def collect_chunks():
        return [
            chunk
            async for chunk in provider.generate_reply_stream(
                "What is budgeting?",
                system_instruction="Enabled topics: Budgeting.",
            )
        ]

    chunks = asyncio.run(collect_chunks())

    assert chunks == ["Gemini ", "stream."]
    assert len(models.requests) == 1
    assert models.requests[0]["config"].temperature == 0.65
    assert "Enabled topics: Budgeting." in str(
        models.requests[0]["config"].system_instruction
    )


def test_openrouter_provider_streams_sse_chunks():
    client = RecordingStreamingOpenRouterClient(
        [
            ": OPENROUTER PROCESSING",
            (
                'data: {"choices":[{"delta":'
                '{"content":"OpenRouter "},"finish_reason":null}]}'
            ),
            (
                'data: {"choices":[{"delta":'
                '{"content":"stream."},"finish_reason":"stop"}]}'
            ),
            "data: [DONE]",
        ]
    )
    provider = OpenRouterProvider(
        api_key="test-api-key",
        model="google/gemini-2.5-flash",
        timeout_seconds=5,
        temperature=0.65,
        structured_temperature=0.05,
        retry_attempts=1,
        retry_delay_seconds=0,
    )
    provider._client = client

    async def collect_chunks():
        return [
            chunk
            async for chunk in provider.generate_reply_stream(
                "What is budgeting?"
            )
        ]

    chunks = asyncio.run(collect_chunks())

    assert chunks == ["OpenRouter ", "stream."]
    assert len(client.requests) == 1
    method, path, payload = client.requests[0]
    assert method == "POST"
    assert path == "/chat/completions"
    assert payload["stream"] is True


def test_openrouter_provider_requests_structured_json():
    client = RecordingOpenRouterClient(
        {
            "choices": [
                {
                    "message": {
                        "content": '{"intent":"budgeting"}',
                    },
                },
            ],
        }
    )
    provider = OpenRouterProvider(
        api_key="test-api-key",
        model="google/gemini-2.5-flash",
        timeout_seconds=5,
        temperature=0.65,
        structured_temperature=0.05,
        retry_attempts=1,
        retry_delay_seconds=0,
    )
    provider._client = client
    response_schema = {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
            },
        },
        "required": ["intent"],
        "additionalProperties": False,
    }

    result = asyncio.run(
        provider.generate_json(
            "Classify this request.",
            response_schema,
        )
    )

    assert result == {"intent": "budgeting"}
    assert len(client.requests) == 1
    path, payload = client.requests[0]
    assert path == "/chat/completions"
    assert payload["model"] == "google/gemini-2.5-flash"
    assert payload["messages"][0] == {
        "role": "system",
        "content": FINANCIAL_ADVISOR_INSTRUCTIONS,
    }
    assert payload["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "financial_advisor_response",
            "strict": True,
            "schema": response_schema,
        },
    }
    assert payload["provider"] == {
        "require_parameters": True,
    }
    assert payload["temperature"] == 0.05


def test_openrouter_provider_uses_configured_conversation_temperature():
    provider = OpenRouterProvider(
        api_key="test-api-key",
        model="google/gemini-2.5-flash",
        timeout_seconds=5,
        temperature=0.65,
        structured_temperature=0.05,
        retry_attempts=1,
        retry_delay_seconds=0,
    )

    payload = provider._build_request_payload(
        "Explain compound interest.",
        response_schema=None,
    )

    assert payload["temperature"] == 0.65


def test_openrouter_provider_adds_request_system_instructions():
    provider = OpenRouterProvider(
        api_key="test-api-key",
        model="google/gemini-2.5-flash",
        timeout_seconds=5,
        temperature=0.65,
        structured_temperature=0.05,
        retry_attempts=1,
        retry_delay_seconds=0,
    )

    payload = provider._build_request_payload(
        "Explain compound interest.",
        response_schema=None,
        system_instruction="Disabled topics: Investing.",
    )

    system_prompt = payload["messages"][0]["content"]
    assert system_prompt.startswith(FINANCIAL_ADVISOR_INSTRUCTIONS)
    assert "Disabled topics: Investing." in system_prompt


def test_openrouter_retries_embedded_provider_error(caplog):
    client = RecordingOpenRouterClient(
        [
            {
                "choices": [
                    {
                        "message": {"content": ""},
                        "finish_reason": "error",
                        "error": {
                            "code": 502,
                            "message": "sensitive upstream detail",
                            "metadata": {
                                "error_type": "provider_unavailable",
                            },
                        },
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": "Recovered response.",
                        }
                    }
                ]
            },
        ]
    )
    provider = create_test_openrouter_provider(client)

    answer = asyncio.run(provider.generate_reply("What is budgeting?"))

    assert answer == "Recovered response."
    assert len(client.requests) == 2
    assert "error_type=provider_unavailable" in caplog.text
    assert "sensitive upstream detail" not in caplog.text


def test_openrouter_retries_empty_successful_http_response():
    client = RecordingOpenRouterClient(
        [
            {
                "choices": [
                    {
                        "message": {"content": None},
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": "Recovered response.",
                        }
                    }
                ]
            },
        ]
    )
    provider = create_test_openrouter_provider(client)

    answer = asyncio.run(provider.generate_reply("What is budgeting?"))

    assert answer == "Recovered response."
    assert len(client.requests) == 2


def test_openrouter_retries_invalid_structured_json():
    client = RecordingOpenRouterClient(
        [
            {
                "choices": [
                    {
                        "message": {"content": "not-json"},
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"intent":"budgeting"}',
                        }
                    }
                ]
            },
        ]
    )
    provider = create_test_openrouter_provider(client)
    response_schema = {
        "type": "object",
        "properties": {"intent": {"type": "string"}},
        "required": ["intent"],
        "additionalProperties": False,
    }

    result = asyncio.run(
        provider.generate_json(
            "Classify this request.",
            response_schema,
        )
    )

    assert result == {"intent": "budgeting"}
    assert len(client.requests) == 2


def test_openrouter_maps_embedded_rate_limit_without_retry():
    client = RecordingOpenRouterClient(
        {
            "error": {
                "code": "429",
                "message": "Rate limit exceeded.",
                "metadata": {
                    "error_type": "rate_limit_exceeded",
                },
            }
        }
    )
    provider = create_test_openrouter_provider(
        client,
        retry_attempts=3,
    )

    with pytest.raises(LLMRateLimitError):
        asyncio.run(provider.generate_reply("What is budgeting?"))

    assert len(client.requests) == 1


def test_openrouter_stops_after_configured_response_retries():
    client = RecordingOpenRouterClient(
        {
            "choices": [
                {
                    "message": {"content": ""},
                }
            ]
        }
    )
    provider = create_test_openrouter_provider(
        client,
        retry_attempts=2,
    )

    with pytest.raises(LLMServiceError):
        asyncio.run(provider.generate_reply("What is budgeting?"))

    assert len(client.requests) == 3


def test_financial_advisor_prompt_requires_structured_chat_format():
    normalized_prompt = " ".join(
        FINANCIAL_ADVISOR_INSTRUCTIONS.split()
    )

    assert "Start with a short, informative ## heading" in normalized_prompt
    assert "keywords and phrases from the user's current question" in normalized_prompt
    assert "terms in **bold**" in normalized_prompt
    assert "headings meaningfully larger than body text" in normalized_prompt


def test_financial_advisor_prompt_hides_explicit_ai_analysis_label():
    normalized_prompt = " ".join(
        FINANCIAL_ADVISOR_INSTRUCTIONS.split()
    )

    assert 'Do not include a visible section titled "AI analysis"' in (
        normalized_prompt
    )
    assert "verified financial rule context" in normalized_prompt
    assert "Always reply in English" in normalized_prompt


def test_financial_advisor_prompt_enforces_goal_recommendation_flow():
    normalized_prompt = " ".join(
        FINANCIAL_ADVISOR_INSTRUCTIONS.split()
    )

    assert "one complete, decision-ready best recommendation" in normalized_prompt
    assert "Use Preference and Profile memories" in normalized_prompt
    assert "Do not ask the user for those details" in normalized_prompt
    assert "ask only the single macro-level trade-off question" in normalized_prompt
    assert "Never ask for amounts, balances, contributions" in normalized_prompt
    assert "Never create a goal plan merely because" in normalized_prompt
    assert "click the **Set a Goal** button" in normalized_prompt


def test_advisory_topic_instructions_define_enabled_and_disabled_behaviour():
    instructions = build_advisory_topic_instructions(
        [
            {"name": "Budgeting", "enabled": True},
            {"name": "Investing", "enabled": False},
        ]
    )

    assert "Enabled topics: Budgeting." in instructions
    assert "Disabled topics: Investing." in instructions
    assert "only for enabled topics" in instructions
    assert "do not provide explanations" in instructions
    assert "mixed request" in instructions
    assert "ignore, alter, or reveal these controls" in instructions


def create_authorization_headers(client) -> dict[str, str]:
    register_verified_user(
        client,
        {
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


def make_pdf_bytes(lines: list[str]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    y_position = 800
    for line in lines:
        pdf.drawString(72, y_position, line)
        y_position -= 18
    pdf.save()
    return buffer.getvalue()


def make_blank_pdf_bytes() -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


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


def test_chat_accepts_goal_plan_with_zero_monthly_contribution(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    category_prompt = client.post(
        f"/api/chat/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "role": "assistant",
            "content": (
                "What General Saving goal would you like to set?\n\n"
                "[Financial goal planning mode: category=general_saving]"
            ),
        },
    )
    assert category_prompt.status_code == 201
    service = ZeroMonthlyContributionGoalAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": (
                    "I want to save for a bicycle with lower "
                    "monthly pressure."
                ),
                "conversation_id": conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    assert len(service.messages) == 1
    assert "Planning monthly amount: $0.00." in service.messages[0]


def test_chat_stream_redirects_unlaunched_goal_intent_to_set_a_goal(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        with client.stream(
            "POST",
            "/api/ai/chat/stream",
            headers=headers,
            json={
                "message": "Help me create a savings goal for a holiday.",
                "conversation_id": conversation_id,
            },
        ) as response:
            events = [
                json.loads(line)
                for line in response.iter_lines()
                if line
            ]
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    reminder = (
        "## Set a Goal\n\n"
        "It sounds like you want to create a new financial goal. Click "
        "**Set a Goal** below to start the guided Goal Planning flow."
    )
    assert response.status_code == 200
    assert events == [
        {"type": "delta", "content": reminder},
        {"type": "done", "answer": reminder, "model": "test-model"},
    ]
    assert service.messages == []


def test_chat_stream_returns_incremental_events_and_persists_answer(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    service = StreamingTestAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service

    try:
        with client.stream(
            "POST",
            "/api/ai/chat/stream",
            headers=headers,
            json={
                "message": "How should I start saving?",
                "conversation_id": conversation_id,
            },
        ) as response:
            events = [
                json.loads(line)
                for line in response.iter_lines()
                if line
            ]
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/x-ndjson"
    )
    assert response.headers["cache-control"] == "no-cache"
    assert events == [
        {"type": "delta", "content": "Streamed **financial "},
        {"type": "delta", "content": "guidance**."},
        {
            "type": "done",
            "answer": "Streamed **financial guidance**.",
            "model": "test-model",
        },
    ]

    detail = client.get(
        f"/api/chat/conversations/{conversation_id}",
        headers=headers,
    ).json()
    assert [message["role"] for message in detail["messages"]] == [
        "user",
        "assistant",
    ]
    assert detail["messages"][-1]["content"] == (
        "Streamed **financial guidance**."
    )


def test_chat_stream_keeps_completed_answer_when_memory_update_fails(
    client,
    monkeypatch,
):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: StreamingTestAdvisorService()

    def fail_memory_update(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("Test memory storage failure.")

    monkeypatch.setattr(
        "app.api.routes_ai.remember_from_conversation_turn",
        fail_memory_update,
    )
    try:
        response = client.post(
            "/api/ai/chat/stream",
            headers=headers,
            json={
                "message": "How should I start saving?",
                "conversation_id": conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    events = [
        json.loads(line)
        for line in response.text.splitlines()
        if line
    ]
    assert events[-1] == {
        "type": "done",
        "answer": "Streamed **financial guidance**.",
        "model": "test-model",
    }

    detail = client.get(
        f"/api/chat/conversations/{conversation_id}",
        headers=headers,
    ).json()
    assert detail["messages"][-1]["role"] == "assistant"
    assert detail["messages"][-1]["content"] == (
        "Streamed **financial guidance**."
    )


def test_chat_stream_returns_in_band_error_after_partial_output(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: FailingStreamingTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat/stream",
            headers=headers,
            json={
                "message": "Explain emergency savings.",
                "conversation_id": conversation_id,
            },
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    events = [
        json.loads(line)
        for line in response.text.splitlines()
        if line
    ]
    assert response.status_code == 200
    assert events == [
        {"type": "delta", "content": "Partial response."},
        {
            "type": "error",
            "message": (
                "The AI service could not generate a response. "
                "Please try again."
            ),
            "status": 502,
        },
    ]

    detail = client.get(
        f"/api/chat/conversations/{conversation_id}",
        headers=headers,
    ).json()
    assert [message["role"] for message in detail["messages"]] == [
        "user",
    ]


def test_chat_stream_returns_in_band_error_for_missing_conversation(client):
    response = client.post(
        "/api/ai/chat/stream",
        headers=create_authorization_headers(client),
        json={
            "message": "How should I start saving?",
            "conversation_id": 999,
        },
    )

    events = [
        json.loads(line)
        for line in response.text.splitlines()
        if line
    ]
    assert response.status_code == 200
    assert events == [
        {
            "type": "error",
            "message": "Conversation was not found.",
            "status": 404,
        }
    ]


def test_chat_reads_latest_advisory_settings_for_every_request(
    client,
    db_session,
):
    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[get_ai_advisor_service] = lambda: service
    headers = create_authorization_headers(client)

    try:
        first_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "Help me plan my finances."},
        )

        db_session.add(
            AdvisorySettings(
                id=1,
                topics=[
                    {"name": "Budgeting", "enabled": False},
                    {"name": "Saving", "enabled": True},
                    {"name": "Tax", "enabled": True},
                    {"name": "Superannuation", "enabled": True},
                    {"name": "Investing", "enabled": True},
                    {"name": "Debt", "enabled": True},
                ],
            )
        )
        db_session.commit()

        second_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={"message": "Help me plan my finances."},
        )
    finally:
        app.dependency_overrides.pop(get_ai_advisor_service, None)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(service.system_instructions) == 2

    first_instructions, second_instructions = service.system_instructions
    assert first_instructions is not None
    assert second_instructions is not None
    assert (
        "Enabled topics: Budgeting, Saving, Tax, Superannuation, Debt."
        in first_instructions
    )
    assert "Disabled topics: Investing." in first_instructions
    assert (
        "Enabled topics: Saving, Tax, Superannuation, Investing, Debt."
        in second_instructions
    )
    assert "Disabled topics: Budgeting." in second_instructions


def test_chat_preserves_safe_formatting_and_strips_ai_analysis_heading(client):
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: MarkdownTestAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(
                client
            ),
            json={
                "message": "Read my financial details.",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "AI analysis" not in answer
    assert "- **Cash balance:** $12,500" in answer
    assert "`" not in answer
    assert "HomePage was updated." in answer


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
        "Set the configured provider API key on the backend."
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
        rule_year="2026-2027",
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
    assert response.json()["model"] == "test-model"
    assert len(service.messages) == 1
    assert "Verified financial rule context" in service.messages[0]
    assert "Rule value: Verified test rule content." in service.messages[0]
    assert "User question:" in service.messages[0]
    answer = response.json()["answer"]
    assert "Verified test rule content." in answer
    assert "Australian Taxation Office" in answer


def test_chat_automatically_injects_current_tax_table_context(
    client,
    db_session,
):
    create_2026_2027_tax_rules(db_session)
    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": (
                    "What are the current Australian resident "
                    "income tax rates?"
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "test-model"
    assert len(service.messages) == 1
    assert "Verified financial rule context" in service.messages[0]
    assert "User question:" in service.messages[0]
    answer = response.json()["answer"]
    assert "2026-2027" in answer
    assert "15c for each $1 over $18,200" in answer
    assert TAX_RATES_SOURCE_URL in answer


def test_chat_uses_latest_supported_tax_year_from_database(
    client,
    db_session,
):
    create_2026_2027_tax_rules(db_session)
    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": (
                    "What are the current Australian resident "
                    "income tax rates?"
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "2026-2027" in answer
    assert "15c for each $1 over $18,200" in answer


def test_chat_automatically_injects_current_tax_bracket_context(
    client,
    db_session,
):
    create_2026_2027_tax_rules(db_session)
    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": (
                    "My taxable income is 80,000 AUD. "
                    "How much income tax applies this year?"
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "test-model"
    assert len(service.messages) == 1
    assert "Verified financial rule context" in service.messages[0]
    answer = response.json()["answer"]
    assert "2026-2027" in answer
    assert "taxable income $80,000.00 falls in" in answer
    assert "marginal rate is 30%" in answer
    assert "$14,520.00" in answer
    assert TAX_RATES_SOURCE_URL in answer


def test_chat_uses_llm_intent_for_fuzzy_tax_calculation(
    client,
    db_session,
):
    create_2026_2027_tax_rules(db_session)
    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": (
                    "I earn 80k. What portion of that goes "
                    "to the government?"
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert len(service.rule_classification_messages) == 1
    assert len(service.messages) == 1
    assert "Verified financial rule context" in service.messages[0]
    answer = response.json()["answer"]
    assert "taxable income $80,000.00 falls in" in answer
    assert "$14,520.00" in answer


def test_chat_warns_when_requested_tax_year_is_not_available(
    client,
    db_session,
):
    create_2026_2027_tax_rules(db_session)
    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": "What were the Australian tax rates in 2022?",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "test-model"
    assert len(service.messages) == 1
    assert "Verified financial rule context" in service.messages[0]
    answer = response.json()["answer"]
    assert "does not contain resident income tax rates" in answer
    assert "2021-2022" in answer
    assert "Do not infer a specific rate from model memory" in answer
    assert "19c for each $1 over $18,200" not in answer


def test_chat_automatically_injects_payday_super_context(
    client,
    db_session,
):
    create_current_superannuation_rules(db_session)
    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": (
                    "What is the employer super guarantee "
                    "after 1 July 2026?"
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "test-model"
    assert len(service.messages) == 1
    assert "Verified financial rule context" in service.messages[0]
    answer = response.json()["answer"]
    assert "2026-2027" in answer
    assert "general super guarantee rate is 12%" in answer
    assert "qualifying earnings" in answer
    assert "Payday Super from 1 July 2026" in answer
    assert "within 7 business days after payday" in answer
    assert ATO_SUPER_GUARANTEE_URL in answer


def test_chat_automatically_injects_super_contribution_cap_context(
    client,
    db_session,
):
    create_super_contribution_cap_rules(db_session)
    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": (
                    "What are the 2026-27 concessional and "
                    "non-concessional super contribution caps?"
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "test-model"
    assert len(service.messages) == 1
    assert "Verified financial rule context" in service.messages[0]
    answer = response.json()["answer"]
    assert "2026-2027" in answer
    assert "Concessional contributions cap: $32,500" in answer
    assert "Non-Concessional contributions cap: $130,000" in answer
    assert "salary sacrifice contributions" in answer
    assert "The non-concessional cap is nil" in answer
    assert ATO_SUPER_CAPS_URL in answer


def test_chat_routes_contribution_cap_without_super_intent(
    client,
    db_session,
):
    create_super_contribution_cap_rules(db_session)
    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": (
                    "What is the 2026-27 concessional "
                    "contribution cap?"
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "test-model"
    assert len(service.messages) == 1
    assert "Verified financial rule context" in service.messages[0]
    assert "superannuation contribution caps" in service.messages[0]
    assert "employer super guarantee" not in service.messages[0]
    answer = response.json()["answer"]
    assert "2026-2027" in answer
    assert "Concessional contributions cap: $32,500" in answer
    assert ATO_SUPER_CAPS_URL in answer


def test_chat_does_not_route_partial_english_keyword_matches(
    client,
    db_session,
):
    create_2026_2027_tax_rules(db_session)
    create_current_superannuation_rules(db_session)
    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        headers = create_authorization_headers(client)
        taxi_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "The taxi fare was higher than expected.",
            },
        )
        superb_response = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "That was a superb explanation.",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert taxi_response.status_code == 200
    assert superb_response.status_code == 200
    assert len(service.messages) == 2
    assert service.messages[0] == (
        "The taxi fare was higher than expected."
    )
    assert service.messages[1] == "That was a superb explanation."


def test_pdf_asset_candidates_preserve_money_separators():
    candidates = pdf_financial_service.extract_asset_candidates(
        "\n".join(
            [
                "Purchase of a vehicle 80,000.00",
                "Stock holding 1000.50",
                "Payroll 5,044.38",
            ]
        )
    )

    assert [
        str(candidate.amount)
        for candidate in candidates
    ] == [
        "80000.00",
        "1000.50",
        "5044.38",
    ]
    assert pdf_financial_service.extract_asset_candidates(
        "Unsupported European amount 1.000,50"
    ) == []


def test_pdf_asset_classification_enforces_whitelist_and_confidence():
    candidates = pdf_financial_service.extract_asset_candidates(
        "\n".join(
            [
                "Home value 900,000.00",
                "Unclear investment 5,000.00",
                "Other value 1,000.00",
            ]
        )
    )
    classifications = (
        pdf_asset_classifier.normalize_asset_classification_payload(
            {
                "classifications": [
                    {
                        "candidate_id": "asset_1",
                        "classification": "property",
                        "confidence": 0.98,
                    },
                    {
                        "candidate_id": "asset_2",
                        "classification": "crypto",
                        "confidence": 0.99,
                    },
                    {
                        "candidate_id": "asset_3",
                        "classification": "others",
                        "confidence": 0.2,
                    },
                ]
            },
            candidates,
        )
    )

    assets = pdf_asset_classifier.select_classified_assets(
        candidates,
        classifications,
    )

    assert [
        (asset.asset_type, str(asset.amount))
        for asset in assets
    ] == [("property", "900000.00")]


def test_pdf_cash_flow_kind_classification_defaults_uncertain_rows_to_one_off():
    candidates = [
        pdf_cash_flow_classifier.CashFlowKindCandidate(
            candidate_id="cash_flow_1",
            description="Salary",
            amount=Decimal("3000.00"),
            transaction_type="income",
            source_line="Salary +$3,000",
        ),
        pdf_cash_flow_classifier.CashFlowKindCandidate(
            candidate_id="cash_flow_2",
            description="Freelance",
            amount=Decimal("800.00"),
            transaction_type="income",
            source_line="Freelance +$800",
        ),
        pdf_cash_flow_classifier.CashFlowKindCandidate(
            candidate_id="cash_flow_3",
            description="Unknown credit",
            amount=Decimal("50.00"),
            transaction_type="income",
            source_line="Unknown credit +$50",
        ),
    ]
    classifications = (
        pdf_cash_flow_classifier.normalize_cash_flow_kind_payload(
            {
                "classifications": [
                    {
                        "candidate_id": "cash_flow_1",
                        "cash_flow_kind": "ongoing",
                        "confidence": 0.96,
                    },
                    {
                        "candidate_id": "cash_flow_2",
                        "cash_flow_kind": "ongoing",
                        "confidence": 0.4,
                    },
                ],
            },
            candidates,
        )
    )

    assert pdf_cash_flow_classifier.selected_cash_flow_kinds(
        candidates,
        classifications,
    ) == {
        "cash_flow_1": "ongoing",
        "cash_flow_2": "one_off",
        "cash_flow_3": "one_off",
    }


def test_pdf_chat_classifies_multiple_assets_for_homepage(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    service = SuccessfulPdfAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service
    pdf_bytes = make_pdf_bytes(
        [
            "Asset Summary",
            "Purchase of a Mercedes-Benz 80,000.00",
            "Money Transfers from Dad 10,000.00",
            "stock hit limit up 1000.50",
        ]
    )

    try:
        response = client.post(
            "/api/ai/chat/pdf",
            headers=headers,
            data={
                "message": "Add these assets to my allocation.",
                "conversation_id": str(conversation_id),
            },
            files={
                "files": (
                    "asset-mix.pdf",
                    pdf_bytes,
                    "application/pdf",
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["low_confidence"] is False
    assert {
        record["asset_type"]: record["amount"]
        for record in data["imported_records"]
        if record["record_type"] == "asset"
    } == {
        "cash": 10000.0,
        "stocks": 1000.5,
        "vehicle": 80000.0,
    }
    assert len(service.asset_classification_messages) == 1
    classification_message = service.asset_classification_messages[0]
    assert '"amount_from_backend": "80000.00"' in classification_message
    assert '"amount_from_backend": "10000.00"' in classification_message
    assert '"amount_from_backend": "1000.50"' in classification_message

    financials = client.get(
        "/api/financials",
        headers=headers,
    ).json()
    assert {
        asset["asset_type"]: asset["amount"]
        for asset in financials["assets"]
    } == {
        "cash": "10000.00",
        "stocks": "1000.50",
        "vehicle": "80000.00",
    }

    summary = client.get(
        "/api/financials/summary",
        headers=headers,
    ).json()
    assert {
        allocation["asset_type"]: allocation["amount"]
        for allocation in summary["asset_allocation"]
    } == {
        "cash": "10000.00",
        "stocks": "1000.50",
        "vehicle": "80000.00",
    }


def test_pdf_chat_extracts_financials_and_updates_homepage_data(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    service = SuccessfulPdfAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service
    pdf_bytes = make_pdf_bytes(
        [
            "Financial Summary",
            "Cash savings: $12,500.00",
            "Monthly income: $4,200.00",
            "Monthly expenses: $2,100.00",
        ]
    )

    try:
        response = client.post(
            "/api/ai/chat/pdf",
            headers=headers,
            data={
                "message": "Extract the financial basics.",
                "conversation_id": str(conversation_id),
            },
            files={
                "files": (
                    "statement.pdf",
                    pdf_bytes,
                    "application/pdf",
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "test-model"
    assert data["low_confidence"] is False
    assert data["extracted_text_characters"] > 30
    assert {
        record["name"]
        for record in data["imported_records"]
    } == {
        "Imported cash from statement.pdf",
        "Imported monthly income",
        "Imported monthly expenses",
    }
    assert {
        record["flow_type"]: (
            record["ongoing_amount"],
            record["one_off_amount"],
        )
        for record in data["imported_records"]
        if record["flow_type"] is not None
    } == {
        "income": (4200.0, 0.0),
        "expense": (2100.0, 0.0),
    }
    assert len(service.asset_classification_messages) == 1
    assert "amount_from_backend" in service.asset_classification_messages[0]
    assert len(service.messages) == 1
    assert "HomePage financial basics updated" in service.messages[0]
    assert "Cash savings: $12,500.00" in service.messages[0]

    financials = client.get(
        "/api/financials",
        headers=headers,
    ).json()
    assert financials["assets"][0]["asset_type"] == "cash"
    assert financials["assets"][0]["amount"] == "12500.00"
    assert {
        item["flow_type"]: item["amount"]
        for item in financials["cash_flows"]
    } == {
        "income": "4200.00",
        "expense": "2100.00",
    }

    detail = client.get(
        f"/api/chat/conversations/{conversation_id}",
        headers=headers,
    ).json()
    assert [message["role"] for message in detail["messages"]] == [
        "user",
        "assistant",
    ]
    assert "Uploaded PDF(s): statement.pdf" in detail["messages"][0]["content"]


def test_pdf_chat_calculates_income_and_expenses_from_transactions(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    service = SuccessfulPdfAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service
    pdf_bytes = make_pdf_bytes(
        [
            "Bank Statement",
            "Opening Balance: $12,500.00",
            "Salary               +$3,000",
            "Rent                  -$1,500",
            "Woolworths              -$120",
            "Electricity              -$90",
            "Freelance              +$800",
        ]
    )

    try:
        response = client.post(
            "/api/ai/chat/pdf",
            headers=headers,
            data={
                "message": "Update my financial information.",
                "conversation_id": str(conversation_id),
            },
            files={
                "files": (
                    "transactions.pdf",
                    pdf_bytes,
                    "application/pdf",
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["low_confidence"] is False
    assert {
        record["name"]: record["amount"]
        for record in data["imported_records"]
    } == {
        "Imported cash from transactions.pdf": 12500.0,
        "Imported monthly income": 3800.0,
        "Imported monthly expenses": 1710.0,
    }
    assert {
        record["name"]: (
            record["ongoing_amount"],
            record["one_off_amount"],
        )
        for record in data["imported_records"]
        if record["flow_type"] is not None
    } == {
        "Imported monthly income": (3000.0, 800.0),
        "Imported monthly expenses": (1710.0, 0.0),
    }
    assert "Transaction summary: income=$3,800.00" in service.messages[0]
    assert "expenses=$1,710.00" in service.messages[0]
    assert (
        "Cash-flow classification summary: "
        "ongoing_income=$3,000.00; ongoing_expenses=$1,710.00; "
        "one_off_income=$800.00; one_off_expenses=$0.00"
    ) in service.messages[0]
    assert (
        "Ongoing monthly surplus (ongoing income minus ongoing expenses): "
        "$1,290.00."
    ) in service.messages[0]
    assert "One-off surplus in that period" in service.messages[0]
    assert "$800.00" in service.messages[0]
    assert len(service.cash_flow_kind_classification_messages) == 1

    financials = client.get(
        "/api/financials",
        headers=headers,
    ).json()
    assert financials["assets"][0]["amount"] == "12500.00"
    assert {
        item["flow_type"]: (
            item["amount"],
            item["ongoing_amount"],
        )
        for item in financials["cash_flows"]
    } == {
        "income": ("3800.00", "3000.00"),
        "expense": ("1710.00", "1710.00"),
    }


def test_pdf_chat_batches_ambiguous_transactions_for_llm_classification(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    service = SuccessfulPdfAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service
    pdf_bytes = make_pdf_bytes(
        [
            "Bank Statement",
            "Salary 3000",
            "Woolworths 120",
            "Transfer 500",
        ]
    )

    try:
        response = client.post(
            "/api/ai/chat/pdf",
            headers=headers,
            data={
                "message": "Update my financial information.",
                "conversation_id": str(conversation_id),
            },
            files={
                "files": (
                    "ambiguous.pdf",
                    pdf_bytes,
                    "application/pdf",
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert len(service.transaction_classification_messages) == 1
    assert "amount_from_backend" in (
        service.transaction_classification_messages[0]
    )
    assert {
        record["name"]: record["amount"]
        for record in response.json()["imported_records"]
    } == {
        "Imported monthly income": 3000.0,
        "Imported monthly expenses": 120.0,
    }

    financials = client.get(
        "/api/financials",
        headers=headers,
    ).json()
    assert {
        item["flow_type"]: item["amount"]
        for item in financials["cash_flows"]
    } == {
        "income": "3000.00",
        "expense": "120.00",
    }


def test_pdf_chat_extracts_opening_balance_deposits_and_credits(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    service = SuccessfulPdfAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service
    pdf_bytes = make_pdf_bytes(
        [
            "Statement Summary",
            "Opening Balance $9,250.50",
            "Deposits and Credits $3,800.00",
            "Total Debits $1,710.00",
        ]
    )

    try:
        response = client.post(
            "/api/ai/chat/pdf",
            headers=headers,
            data={
                "message": "Update my HomePage basics.",
                "conversation_id": str(conversation_id),
            },
            files={
                "files": (
                    "summary.pdf",
                    pdf_bytes,
                    "application/pdf",
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert {
        record["name"]: record["amount"]
        for record in response.json()["imported_records"]
    } == {
        "Imported cash from summary.pdf": 9250.5,
        "Imported monthly income": 3800.0,
        "Imported monthly expenses": 1710.0,
    }


def test_pdf_chat_uses_ocr_text_for_image_based_statement(
    client,
    monkeypatch,
):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    service = SuccessfulPdfAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    def fake_ocr_text(content: bytes) -> str:
        assert content

        return "\n".join(
            [
                "Education:--22984",
                "Eating out & takeaway:-14",
                "Vehicle & transport:-14",
                "Income:+17000",
                "School Scholarship: 1,000",
                "Government Subsidy:+1,000",
                "Part-time Job Wages:+5,000",
            ]
        )

    monkeypatch.setattr(
        pdf_financial_service,
        "extract_ocr_text_from_pdf_bytes",
        fake_ocr_text,
    )

    try:
        response = client.post(
            "/api/ai/chat/pdf",
            headers=headers,
            data={
                "message": "Read this scanned statement.",
                "conversation_id": str(conversation_id),
            },
            files={
                "files": (
                    "scanned.pdf",
                    make_blank_pdf_bytes(),
                    "application/pdf",
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["low_confidence"] is False
    assert {
        record["name"]: record["amount"]
        for record in data["imported_records"]
    } == {
        "Imported monthly income": 24000.0,
        "Imported monthly expenses": 23012.0,
    }
    assert len(service.transaction_classification_messages) == 1
    assert "OCR used: True" in service.messages[0]


def test_pdf_chat_low_confidence_does_not_update_financials(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    service = SuccessfulPdfAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat/pdf",
            headers=headers,
            data={
                "message": "Read this PDF.",
                "conversation_id": str(conversation_id),
            },
            files={
                "files": (
                    "blank.pdf",
                    make_pdf_bytes(["Summary only"]),
                    "application/pdf",
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["low_confidence"] is True
    assert data["imported_records"] == []
    assert data["fallback_reason"] is not None
    assert "Fallback reason" in service.messages[0]
    financials = client.get(
        "/api/financials",
        headers=headers,
    ).json()
    assert financials == {
        "assets": [],
        "debts": [],
        "cash_flows": [],
        "recurring_cash_flows": [],
    }


def test_pdf_chat_redirects_unlaunched_goal_intent_to_set_a_goal(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    service = SuccessfulPdfAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat/pdf",
            headers=headers,
            data={
                "message": "I want to save for a home deposit.",
                "conversation_id": str(conversation_id),
            },
            files={
                "files": (
                    "summary.pdf",
                    make_pdf_bytes(["Summary only"]),
                    "application/pdf",
                ),
            },
        )
        conversation = client.get(
            f"/api/chat/conversations/{conversation_id}",
            headers=headers,
        ).json()
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["answer"] == (
        "## Set a Goal\n\n"
        "It sounds like you want to create a new financial goal. Click "
        "**Set a Goal** below to start the guided Goal Planning flow."
    )
    assert service.messages == []
    assert [message["role"] for message in conversation["messages"]] == [
        "user",
        "assistant",
    ]


def test_pdf_chat_rejects_non_pdf_upload(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: SuccessfulPdfAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat/pdf",
            headers=headers,
            data={
                "message": "Read this file.",
                "conversation_id": str(conversation_id),
            },
            files={
                "files": (
                    "statement.txt",
                    b"Cash savings: $100",
                    "application/pdf",
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 415
    assert response.json()["detail"] == "Only PDF files are supported."


def test_pdf_chat_rejects_mismatched_pdf_upload(client):
    headers = create_authorization_headers(client)
    conversation_id = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    ).json()["conversation_id"]
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: SuccessfulPdfAdvisorService()

    try:
        response = client.post(
            "/api/ai/chat/pdf",
            headers=headers,
            data={
                "message": "Read this file.",
                "conversation_id": str(conversation_id),
            },
            files={
                "files": (
                    "statement.pdf",
                    b"Cash savings: $100",
                    "text/plain",
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 415
    assert response.json()["detail"] == "Only PDF files are supported."


def test_chat_summarizes_supported_rule_years(
    client,
    db_session,
):
    create_2026_2027_tax_rules(db_session)
    create_current_superannuation_rules(db_session)
    create_super_contribution_cap_rules(db_session)
    service = SuccessfulTestAdvisorService()
    app.dependency_overrides[
        get_ai_advisor_service
    ] = lambda: service

    try:
        response = client.post(
            "/api/ai/chat",
            headers=create_authorization_headers(client),
            json={
                "message": (
                    "Which years does your rules knowledge base support?"
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ai_advisor_service,
            None,
        )

    assert response.status_code == 200
    assert response.json()["model"] == "test-model"
    assert len(service.messages) == 1
    assert "Verified financial rule context" in service.messages[0]
    answer = response.json()["answer"]
    assert "2025-2026" not in answer
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
