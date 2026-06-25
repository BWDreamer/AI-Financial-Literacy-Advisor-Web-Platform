from typing import Literal

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

    llm_provider: Literal["gemini"] = "gemini"
    gemini_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_timeout_seconds: float = 30

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
