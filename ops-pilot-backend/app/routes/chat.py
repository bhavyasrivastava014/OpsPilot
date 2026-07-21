from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.routes.retrieve import RetrievedChunk
from app.services.conversation_memory_service import ConversationMemoryService
from app.services.faiss_vector_store_service import FaissVectorStoreService
from app.services.gemini_embeddings_service import GeminiEmbeddingsService
from app.services.gemini_text_service import GeminiTextService


router = APIRouter()


FALLBACK_ANSWER = "I couldn't find that information in the uploaded documents."

memory_service = ConversationMemoryService(max_turns=settings.CHAT_MEMORY_MAX_TURNS)

# Singleton service instances
_faiss_store: FaissVectorStoreService | None = None
_gemini_embed: GeminiEmbeddingsService | None = None
_gemini_text: GeminiTextService | None = None


def _get_faiss_store() -> FaissVectorStoreService:
    global _faiss_store
    if _faiss_store is None:
        _faiss_store = FaissVectorStoreService(base_dir=settings.VECTORSTORE_BASE_DIR)
    return _faiss_store


def _get_gemini_embed() -> GeminiEmbeddingsService:
    global _gemini_embed
    if _gemini_embed is None:
        _gemini_embed = GeminiEmbeddingsService.get_instance()
    return _gemini_embed


def _get_gemini_text() -> GeminiTextService:
    global _gemini_text
    if _gemini_text is None:
        _gemini_text = GeminiTextService.get_instance()
    return _gemini_text


class ChatRequest(BaseModel):
    question: str = Field(..., description="User question")
    index_name: str = Field(default="default", description="FAISS index name")
    top_k: int = Field(default=4, ge=1, le=20)

    # Conversation session. If omitted, the server creates one and returns it.
    session_id: str | None = Field(default=None, description="Client session id for conversation memory")


    # Retriever embedding model (must match embed/indexing dim)
    embed_model: str = Field(
        default_factory=lambda: settings.GEMINI_EMBEDDING_MODEL,
        description="Gemini embedding model name",
    )

    # Gemini generation model
    gen_model: str = Field(
        default_factory=lambda: settings.GEMINI_GEN_MODEL,
        description="Gemini generation model name",
    )


class ChatSource(BaseModel):
    chunk_id: str | None = None
    filename: str | None = None
    page: int | None = None
    chunk_index: int | None = None
    text: str
    similarity_score: float


class ChatResponse(BaseModel):
    ok: bool
    timestamp: str
    question: str

    # Echoed/created session id so the client can keep the conversation.
    session_id: str

    index_name: str
    top_k: int

    answer: str
    sources: List[ChatSource]

    response_time_ms: int



def _to_context(chunks: List[RetrievedChunk]) -> str:
    if not chunks:
        return ""

    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        source_parts: list[str] = [f"[{index}]"]
        if chunk.filename:
            source_parts.append(chunk.filename)
        if chunk.page is not None:
            source_parts.append(f"page {chunk.page}")
        if chunk.chunk_index is not None:
            source_parts.append(f"chunk {chunk.chunk_index}")

        header = " | ".join(source_parts)
        parts.append(f"{header}\n{chunk.text}")

    return "\n\n".join(parts)


def _build_system_prompt() -> str:
    return (
        "You are a helpful assistant. Use only the provided context excerpts to answer the user's question. "
        "If the context does not contain enough information, say that you could not find the information."
    )


def _format_history_for_prompt(turns: list[dict[str, Any]]) -> str:
    """Format recent conversation turns to help follow-up references."""
    if not turns:
        return ""
    lines: list[str] = []
    for t in turns:
        role = t.get("role")
        content = t.get("content") or ""
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")
    return "\n".join(lines).strip()


def _build_retrieval_query(question: str, history: list[dict[str, Any]]) -> str:
    """Make a follow-up searchable while keeping final answers grounded in retrieved chunks."""
    previous_user_questions = [
        str(turn.get("content") or "")
        for turn in history
        if turn.get("role") == "user" and turn.get("content")
    ]
    if not previous_user_questions:
        return question
    return f"Previous question: {previous_user_questions[-1]}\nFollow-up question: {question}"



@router.post("/chat", response_model=ChatResponse, tags=["chat"])
def chat(req: ChatRequest) -> ChatResponse:
    start = time.perf_counter()

    # Get or create session
    session_id = req.session_id or memory_service.new_session_id()
    history = memory_service.get(session_id)


    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="question must be a non-empty string")

    # Use Gemini API for generation
    try:
        # Retriever: embed question -> FAISS search
        gemini_embed = _get_gemini_embed()
        retrieval_query = _build_retrieval_query(req.question, history)
        q_emb = gemini_embed.embed_texts(texts=[retrieval_query], model=req.embed_model).vectors[0]

        faiss_store = _get_faiss_store()
        hits = faiss_store.search(index_name=req.index_name, query_embedding=q_emb, top_k=req.top_k)

        # Convert to RetrievedChunk-like objects (reuse schema)
        chunks: list[RetrievedChunk] = []
        for h in hits:
            distance = float(h.get("distance", 0.0))
            # Same similarity mapping as retrieve.py
            similarity_score = 1.0 / (1.0 + float(distance))
            chunks.append(
                RetrievedChunk(
                    chunk_id=h.get("chunk_id"),
                    filename=h.get("filename"),
                    page=h.get("page"),
                    chunk_index=h.get("chunk_index"),
                    text=h.get("text") or "",
                    similarity_score=similarity_score,
                )
            )

        context = _to_context(chunks)
        if not context:
            answer = FALLBACK_ANSWER
        else:
            # Gemini: generate answer strictly from context
            # Build prompts
            system_prompt = _build_system_prompt()

            prompt = (
                "Conversation history is for resolving references only. It is not evidence.\n"
                f"Conversation history:\n{_format_history_for_prompt(history) or '(none)'}\n\n"
                f"Context excerpts:\n{context}\n\n"
                f"Question: {req.question}\n\n"
                "Provide the answer."
            )

            # Use Gemini API for answer generation
            gemini_text = _get_gemini_text()
            requested_model = req.gen_model or settings.GEMINI_GEN_MODEL
            try:
                text = gemini_text.generate(prompt=prompt, system=system_prompt, model=requested_model)
            except Exception as exc:
                raise

            answer = (text or "").strip()
            if not answer:
                answer = FALLBACK_ANSWER

        response_time_ms = int((time.perf_counter() - start) * 1000)

        # Map sources
        sources = [
            ChatSource(
                chunk_id=c.chunk_id,
                filename=c.filename,
                page=c.page,
                chunk_index=c.chunk_index,
                text=c.text,
                similarity_score=c.similarity_score,
            )
            for c in chunks
        ]

        # Store conversation turns after generating the answer
        memory_service.append_user_assistant_turns(
            session_id=session_id,
            user_content=req.question,
            assistant_content=answer,
        )

        return ChatResponse(
            ok=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
            question=req.question,
            session_id=session_id,
            index_name=req.index_name,
            top_k=req.top_k,
            answer=answer,
            sources=sources,
            response_time_ms=response_time_ms,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to chat: {e}")

