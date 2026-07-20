from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    filename: str
    page: int
    chunk_index: int
    text: str

    def to_json(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "page": self.page,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
        }


class RecursiveCharacterTextSplitter:
    """Simple, dependency-free implementation inspired by LangChain's
    RecursiveCharacterTextSplitter.

    Chunking strategy:
    - Recursively split on separators from coarse -> fine until the segment
      length is <= chunk_size.
    - Enforces overlap by sliding a window over the flattened text chunks.

    This implementation is deterministic and designed for service usage.
    """

    def __init__(
        self,
        *,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        separators: list[str] | None = None,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be < chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def _split_by_separator(self, text: str, separator: str) -> list[str]:
        if separator == "":
            # final fallback: hard split into characters
            return list(text)
        return text.split(separator)

    def _recursive_split(self, text: str, *, separator_idx: int = 0) -> list[str]:
        text = text
        if len(text) <= self.chunk_size:
            return [text]

        # If we've exhausted separators, hard cut.
        if separator_idx >= len(self.separators):
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        sep = self.separators[separator_idx]
        parts = self._split_by_separator(text, sep)

        # If separator didn't actually split, go deeper.
        if len(parts) <= 1:
            return self._recursive_split(text, separator_idx=separator_idx + 1)

        # Recombine parts using separator boundaries to preserve structure.
        # Example: for sep='\n', join with '\n' between parts.
        recombined: list[str] = []
        for idx, p in enumerate(parts):
            if sep == "":
                recombined.append(p)
            else:
                if idx < len(parts) - 1:
                    recombined.append(p + sep)
                else:
                    recombined.append(p)

        # Now recursively split any overlong recombined segments.
        out: list[str] = []
        for seg in recombined:
            if not seg:
                continue
            if len(seg) <= self.chunk_size:
                out.append(seg)
            else:
                out.extend(self._recursive_split(seg, separator_idx=separator_idx + 1))
        return out

    def _apply_overlap(self, segments: Iterable[str]) -> list[str]:
        # Flatten segments into one stream, then window it with overlap.
        # This keeps chunk sizes controlled.
        flat = "".join(segments)
        if not flat:
            return []

        chunks: list[str] = []
        step = self.chunk_size - self.chunk_overlap
        for start in range(0, len(flat), step):
            end = start + self.chunk_size
            chunk = flat[start:end]
            if chunk:
                chunks.append(chunk)
            if end >= len(flat):
                break
        return chunks

    def split_text(self, text: str) -> list[str]:
        segments = self._recursive_split(text, separator_idx=0)
        return self._apply_overlap(segments)


def build_chunks_with_metadata(
    *,
    pages: list[dict[str, Any]],
    filename: str | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[dict[str, Any]]:
    """Create chunk list from extracted pages.

    Input expected per page:
      { "filename": <optional>, "page_number": <1-based>, "text": <page_text> }

    Output chunk metadata attached:
      - Filename
      - Page
      - Chunk id
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks: list[dict[str, Any]] = []
    for page_i, page in enumerate(pages):
        page_num = int(page.get("page_number") or page.get("page") or page_i + 1)
        page_filename = filename or page.get("filename") or ""
        text = page.get("text") or ""

        page_chunks = splitter.split_text(text)
        for chunk_index, chunk_text in enumerate(page_chunks):
            # deterministic id: filename + page + index
            chunk_id = f"{page_filename}::p{page_num}::c{chunk_index}"
            chunks.append(
                TextChunk(
                    chunk_id=chunk_id,
                    filename=page_filename,
                    page=page_num,
                    chunk_index=chunk_index,
                    text=chunk_text,
                ).to_json()
            )

    return chunks

