"""Bot configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central settings — values are read from env vars / .env file."""

    # Telegram
    telegram_bot_token: str

    # Database
    database_url: str

    # Gemini API (primary LLM — cloud, stronger model)
    gemini_api_key: str = ""  # Google AI Studio API key
    gemini_model: str = "gemini-2.0-flash"

    # Global LLM rate limit (requests per minute, across all backends)
    llm_rate_limit: int = 20

    # Ollama LLM (fallback — local, runs on the same machine)
    ollama_url: str = ""  # e.g. "http://ollama:11434"
    ollama_model: str = "gemma3:1b"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore[call-arg]
