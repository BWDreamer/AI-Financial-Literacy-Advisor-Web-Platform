from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class MessageCreateRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Content must not be blank.")
        return value


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ConversationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    conversation_id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationListResponse):
    messages: list[ChatMessageResponse]
