from __future__ import annotations

from functools import lru_cache
from typing import Optional

from app.config.settings import settings
import google.generativeai as genai


class GeminiTextService:
    """Service for generating text responses using the Gemini API.

    Uses the GEMINI_API_KEY from settings and a configurable model
    (default: gemini-2.0-flash) for chat-style answer generation.

    This class is a singleton — use GeminiTextService.get_instance()
    to reuse the same model instances across requests.
    """

    _instance: "GeminiTextService | None" = None

    def __new__(cls, *args, **kwargs) -> "GeminiTextService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = (
            model_name or settings.GEMINI_GEN_MODEL or "gemini-2.0-flash"
        )

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set it in your .env file."
            )

        genai.configure(api_key=self.api_key)

    @classmethod
    def get_instance(cls) -> "GeminiTextService":
        """Return a singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @lru_cache(maxsize=4)
    def _get_model(self, model_name: str):
        """Cache GenerativeModel instances by model name (max 4)."""
        return genai.GenerativeModel(model_name=model_name)

    def generate(
        self,
        *,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
    ) -> str:
        """Generate a text response from Gemini.

        Args:
            prompt: The user-facing prompt (includes context + question).
            system: Optional system instruction to constrain the model.
            model: Override the model name for this call.
            timeout: Maximum time in seconds to wait for the response.

        Returns:
            The generated text string.
        """
        mdl = model or self.model_name
        gen_model = self._get_model(mdl)

        generation_config = genai.types.GenerationConfig(
            max_output_tokens=2048,
            temperature=0.2,
            top_p=0.9,
        )

        try:
            if system:
                chat = gen_model.start_chat()
                response = chat.send_message(
                    f"{system}\n\n{prompt}",
                    generation_config=generation_config,
                )
            else:
                response = gen_model.generate_content(
                    [prompt],
                    generation_config=generation_config,
                )

            # Extract text safely
            if not response.candidates:
                return ""
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                return ""
            return "".join(part.text for part in candidate.content.parts if hasattr(part, "text"))

        except Exception as e:
            raise RuntimeError(f"Gemini generation failed: {e}") from e

