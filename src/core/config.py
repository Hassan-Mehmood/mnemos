from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(...)
    DATABASE_URL: str = Field(...)
    GROQ_API_KEY: str = Field(...)
    HF_TOKEN: str = Field(...)

    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.2
    SEMANTIC_TOP_K: int = 5
    MEMORY_TOKEN_BUDGET: int = 800

    MEMORY_EXTRACTOR_MODEL: str = "gpt-5.4-nano"
    CHAT_BOT_MODEL: str = "gpt-4o-mini-2024-07-18"
    MEMORY_GATE_MODEL: str = "gpt-5.4-nano"

    EMBEDDING_DIMENSIONS: int = Field(1024, description="Qwen3-Embedding-0.6B")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def jwt_secret_key_min_length(cls, v: str) -> str:
        if len(v.encode("utf-8")) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 bytes (use `secrets.token_hex(32)` to generate one)"
            )
        return v


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()  # type: ignore
    return settings
