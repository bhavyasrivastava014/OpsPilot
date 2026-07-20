from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.routes.pdf_utils import extract_pdf_pages, is_pdf_magic
from app.services.faiss_vector_store_service import FaissVectorStoreService
from app.services.gemini_embeddings_service import GeminiEmbeddingsService
from app.services.pdf_extraction_service import extract_pdf_pages_text
from app.services.recursive_text_splitter import build_chunks_with_metadata

# Embed-time models are defined in app/routes/embed.py
from app.routes.embed import ChunkModel

router = APIRouter()

# Keep temp files isolated under backend/app/uploads/tmp
BASE_DIR = Path(__file__).resolve().parents[1]
TMP_UPLOAD_DIR = BASE_DIR / "uploads" / "tmp"

PDF_MAGIC_HEADER = b"%PDF-"


def _sanitize_filename(filename: str) -> str:
    # Keep basename only; strip path components.
    base = os.path.basename(filename)
    # Replace anything unsafe.
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    # Avoid empty names
    return base or "upload.pdf"


def _is_probably_pdf(upload: UploadFile) -> bool:
    # Best-effort: check content type (client controlled) + extension
    content_type = (upload.content_type or "").lower()
    filename = (upload.filename or "").lower()
    if content_type not in {"application/pdf", "application/x-pdf", "application/octet-stream"}:
        # Still allow octet-stream (some clients don't send the right MIME).
        return False

    if filename.endswith(".pdf"):
        return True

    # Some clients may not supply .pdf extension; we do a magic header check after saving.
    return False


def _extract_pdf_pages_with_error_handling(path: Path) -> int:
    try:
        return extract_pdf_pages(path)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to read PDF pages: {e}")


def _document_id_from_filename(original_filename: str) -> str:
    # documents.py expects `document_id` in index_meta.json.
    # We keep it deterministic.
    return f"doc::{os.path.basename(original_filename)}"


@router.post("/upload", tags=["upload"])
async def upload_pdfs(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    TMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    errors: list[dict] = []

    # Create embedding service and FAISS store once (if available)
    try:
        gemini = GeminiEmbeddingsService()
        faiss_store = FaissVectorStoreService(base_dir=settings.VECTORSTORE_BASE_DIR)
    except Exception:
        # We'll create them later once we successfully validate at least one PDF.
        gemini = None
        faiss_store = None

    # Import settings lazily to avoid cycles
    from app.config.settings import settings

    for upload in files:
        original_filename = upload.filename or ""
        safe_filename = _sanitize_filename(original_filename)
        ext = Path(safe_filename).suffix.lower()

        if ext != ".pdf":
            errors.append({"filename": original_filename, "error": "Invalid file extension. Only .pdf is allowed."})
            continue

        if not _is_probably_pdf(upload):
            errors.append({"filename": original_filename, "error": "Invalid content type. Only PDF files are allowed."})
            continue

        uid = uuid.uuid4().hex
        temp_path = TMP_UPLOAD_DIR / f"{uid}__{safe_filename}"
        size_bytes = 0

        try:
            with temp_path.open("wb") as f:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    size_bytes += len(chunk)
                    f.write(chunk)

            # Verify PDF magic header.
            if not is_pdf_magic(temp_path, magic=PDF_MAGIC_HEADER):
                raise HTTPException(
                    status_code=400,
                    detail=f"File is not a valid PDF (missing %PDF- header): {original_filename}",
                )

            pages = _extract_pdf_pages_with_error_handling(temp_path)

            # --- Full pipeline (extract -> chunk -> embed -> store) ---
            # Ensure Gemini + FAISS are ready only when needed.
            if gemini is None:
                gemini = GeminiEmbeddingsService()
            if faiss_store is None:
                faiss_store = FaissVectorStoreService(base_dir=settings.VECTORSTORE_BASE_DIR)

            extracted_pages = extract_pdf_pages_text(temp_path, filename=original_filename)
            chunk_dicts = build_chunks_with_metadata(
                pages=extracted_pages,
                filename=original_filename,
                chunk_size=800,
                chunk_overlap=150,
            )

            chunks: list[ChunkModel] = []
            for c in chunk_dicts:
                chunks.append(
                    ChunkModel(
                        chunk_id=c["chunk_id"],
                        page=c.get("page"),
                        chunk_index=c.get("chunk_index"),
                        text=c.get("text") or "",
                    )
                )

            document_id = _document_id_from_filename(original_filename)

            texts = [c.text for c in chunks if (c.text or "").strip()]
            if texts:
                vectors_result = gemini.embed_texts(texts=texts, model=settings.GEMINI_EMBEDDING_MODEL)

                metadatas: list[dict] = []
                i = 0
                for c in chunks:
                    if not (c.text or "").strip():
                        continue
                    metadatas.append(
                        {
                            "document_id": document_id,
                            "filename": original_filename,
                            "chunk_id": c.chunk_id,
                            "page": c.page,
                            "chunk_index": c.chunk_index,
                            "text": c.text,
                        }
                    )
                    i += 1

                faiss_store.upsert(
                    index_name="default",
                    embeddings=vectors_result.vectors,
                    metadatas=metadatas,
                )

            results.append(
                {
                    "filename": original_filename,
                    "pages": pages,
                    "size": size_bytes,
                    "saved": {
                        "path": str(temp_path),
                        "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "indexed": bool(texts),
                }
            )

        except HTTPException as he:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            errors.append({"filename": original_filename, "error": he.detail})
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            errors.append({"filename": original_filename, "error": str(e)})
        finally:
            await upload.close()

    if errors:
        return JSONResponse(status_code=400, content={"ok": False, "errors": errors})

    return {"ok": True, "files": results}

