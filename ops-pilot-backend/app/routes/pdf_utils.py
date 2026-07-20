from __future__ import annotations

from pathlib import Path


def is_pdf_magic(path: Path, magic: bytes = b"%PDF-") -> bool:
    with path.open("rb") as f:
        return f.read(len(magic)) == magic


def extract_pdf_pages(path: Path) -> int:
    """Return number of pages in a PDF.

    Uses pypdf (imported lazily).
    """

    from pypdf import PdfReader  # type: ignore

    reader = PdfReader(str(path))
    return len(reader.pages)

