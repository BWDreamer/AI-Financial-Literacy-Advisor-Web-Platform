from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


def validate_password_strength(value: str) -> str:
    if len(value) < 10:
        raise ValueError("Password must contain at least 10 characters.")
    if not any(character.islower() for character in value):
        raise ValueError("Password must contain lowercase characters.")
    if not any(character.isupper() for character in value):
        raise ValueError("Password must contain uppercase characters.")
    if not any(character.isdigit() for character in value):
        raise ValueError("Password must contain numbers.")
    return value


class UserRegisterRequest(BaseModel):
    email: EmailStr

    username: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
    )

    password: str = Field(
        min_length=10,
        max_length=72,
    )

    verification_code: str = Field(
        pattern=r"^\d{6}$",
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

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


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


class OnboardingUpdateRequest(BaseModel):
    onboarding_completed: bool = Field(alias="onboardingCompleted")

    model_config = ConfigDict(populate_by_name=True)


class EmailUpdateRequest(BaseModel):
    new_email: EmailStr

    current_password: str = Field(
        min_length=1,
        max_length=72,
    )

    verification_code: str = Field(
        pattern=r"^\d{6}$",
    )


class RegistrationVerificationCodeRequest(BaseModel):
    email: EmailStr


class EmailChangeVerificationCodeRequest(BaseModel):
    new_email: EmailStr

    current_password: str = Field(
        min_length=1,
        max_length=72,
    )


class VerificationCodeSentResponse(BaseModel):
    message: str
    expires_in: int


class PasswordUpdateRequest(BaseModel):
    current_password: str = Field(
        min_length=1,
        max_length=72,
    )

    new_password: str = Field(
        min_length=10,
        max_length=72,
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


class PasswordResetVerificationCodeRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    email: EmailStr
    verification_code: str = Field(pattern=r"^\d{6}$")
    new_password: str = Field(min_length=10, max_length=72)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


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
    onboarding_completed: bool
    email_verified_at: datetime | None
    created_at: datetime
