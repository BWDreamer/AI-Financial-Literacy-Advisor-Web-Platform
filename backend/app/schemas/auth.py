from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class UserRegisterRequest(BaseModel):
    email: EmailStr

    username: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
    )

    password: str = Field(
        min_length=8,
        max_length=72,
    )

    @field_validator("username")
    @classmethod
    def normalize_optional_username(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        if len(normalized) < 2:
            raise ValueError(
                "Username must contain at least 2 characters."
            )

        return normalized


class UserLoginRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=72,
    )


class UserUpdateRequest(BaseModel):
    username: str = Field(
        min_length=2,
        max_length=50,
    )

    @field_validator("username")
    @classmethod
    def normalize_username(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if len(normalized) < 2:
            raise ValueError(
                "Username must contain at least 2 characters."
            )

        return normalized


class EmailUpdateRequest(BaseModel):
    new_email: EmailStr

    current_password: str = Field(
        min_length=1,
        max_length=72,
    )


class PasswordUpdateRequest(BaseModel):
    current_password: str = Field(
        min_length=1,
        max_length=72,
    )

    new_password: str = Field(
        min_length=8,
        max_length=72,
    )


class AccountDeleteRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AvatarResponse(BaseModel):
    avatar_url: str


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    email: EmailStr
    username: str | None
    avatar_url: str | None
    role: str
    created_at: datetime
