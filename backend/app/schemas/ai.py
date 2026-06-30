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
