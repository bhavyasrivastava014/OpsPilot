from __future__ import annotations

from typing import Optional

import google.generativeai as genai

from app.config.settings import settings


class GeminiTextService:
    """Service for generating text responses using the Gemini API.

    Uses the GEMINI_API_KEY from settings and a configurable model
    (default: gemini-2.0-flash) for chat-style answer generation.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = (
            model_name or settings.GEMINI_GEN_MODEL or "gemini-2.0-flash"
        )

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set it in your .env file."
            )

        genai.configure(api_key=self.api_key)

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
        gen_model = genai.GenerativeModel(model_name=mdl)

        # Build contents: system instruction + user prompt
        contents = [prompt]
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=2048,
            temperature=0.2,
            top_p=0.9,
        )

        try:
            if system:
                # Use chat session with system instruction
                chat = gen_model.start_chat()
                if system:
                    # Prepend system instruction as a user message with context
                    # because Gemini API doesn't have native 'system' role.
                    # We instruct the model in the first turn.
                    response = chat.send_message(
                        f"{system}\n\n{prompt}",
                        generation_config=generation_config,
                    )
                else:
                    response = chat.send_message(
                        prompt,
                        generation_config=generation_config,
                    )
            else:
                response = gen_model.generate_content(
                    contents,
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

