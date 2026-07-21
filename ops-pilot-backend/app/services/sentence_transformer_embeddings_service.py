from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.config.settings import settings

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover - optional dependency during import
    SentenceTransformer = None  # type: ignore[assignment]


@dataclass(frozen=True)
class EmbeddingResult:
    vectors: list[list[float]]


class GeminiEmbeddingsService:
    """Service for generating embeddings using SentenceTransformers.

    This class is a singleton — use GeminiEmbeddingsService.get_instance()
    to reuse the same model instances across requests.
    """

    _instance: "GeminiEmbeddingsService | None" = None

    def __init__(self, *, api_key: str | None = None, model_name: str | None = None) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model_name = (
            model_name
            or settings.GEMINI_EMBEDDING_MODEL
            or "sentence-transformers/all-MiniLM-L6-v2"
        )

    @classmethod
    def get_instance(cls) -> "GeminiEmbeddingsService":
        """Return a singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _resolve_model_name(self, *, model: str | None) -> str:
        candidate = (
            model
            or self.model_name
            or "sentence-transformers/all-MiniLM-L6-v2"
        ).strip()

        if not candidate:
            return "sentence-transformers/all-MiniLM-L6-v2"

        # Ignore old Gemini embedding model names
        if candidate.startswith("models/") or candidate.startswith("text-embedding-"):
            return "sentence-transformers/all-MiniLM-L6-v2"

        return candidate

    @lru_cache(maxsize=2)
    def _get_model(self, *, model: str) -> Any:
        """Cache SentenceTransformer models (max 2)."""
        resolved_model = self._resolve_model_name(model=model)

        global SentenceTransformer

        if SentenceTransformer is None:
            from sentence_transformers import (
                SentenceTransformer as ImportedSentenceTransformer,
            )

            SentenceTransformer = ImportedSentenceTransformer  # type: ignore[assignment]

        return SentenceTransformer(resolved_model)

    def embed_texts(self, *, texts: list[str], model: str) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(vectors=[])
        
        model_instance = self._get_model(model=model)
        embeddings = model_instance.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return EmbeddingResult(
            vectors=embeddings.tolist()
        )
