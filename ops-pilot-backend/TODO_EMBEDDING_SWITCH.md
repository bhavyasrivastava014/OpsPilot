# TODO: Switch embeddings from Gemini to sentence-transformers/all-MiniLM-L6-v2

- [x] Update `app/services/gemini_embeddings_service.py`:
  - [x] Replace Gemini embedding client with `sentence-transformers/all-MiniLM-L6-v2`
  - [x] Remove `get_gemini_startup_diagnostics`
  - [x] Remove Gemini embedding model discovery / fallback logic
  - [x] Preserve `EmbeddingResult` and `GeminiEmbeddingsService.embed_texts(texts, model)` signature/behavior (returns list[list[float]])
- [x] Update `app/main.py` to remove startup diagnostics import/print
- [x] Update `requirements.txt`:
  - [x] Remove `google-genai`
  - [x] Add `sentence-transformers`
- [x] Sanity check by importing the service and generating a small embedding

