from __future__ import annotations

import json
from typing import Any, Optional

import requests

from app.config.settings import settings


class OllamaService:
    def __init__(self, *, url: Optional[str] = None, model: Optional[str] = None) -> None:
        self.url = (url or settings.OLLAMA_URL or "http://localhost:11434").rstrip("/")
        self.model = model or settings.OLLAMA_MODEL

    def generate(self, *, prompt: str, system: Optional[str] = None, model: Optional[str] = None, timeout: int = 60) -> str:
        mdl = model or self.model
        endpoint = f"{self.url}/api/generate"
        payload: dict[str, Any] = {"model": mdl, "prompt": prompt}
        if system:
            payload["system"] = system

        resp = requests.post(endpoint, json=payload, timeout=timeout)
        resp.raise_for_status()

        # Try to parse typical JSON shapes; otherwise return raw text
        try:
            data = resp.json()
        except Exception:
            return resp.text or ""

        # Common shapes: {"text": "..."} or {"output": "..."} or nested
        if isinstance(data, dict):
            if "text" in data and isinstance(data["text"], str):
                return data["text"]
            if "output" in data and isinstance(data["output"], str):
                return data["output"]
            # Ollama may return streaming outputs; try fallback keys
            if "results" in data and isinstance(data["results"], list) and data["results"]:
                try:
                    return json.dumps(data["results"])[:10000]
                except Exception:
                    return str(data["results"][0])

        # Fallback to stringified JSON or text
        try:
            return json.dumps(data)
        except Exception:
            return str(data)
