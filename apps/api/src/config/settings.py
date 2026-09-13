
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "Unotusk API"
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)

    # Server settings
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/unotusk"
    )
    SYNC_DATABASE_URL: str | None = Field(
        default="postgresql://postgres:postgres@localhost:5432/unotusk"
    )

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Security
    AUTH_SECRET: str = Field(
        default="insecure-dev-secret-please-change-in-production-min-32-chars-long"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3005",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3005",
    ]

    # LLM Settings (Explicit Provider: 'claude', 'groq', 'offline')
    LLM_PROVIDER: str = Field(default="groq")

    # Anthropic / Claude LLM Settings
    ANTHROPIC_API_KEY: str | None = Field(default=None)
    ANTHROPIC_MODEL: str = Field(default="claude-3-5-sonnet-20241022")

    # Groq LLM Settings
    GROQ_API_KEY: str | None = Field(default=None)
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")

    # Context Budget
    CONTEXT_BUDGET_TOKENS: int = Field(default=16000)


settings = Settings()
