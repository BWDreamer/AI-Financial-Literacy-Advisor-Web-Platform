from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "AI Financial Literacy Advisor"
    database_url: str = "postgresql://finance_user:finance_password@db:5432/finance_db"
    jwt_secret_key: str = "replace_with_a_secure_secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    llm_provider: str = "mock"
    llm_api_key: str = "replace_with_your_api_key"
    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
