"""Bot configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central settings — values are read from env vars / .env file."""

    # Telegram
    telegram_bot_token: str

    # Database
    database_url: str

    # Ollama LLM (optional – for smart department classification)
    ollama_url: str = ""  # e.g. "http://ollama:11434"
    ollama_model: str = "gemma3:1b"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore[call-arg]
