from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


INDEX_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


def validate_index_name(index_name: str) -> str:
    if not INDEX_NAME_PATTERN.fullmatch(index_name):
        raise ValueError("index_name may contain only letters, numbers, underscores, and hyphens")
    return index_name


@dataclass(frozen=True)
class VectorStorePaths:
    index_dir: Path
    index_file: Path
    meta_file: Path


def get_vectorstore_paths(*, base_dir: str, index_name: str) -> VectorStorePaths:
    validate_index_name(index_name)
    base = Path(base_dir)
    index_dir = base / index_name
    return VectorStorePaths(
        index_dir=index_dir,
        index_file=index_dir / "index.faiss",
        meta_file=index_dir / "index_meta.json",
    )


class FaissVectorStoreService:
    """Minimal FAISS persistence layer.

    - Uses IndexFlatL2 for simplicity/determinism.
    - Stores metadata JSON keyed by vector position.

    Note: IndexFlatL2 doesn't require training.
    """

    def __init__(self, *, base_dir: str) -> None:
        self.base_dir = base_dir

        # Lazy import so startup doesn't fail if faiss isn't installed.
        import faiss  # type: ignore

        self.faiss = faiss

    def _load_meta(self, meta_file: Path) -> list[dict[str, Any]]:
        if not meta_file.exists():
            return []
        return json.loads(meta_file.read_text(encoding="utf-8"))

    def _save_meta(self, meta_file: Path, meta: list[dict[str, Any]]) -> None:
        meta_file.parent.mkdir(parents=True, exist_ok=True)
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert(
        self,
        *,
        index_name: str,
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> int:
        if not embeddings:
            return 0
        if len(embeddings) != len(metadatas):
            raise ValueError("embeddings and metadatas length mismatch")

        paths = get_vectorstore_paths(base_dir=self.base_dir, index_name=index_name)
        paths.index_dir.mkdir(parents=True, exist_ok=True)

        # Normalize embeddings to float32 2D array.
        x = np.asarray(embeddings, dtype=np.float32)
        if x.ndim != 2:
            raise ValueError("embeddings must be a list of vectors")

        dim = x.shape[1]

        index = None
        if paths.index_file.exists():
            index = self.faiss.read_index(str(paths.index_file))

            # Basic dimension check.
            if index.d != dim:
                raise RuntimeError(
                    f"Existing FAISS index dimension mismatch: index.d={index.d}, embeddings.d={dim}"
                )
        else:
            index = self.faiss.IndexFlatL2(dim)

        # Load existing metadata.
        existing_meta = self._load_meta(paths.meta_file)

        # Add vectors.
        index.add(x)

        # Append metadata for each new vector in order.
        start_pos = len(existing_meta)
        for i, md in enumerate(metadatas):
            md_with_pos = dict(md)
            md_with_pos["_vector_pos"] = start_pos + i
            existing_meta.append(md_with_pos)

        # Persist index + metadata.
        self.faiss.write_index(index, str(paths.index_file))
        self._save_meta(paths.meta_file, existing_meta)

        return len(metadatas)

    def search(
        self,
        *,
        index_name: str,
        query_embedding: list[float] | list[list[float]],
        top_k: int = 4,
    ) -> list[dict[str, Any]]:
        """Search the persisted FAISS index and return top-k hits.

        Returns a list of dicts that include:
          - _vector_pos
          - distance (FAISS L2 distance)
          - similarity_score (higher is better; computed outside by caller if desired)
          - any metadata fields stored in index_meta.json at that vector position
        """
        if top_k <= 0:
            return []

        paths = get_vectorstore_paths(base_dir=self.base_dir, index_name=index_name)
        if not paths.index_file.exists():
            return []

        meta = self._load_meta(paths.meta_file)
        if not meta:
            return []

        # Normalize query to shape (1, dim)
        q = np.asarray(query_embedding, dtype=np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)
        if q.ndim != 2 or q.shape[0] != 1:
            raise ValueError("query_embedding must be a single vector")

        index = self.faiss.read_index(str(paths.index_file))
        if index.d != q.shape[1]:
            raise RuntimeError(
                f"Query embedding dimension mismatch: index.d={index.d}, query.d={q.shape[1]}"
            )

        k = min(top_k, index.ntotal)
        distances, positions = index.search(q, k)

        # Build lookup by vector position for stable mapping.
        pos_to_meta: dict[int, dict[str, Any]] = {}
        for md in meta:
            vp = md.get("_vector_pos")
            if vp is None:
                continue
            pos_to_meta[int(vp)] = md

        out: list[dict[str, Any]] = []
        for dist, pos in zip(distances[0].tolist(), positions[0].tolist()):
            if pos == -1:
                continue
            md = pos_to_meta.get(int(pos), {})
            out.append(
                {
                    "_vector_pos": int(pos),
                    "distance": float(dist),
                    **md,
                }
            )

        return out


