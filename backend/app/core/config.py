from decimal import Decimal
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "AI Financial Literacy Advisor"

    database_url: str = (
        "postgresql://finance_user:finance_password@db:5432/finance_db"
    )

    jwt_secret_key: str = "replace_with_a_secure_secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    llm_provider: Literal["gemini", "openrouter", "mock"] = "gemini"
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_timeout_seconds: float = Field(default=15, gt=0)
    llm_temperature: float = Field(default=0.3, ge=0, le=2)
    llm_structured_temperature: float = Field(default=0, ge=0, le=2)
    llm_retry_attempts: int = Field(default=1, ge=0)
    llm_retry_delay_seconds: float = Field(default=0.75, ge=0)

    chat_context_max_messages: int = Field(default=16, ge=1)
    chat_context_max_message_characters: int = Field(default=1200, ge=4)
    goal_context_max_messages: int = Field(default=24, ge=1)
    goal_context_max_message_characters: int = Field(default=4000, ge=4)
    pdf_context_max_characters: int = Field(default=6000, ge=1)

    goal_priority_high_weight: Decimal = Field(
        default=Decimal("3"),
        gt=0,
    )
    goal_priority_medium_weight: Decimal = Field(
        default=Decimal("2"),
        gt=0,
    )
    goal_priority_low_weight: Decimal = Field(
        default=Decimal("1"),
        gt=0,
    )
    # Model self-assessed routing confidence, not a calibrated probability.
    rule_intent_confidence_threshold: float = 0.55

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10

    admin_email: str = ""
    admin_password: str = ""
    admin_name: str = "Admin"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
