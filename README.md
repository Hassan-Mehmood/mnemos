# Mnemos Backend

Mnemos is a personal AI assistant backend with a persistent memory layer. Every
conversation is used to learn facts about the user — and those facts are
recalled, ranked, and injected into future responses so the assistant always
knows who it's talking to.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Architecture Overview](#architecture-overview)
- [API Design: Router → Service → Repository](#api-design-router--service--repository)
- [The Memory Pipeline](#the-memory-pipeline)
- [Database Schema](#database-schema)
- [Configuration](#configuration)

---

## Getting Started

**Prerequisites:** Python (via `uv`), Docker, PostgreSQL.

```bash
# Install dependencies
uv sync

# Apply DB migrations
alembic upgrade head

# Run dev server (port 8000, reload enabled)
uv run main.py
```

**Required `.env` variables:**

```
OPENAI_API_KEY=
GROQ_API_KEY=
HF_TOKEN=
DATABASE_URL=
```

---

## Architecture Overview

```
src/
├── __init__.py              # FastAPI app, lifespan, CORS, router registration
├── chats/                   # Chat feature: router, service, repository, schemas
├── memory/                  # Full memory pipeline (gate → retrieval → extraction)
│   └── schemas/             # Pydantic output schemas for the extractor
├── components/
│   └── chatbot.py           # OpenAI streaming + non-streaming wrapper
├── core/
│   ├── config.py            # Pydantic settings (loaded via get_settings())
│   ├── logger.py            # Structured logger
│   └── database/
│       ├── database.py      # SQLAlchemy async engine + sessionmanager
│       ├── models.py        # ORM models
│       └── db_enums.py      # MessageSender enum
├── users/
│   └── user_repository.py   # Memory read/write operations for a user
└── utils/
    └── system_prompts.py    # All LLM prompt strings
```

The app is **fully async** end-to-end: FastAPI handles HTTP, SQLAlchemy uses
`asyncpg`, and all LLM calls are non-blocking. Heavy post-response work (memory
extraction, bot message saving) runs in FastAPI `BackgroundTasks` so the
streamed response reaches the client immediately.

---

## API Design: Router → Service → Repository

The codebase uses a strict three-layer pattern for all features.

### Router (`chat_router.py`)

The router is the HTTP boundary. It handles:

- Request validation via Pydantic schemas (`ChatInvoke`, etc.)
- Dependency injection of `ChatService` via `get_chat_service()`
- Returning `StreamingResponse` for chat invocations or wrapped
  `SuccessResponse[T]` for data endpoints
- Catching and re-raising `HTTPException` with appropriate status codes

Routers never touch the database directly.

**Endpoints:**

| Method   | Path               | Description                                      |
| -------- | ------------------ | ------------------------------------------------ |
| `POST`   | `/chats/invoke`    | Send a message; streams the assistant's response |
| `GET`    | `/chats`           | List all chats                                   |
| `GET`    | `/chats/{chat_id}` | Get all messages for a specific chat             |
| `DELETE` | `/chats/{chat_id}` | Delete a chat and all its messages               |
| `GET`    | `/health`          | Health check                                     |

### Service (`chat_service.py`)

The service layer holds all business logic. `ChatService` is responsible for:

1. Persisting the incoming user message via `ChatRepository`
2. Running the full memory retrieval pipeline via `MemoryRetriever`
3. Opening an async generator that streams the LLM response chunk by chunk
4. Scheduling two background tasks after streaming completes:
    - `MemoryExtractor.extract()` — mine new facts from the user's message
    - `ChatRepository.save_bot_message()` — persist the full response

The service owns no DB session itself — it receives injected repositories that
already hold a session.

### Repository

Raw database access is isolated to repository classes. Each repository takes an
`AsyncSession` in its constructor and exposes async methods for specific
queries. There are no raw SQL strings — everything uses SQLAlchemy 2.0 ORM.

| Repository            | Responsibility                                                |
| --------------------- | ------------------------------------------------------------- |
| `ChatRepository`      | CRUD for `Chat` and `ChatMessage`; fetch conversation history |
| `UserRepository`      | Read/write `MemoryStructured` and `MemoryEmbedding` records   |
| `MemoryLogRepository` | Write and update `MemoryLog` audit records                    |

Background tasks that need DB access open their own session with
`async with sessionmanager.session()` — they never reuse a request-scoped
session.

---

## The Memory Pipeline

This is the core of Mnemos. Every incoming message passes through the pipeline
before a response is generated, and every outgoing message triggers async
extraction after the response is sent.

### Full Request Flow

```
POST /chats/invoke
│
├── ChatRouter receives ChatInvoke { chat_id, user_id, message }
│
├── ChatService.invoke()
│   ├── 1. Save user message → get message_id
│   │
│   ├── 2. MemoryRetriever.retrieve()
│   │   ├── MemoryGate.should_retrieve(query)
│   │   │   ├── Layer 0: HARD_RETRIEVE_PATTERNS → force RETRIEVE
│   │   │   ├── Layer 1a: HARD_SKIP_PATTERNS → force SKIP
│   │   │   ├── Layer 1b: HARD_EXTRACT_PATTERNS → force RETRIEVE
│   │   │   └── Layer 2: LLM fallback (gpt-5.4-nano) → RETRIEVE or SKIP
│   │   │
│   │   ├── Log gate decision to MemoryLog
│   │   │
│   │   ├── ShortTermMemory: last ≤10 messages from ChatMessage table
│   │   │
│   │   ├── FactualMemory: all MemoryStructured rows where
│   │   │   confidence ≥ 0.8 AND superseded_by IS NULL
│   │   │   (token-budget capped at 800 tokens)
│   │   │
│   │   └── [if RETRIEVE] LongTermSemanticMemory:
│   │       ├── Embed query with Qwen3-0.6B (query mode, task-instruction prefix)
│   │       ├── Cosine similarity against all user MemoryEmbedding rows
│   │       ├── Score = similarity × time_decay × importance (confidence)
│   │       └── Return top-K results above SEMANTIC_SIMILARITY_THRESHOLD (0.2)
│   │
│   ├── Update MemoryLog with token count
│   │
│   ├── 3. chatbot.stream() — OpenAI streaming with memory injected into instructions
│   │   └── Yields chunks back to the client via StreamingResponse
│   │
│   └── [background] After stream completes:
│       ├── MemoryExtractor.extract(message, user_id)
│       │   ├── Fetch existing user memories for context
│       │   ├── LLM (gpt-5.4-nano) extracts KV pairs with confidence scores
│       │   └── Persist new MemoryStructured + MemoryEmbedding records
│       │       (old record's superseded_by is set to new record's id)
│       └── ChatRepository.save_bot_message()
```

### Stage 1: MemoryGate

The gate decides whether long-term semantic memory should be fetched for a given
query. It uses a three-tier approach to avoid unnecessary LLM calls:

1. **Hard Retrieve** — regex patterns that always force retrieval (e.g. "what's
   my name", "who am I")
2. **Hard Skip** — regex patterns for queries that obviously don't need personal
   context (knowledge questions, coding tasks, math)
3. **Hard Extract** — regex patterns that indicate personal statements worth
   storing but don't always need retrieval
4. **LLM fallback** — for ambiguous messages, a small `gpt-5.4-nano` agent gives
   a structured `RETRIEVE / SKIP` verdict

Short-term and factual memory are **always fetched** regardless of the gate
decision. Only semantic retrieval is gated.

### Stage 2: Short-Term Memory

Pulls the last ≤10 messages from the `ChatMessage` table for the current chat.
Always included. Appends the current user message to form the full conversation
history passed to the LLM.

### Stage 3: Factual Memory

Reads all `MemoryStructured` rows for the user where `confidence ≥ 0.8` and
`superseded_by IS NULL`. These are high-confidence explicit facts (e.g.
`preferred_language: Python`). Injected into the system prompt under a
`## Factual Memory` section, capped by a token budget (800 tokens by default).

### Stage 4: Long-Term Semantic Memory

Only runs when the gate returns `RETRIEVE`. Uses a singleton
`LongTermSemanticMemory` instance backed by **Qwen3-Embedding-0.6B** (1024-dim,
loaded once at startup):

- Documents are encoded at write-time in default mode
- Queries are encoded with a task-instruction prefix:
  `"Instruct: Given a user query, retrieve relevant personal facts\nQuery: ..."`
- Similarity is computed as cosine distance; results are re-ranked by
  `similarity × time_decay × importance`
- Top-K results (default 5) above a threshold (default 0.2) are injected as
  freeform strings

### Stage 5: Memory Extraction (Background)

After the response is fully streamed, `MemoryExtractor` runs as a background
task:

1. Fetches the user's existing memories from the DB for de-duplication context
2. Sends the user message + existing memories to a `pydantic-ai` Agent with
   `EXTRACTION_PROMPT`
3. The LLM returns a list of `{ key, value, confidence }` KV pairs — or `None`
   if nothing extractable
4. For each extracted fact:
    - If a record with the same `key` already exists (and
      `superseded_by IS NULL`), it is marked as superseded by setting its
      `superseded_by` to the new record's `id`
    - A new `MemoryStructured` row is inserted
    - A new `MemoryEmbedding` row is inserted with the embedding of
      `"key: value"`

This versioning approach means no memory is ever overwritten — the full history
is preserved via the `superseded_by` chain.

### Stage 6: MemoryLog (Audit)

Every message that goes through the pipeline creates a `MemoryLog` row
recording:

- The gate decision (`RETRIEVE` / `SKIP`) and the reason (which regex pattern or
  LLM verdict)
- The total memory token count injected into the prompt
- Foreign key to the `ChatMessage` row (cascade-deleted when the message is
  deleted)

---

## Database Schema

All tables use UUID primary keys.

```
User
  id, name, fullname, created_at, updated_at

Chat
  id, user_id (FK → User), name, last_message_at, created_at, updated_at

ChatMessage
  id, chat_id (FK → Chat), content, sender (USER|BOT), created_at, updated_at

MemoryStructured
  id, user_id (FK → User), key, value, confidence (0.0–1.0)
  superseded_by (nullable UUID — points to newer version of same fact)
  created_at, updated_at

MemoryEmbedding
  id, user_id (FK → User), memory_id (FK → MemoryStructured, NOT NULL)
  content (text), embedding (pgvector 1024-dim)
  HNSW index (m=16, ef_construction=64, cosine distance)
  created_at, updated_at

MemoryLog
  id, user_id, message_id (FK → ChatMessage, CASCADE DELETE)
  gate_decision, gate_reason, token_count
  created_at, updated_at
```

---

## Configuration

Settings are loaded from `.env` via `pydantic-settings` and cached with
`@lru_cache()`. Import with `get_settings()`.

| Variable                        | Default                  | Description                                          |
| ------------------------------- | ------------------------ | ---------------------------------------------------- |
| `CHAT_BOT_MODEL`                | `gpt-4o-mini-2024-07-18` | Model used for chat responses                        |
| `MEMORY_GATE_MODEL`             | `gpt-5.4-nano`           | Model for LLM gate fallback                          |
| `MEMORY_EXTRACTOR_MODEL`        | `gpt-5.4-nano`           | Model for memory extraction                          |
| `EMBEDDING_DIMENSIONS`          | `1024`                   | Must match Qwen3-Embedding-0.6B output               |
| `MEMORY_TOKEN_BUDGET`           | `800`                    | Max tokens allocated to factual memory injection     |
| `SEMANTIC_SIMILARITY_THRESHOLD` | `0.2`                    | Minimum cosine similarity score for semantic results |
| `SEMANTIC_TOP_K`                | `5`                      | Maximum number of semantic memory results to inject  |
