from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config.settings import settings
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


class ChunkModel(BaseModel):
    chunk_id: str
    page: int | None = None
    chunk_index: int | None = None
    text: str


class DocumentModel(BaseModel):
    document_id: str = Field(..., description="Client-side id for the source document")
    filename: str
    chunks: List[ChunkModel]


class EmbedRequest(BaseModel):
    index_name: str = Field(default="default", description="FAISS index name")
    model: str = Field(
        default_factory=lambda: settings.GEMINI_EMBEDDING_MODEL,
        description="Gemini embedding model name",
    )
    documents: List[DocumentModel]


class EmbedResponse(BaseModel):
    ok: bool
    indexed: List[dict[str, Any]]
    index_name: str
    timestamp: str


@router.post("/embed", response_model=EmbedResponse, tags=["embed"])
def embed_documents(req: EmbedRequest) -> EmbedResponse:
    # Flatten chunks across multiple documents.
    flat_texts: list[str] = []
    flat_metadatas: list[dict[str, Any]] = []
    per_doc_indexed: list[dict[str, Any]] = []

    for doc in req.documents:
        doc_added = 0
        for ch in doc.chunks:
            text = (ch.text or "").strip()
            if not text:
                continue
            flat_texts.append(text)
            flat_metadatas.append(
                {
                    "document_id": doc.document_id,
                    "filename": doc.filename,
                    "chunk_id": ch.chunk_id,
                    "page": ch.page,
                    "chunk_index": ch.chunk_index,
                    "text": text,
                }
            )
            doc_added += 1

        per_doc_indexed.append(
            {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "chunks_added": doc_added,
            }
        )

    if not flat_texts:
        return EmbedResponse(
            ok=True,
            indexed=per_doc_indexed,
            index_name=req.index_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    try:
        gemini = _get_gemini_embed()
        vectors_result = gemini.embed_texts(texts=flat_texts, model=req.model)

        if len(vectors_result.vectors) != len(flat_metadatas):
            raise RuntimeError("Embedding generation returned unexpected number of vectors")

        faiss_store = _get_faiss_store()
        faiss_store.upsert(
            index_name=req.index_name,
            embeddings=vectors_result.vectors,
            metadatas=flat_metadatas,
        )

        return EmbedResponse(
            ok=True,
            indexed=per_doc_indexed,
            index_name=req.index_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to embed/index documents: {e}")
