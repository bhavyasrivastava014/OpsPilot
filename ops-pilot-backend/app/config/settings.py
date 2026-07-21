import json
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[BACKEND_DIR / ".env", REPO_ROOT / ".env", ".env"],
        extra="ignore",
    )

    APP_NAME: str = Field(default="OpsPilot API")
    APP_VERSION: str = Field(default="0.1.0")

    PORT: int = Field(default=8000)

    # Gemini / Embeddings
    GEMINI_API_KEY: str | None = Field(default=None, description="Gemini API key (required for Gemini text generation)")
    GEMINI_GEN_MODEL: str = Field(
        default="gemini-2.0-flash",
        description="Gemini generation model name (e.g. gemini-2.0-flash, gemini-1.5-pro)",
    )
    GEMINI_EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence-transformers embedding model name",
    )

    # Vector store persistence
    VECTORSTORE_BASE_DIR: str = Field(default="app/vectorstores")

    # Conversation memory (in-memory per backend process)
    CHAT_MEMORY_MAX_TURNS: int = Field(default=12, description="Max stored chat turns per session (user+assistant entries)")

    # CORS

    # Comma-separated list, e.g. "http://localhost:5173,http://127.0.0.1:5173"
    CORS_ORIGINS: str = Field(default="")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default_factory=lambda: ["*"])

    def get_cors_origins(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return []
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
