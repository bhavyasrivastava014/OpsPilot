from __future__ import annotations

import os
import re
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.routes.pdf_utils import is_pdf_magic
from app.services.pdf_extraction_service import extract_pdf_pages_text
from app.services.recursive_text_splitter import build_chunks_with_metadata


router = APIRouter()
# Backwards-compatible export expected by app/main.py
extract_router = router

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
        return False

    if filename.endswith(".pdf"):
        return True

    # Some clients may not supply .pdf extension; we do a magic header check after saving.
    return False


@router.post("/extract", tags=["extract"])
async def extract_pdfs(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    TMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    errors: list[dict] = []

    for upload in files:
        original_filename = upload.filename or ""
        safe_filename = _sanitize_filename(original_filename)
        ext = Path(safe_filename).suffix.lower()

        # Basic extension/MIME guard before we store anything.
        if ext != ".pdf":
            errors.append(
                {
                    "filename": original_filename,
                    "error": "Invalid file extension. Only .pdf is allowed.",
                }
            )
            continue

        if not _is_probably_pdf(upload):
            errors.append(
                {
                    "filename": original_filename,
                    "error": "Invalid content type. Only PDF files are allowed.",
                }
            )
            continue

        uid = uuid.uuid4().hex
        temp_path = TMP_UPLOAD_DIR / f"{uid}__{safe_filename}"
        size_bytes = 0

        try:
            # Stream to disk to avoid buffering entire file in memory.
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

            pages = extract_pdf_pages_text(temp_path, filename=original_filename)
            chunks = build_chunks_with_metadata(
                pages=pages,
                filename=original_filename,
                chunk_size=800,
                chunk_overlap=150,
            )

            results.append(
                {
                    "filename": original_filename,
                    "pages": pages,
                    "chunks": chunks,
                    "size": size_bytes,
                    "saved": {
                        "path": str(temp_path),
                        "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    },
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

