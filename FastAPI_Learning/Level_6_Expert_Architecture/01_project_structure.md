# Level 6 — Production Project Structure

## The Golden Rule

**Every file should have one job.**
When a file does two things, it is twice as hard to test, debug, and understand.

---

## Recommended Folder Structure (Full Production App)

```
my_ai_app/
│
├── main.py                  # App factory ONLY — no business logic here
├── config.py                # All settings via pydantic-settings
├── database.py              # Engine, session factory, get_db dependency
│
├── models/                  # SQLAlchemy ORM models (one file per domain)
│   ├── __init__.py
│   ├── user.py
│   ├── task.py
│   └── document.py          # Document + DocumentChunk with pgvector
│
├── schemas/                 # Pydantic schemas (Input/Output strictly separated)
│   ├── __init__.py
│   ├── user.py              # UserCreate, UserOut, UserUpdate
│   ├── task.py              # TaskCreate, TaskOut, TaskListOut
│   └── rag.py               # RAGQueryRequest, RAGQueryResponse, SourceChunk
│
├── crud/                    # Data access layer (NO HTTP logic here)
│   ├── __init__.py
│   ├── user.py              # create_user, get_user_by_id, verify_password
│   ├── task.py              # create_task, get_tasks, update_task, delete_task
│   └── document.py          # create_chunk, search_similar_chunks
│
├── services/                # Business logic (orchestrates crud + external APIs)
│   ├── __init__.py
│   ├── auth.py              # create_token, decode_token, hash logic
│   ├── embedding.py         # Embedding model wrapper
│   ├── llm.py               # LLM client with retry + streaming
│   └── rag.py               # Full RAG pipeline: embed → retrieve → prompt → generate
│
├── routers/                 # FastAPI route handlers (thin — call services)
│   ├── __init__.py
│   ├── auth.py              # /auth/register, /auth/login, /auth/refresh
│   ├── users.py             # /users/me, /users/{id}
│   ├── tasks.py             # /tasks CRUD
│   └── rag.py               # /rag/query, /rag/ingest, /rag/documents
│
├── dependencies/            # Reusable FastAPI Depends() functions
│   ├── __init__.py
│   ├── auth.py              # get_current_user, require_admin, require_role
│   └── rate_limit.py        # rate_limit(), get_user_rate_limiter()
│
├── middleware/              # Custom middleware
│   ├── __init__.py
│   ├── logging.py           # RequestLoggingMiddleware
│   └── security.py          # SecurityHeadersMiddleware
│
├── background/              # Background task functions
│   ├── __init__.py
│   └── ingestion.py         # index_document(), send_welcome_email()
│
├── tests/                   # All tests mirror the source structure
│   ├── conftest.py          # Shared fixtures (test DB, test client, test users)
│   ├── test_auth.py
│   ├── test_tasks.py
│   └── test_rag.py
│
├── alembic/                 # Database migrations (schema versioning)
│   ├── versions/
│   └── env.py
│
├── .env                     # Local secrets (NEVER commit to git)
├── .env.example             # Template with fake values (commit this)
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## The Layered Architecture (Data Flow)

```
HTTP Request
    │
    ▼
[Router]        — Receives HTTP, validates with schemas, calls service
    │
    ▼
[Service]       — Orchestrates: call crud + call LLM + call embedding model
    │
    ▼
[CRUD]          — All database queries, returns ORM objects
    │
    ▼
[Database]      — PostgreSQL (via SQLAlchemy async engine)
    │
    ▼
[Schema]        — Pydantic converts ORM object → JSON for the response
    │
    ▼
HTTP Response
```

---

## main.py Pattern (App Factory)

```python
# main.py — this is ALL that belongs here
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import get_settings
from database import setup_pgvector, create_tables
from middleware.logging import RequestLoggingMiddleware
from middleware.security import SecurityHeadersMiddleware
from routers import auth, users, tasks, rag

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: runs once when the server starts
    await setup_pgvector()
    await create_tables()
    yield
    # Shutdown: runs when the server stops (close connections, etc.)

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, ...)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
app.include_router(rag.router, prefix="/rag", tags=["RAG"])
```

---

## Router Pattern (Thin Routes)

```python
# routers/tasks.py — routes should be thin
from fastapi import APIRouter, Depends
from dependencies.auth import AuthUser, DB
from services import task_service
from schemas.task import TaskCreate, TaskOut, TaskListOut

router = APIRouter()

@router.post("/", response_model=TaskOut, status_code=201)
async def create_task(task: TaskCreate, user: AuthUser, db: DB):
    # Routes call services, not CRUD directly
    return await task_service.create(db, task, user.id)

@router.get("/", response_model=TaskListOut)
async def list_tasks(page: int = 1, user: AuthUser = ..., db: DB = ...):
    return await task_service.list_for_user(db, user.id, page)
```

---

## Naming Conventions

| Layer | Pattern | Example |
|-------|---------|---------|
| Router | noun (resource name) | `tasks.py`, `users.py` |
| Schema | `{Resource}{Action}` | `TaskCreate`, `TaskOut`, `TaskUpdate` |
| CRUD function | `verb_noun` | `create_task`, `get_tasks`, `delete_task` |
| Service function | `verb_noun` or `action` | `process_document`, `rag_query` |
| Dependency | `get_` prefix | `get_current_user`, `get_db` |

---

## Alembic Migration Workflow

```bash
# 1. Install Alembic
pip install alembic

# 2. Initialize (once per project)
alembic init alembic

# 3. After changing models.py, generate a migration
alembic revision --autogenerate -m "add documents table"

# 4. Apply the migration
alembic upgrade head

# 5. Rollback one step
alembic downgrade -1
```

Alembic creates versioned migration files.
Every schema change is tracked and reversible.
This is how professional teams manage database evolution.
