from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


MemoryCategory = Literal[
    "asset",
    "debt",
    "expense",
    "goal",
    "income",
    "preference",
    "profile",
    "other",
]
MemorySource = Literal["chat", "manual"]


class MemoryRequest(BaseModel):
    fact: str = Field(min_length=1, max_length=1000)
    category: MemoryCategory = "other"

    @field_validator("fact")
    @classmethod
    def normalize_fact(cls, value: str) -> str:
        value = " ".join(value.strip().split())
        if not value:
            raise ValueError("Memory fact must not be blank.")
        return value


class MemoryResponse(MemoryRequest):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: MemorySource
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None


class MemoryExportResponse(BaseModel):
    generated_at: datetime
    memories: list[MemoryResponse]