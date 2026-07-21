from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.routes.pdf_utils import is_pdf_magic
from app.services.faiss_vector_store_service import FaissVectorStoreService, validate_index_name
from app.services.gemini_embeddings_service import GeminiEmbeddingsService
from app.services.pdf_extraction_service import extract_pdf_pages_text
from app.services.recursive_text_splitter import build_chunks_with_metadata


router = APIRouter()
TMP_UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads" / "tmp"
PDF_MAGIC_HEADER = b"%PDF-"
EMBEDDING_BATCH_SIZE = 100

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


class IngestedDocument(BaseModel):
    document_id: str
    filename: str
    pages: int
    chunks_indexed: int


class IngestResponse(BaseModel):
    ok: bool = True
    index_name: str
    documents: list[IngestedDocument]
    timestamp: str


def _safe_filename(filename: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.basename(filename)) or "upload.pdf"


def _is_pdf(upload: UploadFile, filename: str) -> bool:
    content_type = (upload.content_type or "").lower()
    return filename.lower().endswith(".pdf") and content_type in {
        "application/pdf", "application/x-pdf", "application/octet-stream"
    }


@router.post("/ingest", response_model=IngestResponse, tags=["documents"])
async def ingest_documents(
    files: Annotated[list[UploadFile], File(...)],
    index_name: str = "default",
) -> IngestResponse:
    """Validate, extract, chunk, embed, and index uploaded PDFs in one request."""
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF is required")

    try:
        validate_index_name(index_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    TMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    all_texts: list[str] = []
    all_metadata: list[dict] = []
    documents: list[IngestedDocument] = []

    for upload in files:
        original_filename = upload.filename or ""
        safe_filename = _safe_filename(original_filename)
        if not _is_pdf(upload, safe_filename):
            raise HTTPException(status_code=400, detail=f"Only PDF files are allowed: {original_filename}")

        temp_path = TMP_UPLOAD_DIR / f"{uuid.uuid4().hex}__{safe_filename}"
        try:
            with temp_path.open("wb") as output:
                while data := await upload.read(1024 * 1024):
                    output.write(data)
            if not is_pdf_magic(temp_path, magic=PDF_MAGIC_HEADER):
                raise HTTPException(status_code=400, detail=f"Invalid PDF file: {original_filename}")

            pages = extract_pdf_pages_text(temp_path, filename=original_filename)
            if not pages:
                raise HTTPException(
                    status_code=422,
                    detail=f"No extractable text found in {original_filename}. Scanned PDFs need OCR support.",
                )
            chunks = build_chunks_with_metadata(pages=pages, filename=original_filename)
            if not chunks:
                raise HTTPException(status_code=422, detail=f"No text chunks could be created for {original_filename}")

            document_id = str(uuid.uuid4())
            page_count = len(pages)
            documents.append(IngestedDocument(
                document_id=document_id,
                filename=original_filename,
                pages=page_count,
                chunks_indexed=len(chunks),
            ))
            for chunk in chunks:
                all_texts.append(chunk["text"])
                all_metadata.append({
                    **chunk,
                    "document_id": document_id,
                    "document_pages": page_count,
                })
        finally:
            await upload.close()
            temp_path.unlink(missing_ok=True)

    try:
        embeddings_service = _get_gemini_embed()
        vectors: list[list[float]] = []
        for start in range(0, len(all_texts), EMBEDDING_BATCH_SIZE):
            batch = all_texts[start : start + EMBEDDING_BATCH_SIZE]
            vectors.extend(
                embeddings_service.embed_texts(
                    texts=batch, model=settings.GEMINI_EMBEDDING_MODEL
                ).vectors
            )
        _get_faiss_store().upsert(
            index_name=index_name, embeddings=vectors, metadatas=all_metadata
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to index PDFs: {exc}") from exc

    return IngestResponse(
        index_name=index_name,
        documents=documents,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
