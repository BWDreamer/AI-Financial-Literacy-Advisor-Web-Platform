from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class AdminUserCreateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)

    @field_validator("first_name", "last_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank.")
        return value


class AdminUserUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank.")
        return value


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    first_name: str | None
    last_name: str | None
    email: EmailStr
    created_at: datetime
    is_online: bool
    last_seen_at: datetime | None


class HeartbeatResponse(BaseModel):
    last_seen_at: datetime
    is_online: bool
