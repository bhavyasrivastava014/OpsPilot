from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.routes.embed import ChunkModel
from app.services.faiss_vector_store_service import FaissVectorStoreService
from app.services.gemini_embeddings_service import GeminiEmbeddingsService

router = APIRouter()

# Singleton instances
_faiss_store: FaissVectorStoreService | None = None
_gemini_embed: GeminiEmbeddingsService | None = None


def _get_faiss_store() -> FaissVectorStoreService:
    global _faiss_store
    if _faiss_store is None:
        _faiss_store = FaissVectorStoreService(base_dir=settings.VECTORSTORE_BASE_DIR)
    return _faiss_store


def _get_gemini_embed() -> GeminiEmbeddingsService:
    global _gemini_embed
    if _gemini_embed is None:
        _gemini_embed = GeminiEmbeddingsService.get_instance()
    return _gemini_embed


class RetrieveRequest(BaseModel):
    query: str = Field(..., description="User question to retrieve relevant chunks for")
    index_name: str = Field(default="default", description="FAISS index name")
    top_k: int = Field(default=4, ge=1, le=20)
    model: str = Field(
        default_factory=lambda: settings.GEMINI_EMBEDDING_MODEL,
        description="Gemini embedding model name",
    )


class RetrievedChunk(BaseModel):
    chunk_id: str | None = None
    filename: str | None = None
    page: int | None = None
    chunk_index: int | None = None
    text: str
    similarity_score: float


class RetrieveResponse(BaseModel):
    ok: bool
    index_name: str
    top_k: int
    timestamp: str
    query: str
    results: List[RetrievedChunk]


def _to_similarity_score_l2_lte_zero(distance: float) -> float:
    # IndexFlatL2 gives distance >= 0. Smaller distance => more similar.
    # Map to (0, 1].
    return 1.0 / (1.0 + float(distance))


@router.post("/retrieve", response_model=RetrieveResponse, tags=["retrieve"])
def retrieve(req: RetrieveRequest) -> RetrieveResponse:
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="query must be a non-empty string")

    try:
        gemini = _get_gemini_embed()
        emb = gemini.embed_texts(texts=[req.query], model=req.model).vectors[0]

        faiss_store = _get_faiss_store()
        hits = faiss_store.search(
            index_name=req.index_name,
            query_embedding=emb,
            top_k=req.top_k,
        )

        results: list[RetrievedChunk] = []
        for h in hits:
            distance = float(h.get("distance", 0.0))
            results.append(
                RetrievedChunk(
                    chunk_id=h.get("chunk_id"),
                    filename=h.get("filename"),
                    page=h.get("page"),
                    chunk_index=h.get("chunk_index"),
                    text=h.get("text") or "",
                    similarity_score=_to_similarity_score_l2_lte_zero(distance),
                )
            )

        return RetrieveResponse(
            ok=True,
            index_name=req.index_name,
            top_k=req.top_k,
            timestamp=datetime.now(timezone.utc).isoformat(),
            query=req.query,
            results=results,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chunks: {e}")
