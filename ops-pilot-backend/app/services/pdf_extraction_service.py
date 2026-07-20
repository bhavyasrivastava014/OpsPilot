from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExtractedPage:
    filename: str
    page_number: int  # 1-based
    text: str

    def to_json(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "page_number": self.page_number,
            "text": self.text,
        }


def _is_blank_text(text: str) -> bool:
    # Treat page as blank if, after trimming, nothing is left.
    return not text or not text.strip()


def extract_pdf_pages_text(path: Path, *, filename: str) -> list[dict[str, Any]]:
    """Extract non-blank pages from a PDF.

    Uses pypdf.

    Returns a list of objects:
      { "filename": <original filename>, "page_number": <1-based>, "text": <extracted> }

    Blank pages are ignored.
    """

    from pypdf import PdfReader  # type: ignore

    reader = PdfReader(str(path))
    try:
        extracted: list[dict[str, Any]] = []
        for i, page in enumerate(reader.pages):
            page_number = i + 1
            text = page.extract_text() or ""
            if _is_blank_text(text):
                continue

            extracted.append(
                ExtractedPage(filename=filename, page_number=page_number, text=text).to_json()
            )

        return extracted
    finally:
        reader = None

