"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central settings object – values are read from env vars / .env file."""

    # Telegram
    telegram_bot_token: str

    # Database
    database_url: str

    # Auth
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # CORS
    cors_origins: str = "*"

    # Ollama LLM (optional – for department classification)
    ollama_url: str = ""  # e.g. "http://ollama:11434"
    ollama_model: str = "gemma3:1b"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore[call-arg]
