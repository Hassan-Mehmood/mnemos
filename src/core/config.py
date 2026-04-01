from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(...)
    DATABASE_URL: str = Field(...)
    GROQ_API_KEY: str = Field(...)
    HF_TOKEN: str = Field(...)

    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.2
    SEMANTIC_TOP_K: int = 5

    MEMORY_EXTRACTOR_MODEL: str = "gpt-5.4-nano"
    CHAT_BOT_MODEL: str = "gpt-4o-mini-2024-07-18"
    MEMORY_GATE_MODEL: str = "gpt-5.4-nano"

    EMBEDDING_DIMENSIONS: int = Field(1024, description="Qwen3-Embedding-0.6B")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()  # type: ignore
    return settings
