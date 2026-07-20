<div align="center">
  <h1>📄 OpsPilot</h1>
  <p><strong>AI-Powered Document Q&A Assistant</strong></p>
  <p>Upload PDFs, ask questions, get answers grounded in your documents.</p>
</div>

---

## Features

- ** PDF Upload & Ingestion** — Upload multiple PDFs, automatically extract text, chunk, embed, and index them
- ** Intelligent Q&A** — Ask questions about your documents, get answers with cited sources
- ** Source Attribution** — Every answer shows which document, page, and chunk the information came from
- ** Conversation Memory** — Follow-up questions use conversation history for context
- ** Document Management** — Preview document text content and delete documents from the index
- ** Fast Vector Search** — Powered by FAISS (Facebook AI Similarity Search) for sub-second retrieval
- ** Local Embeddings** — Uses SentenceTransformers for offline embedding generation (no API costs)

---

## Architecture

```
┌──────────────────┐        ┌──────────────────────────────┐
│   React Frontend │  ──►   │     FastAPI Backend           │
│   (Vite + TS)    │  proxy │                              │
│                  │        │  ┌─ Upload & Ingest ───────┐ │
│  ┌────────────┐  │        │  │ PDF → Extract → Chunk  │ │
│  │ Chat Panel │  │        │  │ → Embed → FAISS Index   │ │
│  └────────────┘  │        │  └────────────────────────┘ │
│  ┌────────────┐  │        │  ┌─ Chat ─────────────────┐ │
│  │ Documents  │  │        │  │ Query → Embed → Search │ │
│  │ Panel      │  │        │  │ → Build Context → LLM  │ │
│  └────────────┘  │        │  └────────────────────────┘ │
│                  │        │  ┌─ Management ───────────┐ │
│                  │        │  │ List / Preview / Delete │ │
│                  │        │  └────────────────────────┘ │
└──────────────────┘        └──────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS |
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **Embeddings** | SentenceTransformers (`all-MiniLM-L6-v2`) |
| **Vector Store** | FAISS (IndexFlatL2) |
| **LLM** | Google Gemini API (or Ollama for local) |
| **PDF Parsing** | PyPDF |

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Google Gemini API key (for chat / optional)

### 1. Clone & Setup Backend

```bash
# Clone the repo
git clone https://github.com/your-username/opspilot.git
cd opspilot

# Setup backend
cd ops-pilot-backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt

# Create .env file (copy from .env.example)
# Add your Gemini API key
echo "GEMINI_API_KEY=your_key_here" > .env
echo "CORS_ORIGINS=http://localhost:5173" >> .env
```

### 2. Start Backend Server

```bash
cd ops-pilot-backend
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. 
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### 3. Setup & Start Frontend

```bash
cd ops-pilot
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

> **Note:** During development, the Vite proxy forwards `/api/*` requests to `http://127.0.0.1:8000`.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/ingest` | Upload & index PDFs |
| `POST` | `/chat` | Ask a question (with context) |
| `GET` | `/documents` | List indexed documents |
| `DELETE` | `/documents/{index}/{doc_id}` | Delete a document |
| `GET` | `/documents/{index}/{doc_id}/preview` | Preview document text |
| `POST` | `/retrieve` | Search chunks by query |
| `POST` | `/upload` | Upload PDFs (manual pipeline) |

### Chat Request Example

```json
POST /chat
{
  "question": "What are the key terms of service?",
  "index_name": "default",
  "top_k": 4,
  "session_id": null
}
```

### Chat Response Example

```json
{
  "ok": true,
  "answer": "The key terms include...",
  "sources": [
    {
      "filename": "terms.pdf",
      "page": 3,
      "text": "Section 2.1 outlines...",
      "similarity_score": 0.92
    }
  ],
  "session_id": "abc-123",
  "response_time_ms": 1450
}
```

---

## Deployment

### Frontend → Vercel

1. Create a new Vercel project from your repository
2. Set **Root Directory** to `ops-pilot/`
3. Framework preset: **Vite**
4. Add environment variable:
   - `VITE_API_BASE_URL` = your Render backend URL (e.g., `https://your-app.onrender.com`)
5. Deploy

### Backend → Render (Docker)

1. Create a **Web Service** on Render
2. Set **Root Directory** to `ops-pilot-backend/`
3. Runtime: **Docker**
4. Add environment variables:
   - `GEMINI_API_KEY` — Your Google Gemini API key
   - `CORS_ORIGINS` — Your Vercel frontend URL (e.g., `https://your-app.vercel.app`)
   - `PORT` — `8000`
5. Deploy

---

## Configuration

All configuration is through environment variables (see `ops-pilot-backend/app/config/settings.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | `None` | Google Gemini API key |
| `GEMINI_GEN_MODEL` | `gemini-2.0-flash` | Gemini model for chat |
| `GEMINI_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `CORS_ORIGINS` | `""` | Comma-separated allowed origins |
| `VECTORSTORE_BASE_DIR` | `app/vectorstores` | FAISS index storage path |
| `CHAT_MEMORY_MAX_TURNS` | `12` | Conversation history turns |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL (optional) |
| `OLLAMA_MODEL` | `mistral-7b-instruct` | Ollama model name (optional) |

---

## Project Structure

```
ops-pilot/
├── ops-pilot/                    # Frontend (React + Vite)
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/            # Chat panel, input, sources
│   │   │   ├── documents/       # Document list, cards, preview
│   │   │   └── layout/          # App layout, sidebar, topbar
│   │   ├── services/            # API client functions
│   │   ├── pages/               # Route pages
│   │   └── types/               # Shared TypeScript types
│   ├── Dockerfile
│   └── vite.config.ts
│
├── ops-pilot-backend/            # Backend (FastAPI)
│   ├── app/
│   │   ├── routes/              # API route handlers
│   │   │   ├── chat.py          # Chat endpoint
│   │   │   ├── documents.py     # Document management
│   │   │   ├── ingest.py        # PDF upload & index
│   │   │   └── ...
│   │   ├── services/            # Core business logic
│   │   │   ├── gemini_text_service.py
│   │   │   ├── sentence_transformer_embeddings_service.py
│   │   │   ├── faiss_vector_store_service.py
│   │   │   ├── pdf_extraction_service.py
│   │   │   └── conversation_memory_service.py
│   │   ├── config/
│   │   │   └── settings.py      # Environment config
│   │   └── main.py              # App entry point
│   ├── Dockerfile
│   └── requirements.txt
│
├── .gitignore
└── README.md
```

---

## 📝 Notes

- **FAISS is single-instance** — For production with multiple backend replicas, replace with Qdrant, Pinecone, or Weaviate
- **Memory is in-process** — Conversation history resets if the backend restarts. Use Redis for persistence
- **Gemini Free Tier** — Has rate limits. Enable billing on your API key for production use
- **SentenceTransformers** — Downloads ~80MB model on first use. For Docker, pre-download it in the Dockerfile to avoid cold starts
