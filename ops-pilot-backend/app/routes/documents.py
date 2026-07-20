from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.services.faiss_vector_store_service import FaissVectorStoreService, validate_index_name

router = APIRouter()


class DocumentSummary(BaseModel):
    # Client-side document id for the embedded document
    document_id: str = Field(..., description="Client-side document id")
    filename: str
    pages: int | None = Field(default=None, description="Optional; may be unknown if not tracked")


class DocumentsResponse(BaseModel):
    ok: bool
    index_name: str
    timestamp: str
    documents: List[DocumentSummary]


class DeleteDocumentResponse(BaseModel):
    ok: bool
    index_name: str
    document_id: str
    chunks_deleted: int
    timestamp: str


class PreviewDocumentResponse(BaseModel):
    ok: bool
    index_name: str
    document_id: str
    filename: str
    pages: list[dict[str, Any]]
    timestamp: str


def _vectorstore_base_dir() -> Path:
    return Path(settings.VECTORSTORE_BASE_DIR)


@router.get("/documents", response_model=DocumentsResponse, tags=["documents"])
def list_documents(index_name: str = "default") -> DocumentsResponse:
    try:
        validate_index_name(index_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Stored metadata lives at: {VECTORSTORE_BASE_DIR}/{index_name}/index_meta.json
    index_dir = _vectorstore_base_dir() / index_name
    meta_file = index_dir / "index_meta.json"

    if not meta_file.exists():
        # No index yet => empty list
        return DocumentsResponse(
            ok=True,
            index_name=index_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            documents=[],
        )

    try:
        meta: list[dict[str, Any]] = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read index metadata: {e}")

    # Deduplicate by document_id
    docs_by_id: dict[str, dict[str, Any]] = {}
    for md in meta:
        did = md.get("document_id")
        if not did:
            continue
        if did not in docs_by_id:
            docs_by_id[did] = {
                "document_id": did,
                "filename": md.get("filename") or "",
                "pages": md.get("document_pages"),
            }

    docs = [DocumentSummary(**d) for d in docs_by_id.values()]

    return DocumentsResponse(
        ok=True,
        index_name=index_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        documents=docs,
    )


@router.delete(
    "/documents/{index_name}/{document_id}",
    response_model=DeleteDocumentResponse,
    tags=["documents"],
)
def delete_document(index_name: str, document_id: str) -> DeleteDocumentResponse:
    """Delete all chunks belonging to a specific document from the vector store."""
    try:
        validate_index_name(index_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        faiss_store = FaissVectorStoreService(base_dir=settings.VECTORSTORE_BASE_DIR)
        chunks_deleted = faiss_store.delete_by_document_id(
            index_name=index_name,
            document_id=document_id,
        )
        return DeleteDocumentResponse(
            ok=True,
            index_name=index_name,
            document_id=document_id,
            chunks_deleted=chunks_deleted,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {e}")


@router.get(
    "/documents/{index_name}/{document_id}/preview",
    response_model=PreviewDocumentResponse,
    tags=["documents"],
)
def preview_document(index_name: str, document_id: str) -> PreviewDocumentResponse:
    """Preview the text content of all chunks belonging to a document."""
    try:
        validate_index_name(index_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    index_dir = _vectorstore_base_dir() / index_name
    meta_file = index_dir / "index_meta.json"

    if not meta_file.exists():
        raise HTTPException(status_code=404, detail=f"Index '{index_name}' not found")

    try:
        meta: list[dict[str, Any]] = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read index metadata: {e}")

    # Filter chunks belonging to this document
    doc_chunks = [md for md in meta if md.get("document_id") == document_id]

    if not doc_chunks:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_id}' not found in index '{index_name}'",
        )

    filename = doc_chunks[0].get("filename", "Unknown")

    # Group chunks by page
    pages_map: dict[int, list[dict[str, Any]]] = {}
    for chunk in doc_chunks:
        page = chunk.get("page") or chunk.get("page_number") or 1
        if page not in pages_map:
            pages_map[page] = []
        pages_map[page].append({
            "chunk_id": chunk.get("chunk_id"),
            "text": chunk.get("text", ""),
            "chunk_index": chunk.get("chunk_index"),
        })

    pages_list = [
        {"page_number": page, "chunks": chunks}
        for page, chunks in sorted(pages_map.items())
    ]

    return PreviewDocumentResponse(
        ok=True,
        index_name=index_name,
        document_id=document_id,
        filename=filename,
        pages=pages_list,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

