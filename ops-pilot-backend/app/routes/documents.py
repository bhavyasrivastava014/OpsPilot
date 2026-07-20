from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.services.faiss_vector_store_service import validate_index_name

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

