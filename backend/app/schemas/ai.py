from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class AIChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=4000,
    )
    rule_id: int | None = Field(default=None, gt=0)
    conversation_id: int | None = Field(default=None, gt=0)

    @field_validator("message")
    @classmethod
    def normalize_message(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Message must not be empty."
            )

        return normalized


class AIChatResponse(BaseModel):
    answer: str
    model: str


class ImportedFinancialRecordResponse(BaseModel):
    record_type: str
    name: str
    amount: float
    asset_type: str | None = None
    flow_type: str | None = None
    date: str | None = None


class AIPdfChatResponse(AIChatResponse):
    low_confidence: bool
    extracted_text_characters: int
    imported_records: list[ImportedFinancialRecordResponse]
    fallback_reason: str | None = None
