# Mnemos Backend — Copilot Instructions

AI memory system: a persistent cognitive layer for LLMs with structured +
semantic memory, ranked retrieval, and contradiction-aware updates.

## Build & Run

```bash
# Install dependencies (uses uv)
uv sync

# Start PostgreSQL + pgAdmin
docker-compose up -d

# Apply DB migrations
alembic upgrade head

# Run dev server (reload enabled, port 8000)
python main.py

# Streamlit UI (early-stage, not integrated with current API)
streamlit run streamlit_app.py
```

**Required `.env` vars:**

```
OPENAI_API_KEY=
GROQ_API_KEY=
HF_TOKEN=
DATABASE_URL=postgresql+asyncpg://hassan:mypassword@localhost:5432/mnemos
```

## Architecture

**Request flow:**

```
User msg → ChatRouter → ChatService
  → MemoryGate (LLM: retrieve or skip?)
  → Memory retrieval (short-term + factual + semantic)
  → Chatbot streams response
  → Background: MemoryExtractor saves new facts
```

**Key modules in `src/`:**

| Module                    | Responsibility                                                                                             |
| ------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `chats/`                  | FastAPI routes, service orchestration, chat repository                                                     |
| `memory/`                 | Memory gate, extraction (pydantic-ai), retrieval ranking, embeddings (Qwen3-0.6B via SentenceTransformers) |
| `core/database/`          | SQLAlchemy 2.0 async ORM, Alembic migrations, models                                                       |
| `users/`                  | User CRUD                                                                                                  |
| `components/chatbot.py`   | Streaming + non-streaming LLM invocation                                                                   |
| `utils/system_prompts.py` | All LLM prompt strings                                                                                     |

See [src/core/database/models.py](../src/core/database/models.py) for the full
schema (User, Chat, ChatMessage, MemoryEmbedding, MemoryStructured, MemoryLog).

## Conventions

- **Fully async** — FastAPI, SQLAlchemy async sessions, asyncpg. Never block the
  event loop with sync I/O.
- **Repository pattern** — DB access lives in `*_repository.py` files; services
  call repos, not raw SQL.
- **UUID PKs** on all tables; use `uuid.uuid4()` for new records, never auto-int
  IDs.
- **pydantic-ai `Agent`** for LLM calls with structured output — see
  [memory_extractor.py](../src/memory/memory_extractor.py) for the pattern.
- **Pydantic schemas** for all request/response validation; keep in
  `*_schemas.py` alongside the router.
- **Background tasks** (`fastapi.BackgroundTasks`) for non-blocking
  post-response work (extraction, message saves).
- **`sessionmanager.session()`** context manager for DB sessions in background
  tasks — do not reuse request-scoped sessions.
- **Versioned memory** — structured memories use `superseded_by` FK +
  `confidence` float; never overwrite, only supersede.
- **Embedding dimensions** are fixed at `1024` (Qwen3-Embedding-0.6B). Changing
  the model requires a new migration.
- **Settings** are loaded via pydantic-settings + `.env` and cached with
  `@lru_cache()` — import via `get_settings()`.
- **Logging** — use `from src.core.logger import logger` (structured, not
  `print`).

## Critical Gotchas

1. **Memory retrieval is incomplete** —
   [memory_retriever.py](../src/memory/memory_retriever.py) doesn't yet use
   semantic scores in ranking; `factual=[]` is hardcoded. Don't assume retrieval
   is fully wired.
2. **Background task sessions** — each background task must open its own
   `async with sessionmanager.session()`. Sharing a request session across task
   boundaries will fail.
3. **HNSW index** (m=16, ef_construction=64) on `memory_embedding.embedding`.
   Changing `EMBEDDING_DIMENSIONS` requires dropping and recreating the index
   via migration.
4. **CORS is open** (`allow_origins=["*"]`) in [main.py](../main.py) — restrict
   before any public deployment.
5. **Streamlit app** uses hardcoded `chat_id=1` and is decoupled from the
   current API — treat it as a scratch pad.
