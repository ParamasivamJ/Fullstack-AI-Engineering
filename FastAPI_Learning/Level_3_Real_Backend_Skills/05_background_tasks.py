"""
Level 3 — Background Tasks and Async
======================================

Two of the most important concepts for AI apps:

BACKGROUND TASKS: Run work AFTER you return the response.
  → User uploads a PDF → return "Received!" immediately
  → THEN index the PDF in the background (takes 5–10 seconds)
  → User is not stuck waiting

ASYNC: Run I/O-bound work (HTTP calls, DB queries) without blocking the server.
  → Without async: calling the OpenAI API blocks ALL other requests for 2–3 seconds
  → With async: while waiting for OpenAI, the server handles other requests

HOW TO RUN:
  uvicorn 05_background_tasks:app --reload
"""

from fastapi import FastAPI, BackgroundTasks, Depends
from pydantic import BaseModel
import asyncio
import time
import logging
from typing import Optional
import httpx  # async HTTP client — use this instead of 'requests' in async code

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Level 3: Background Tasks and Async")


# ─────────────────────────────────────────────
# 1. BACKGROUND TASKS — fire and forget
# ─────────────────────────────────────────────
# BackgroundTasks runs functions AFTER the HTTP response is sent.
# The user gets an instant response; the heavy work happens in the background.

def send_welcome_email(email: str, username: str):
    """
    Simulates sending a welcome email.
    This function runs in the background after the response is sent.
    NOTE: BackgroundTasks runs in the same thread, so use async if doing I/O.
    """
    logger.info(f"Sending welcome email to {email} for user {username}...")
    time.sleep(2)  # Simulate email sending delay (2 seconds)
    logger.info(f"Email sent to {email}")


class RegisterRequest(BaseModel):
    username: str
    email: str


@app.post("/register", status_code=201, tags=["Background Tasks"])
def register_user(
    user: RegisterRequest,
    # FastAPI injects BackgroundTasks automatically — no Depends() needed
    background_tasks: BackgroundTasks,
):
    # 1. Save user to DB (fast — happens before response)
    logger.info(f"User {user.username} saved to DB")

    # 2. Schedule email sending as a background task (slow — happens after response)
    background_tasks.add_task(
        send_welcome_email,      # the function to call
        user.email,              # argument 1
        user.username,           # argument 2
    )

    # 3. Return the response IMMEDIATELY — email is still being sent in the background
    return {"message": "Registration successful! Welcome email will arrive shortly."}


# ─────────────────────────────────────────────
# 2. AI-SPECIFIC BACKGROUND TASKS
# ─────────────────────────────────────────────
# The most important use case: document ingestion pipeline

async def index_document_async(file_path: str, user_id: int):
    """
    Simulates indexing a document into a vector database.
    This is async because it does multiple I/O operations:
      1. Read the file
      2. Call an embedding model API
      3. Write vectors to the vector DB
    """
    logger.info(f"[user {user_id}] Starting document indexing: {file_path}")

    # Step 1: Read and chunk the document (simulated)
    await asyncio.sleep(1)
    logger.info(f"[user {user_id}] Document chunked into pieces")

    # Step 2: Generate embeddings (simulated — in real app, call HuggingFace/OpenAI)
    await asyncio.sleep(2)
    logger.info(f"[user {user_id}] Embeddings generated")

    # Step 3: Write to vector DB (simulated)
    await asyncio.sleep(1)
    logger.info(f"[user {user_id}] Vectors written to database. Indexing complete!")


@app.post("/documents/ingest", tags=["Background Tasks"])
async def ingest_document(
    file_path: str,
    user_id: int,
    background_tasks: BackgroundTasks,
):
    # Return "accepted" immediately — don't make user wait for a 4-second pipeline
    background_tasks.add_task(index_document_async, file_path, user_id)
    return {
        "status": "accepted",
        "message": "Document is being indexed. Query it in about 10 seconds.",
    }


# ─────────────────────────────────────────────
# 3. SYNC vs ASYNC — understanding the difference
# ─────────────────────────────────────────────

@app.get("/sync-example", tags=["Async vs Sync"])
def sync_route():
    """
    SYNC route (def, not async def).
    FastAPI runs this in a thread pool — it does NOT block the event loop.
    Use this for CPU-bound work or when using sync libraries (like SQLAlchemy sync mode).
    """
    time.sleep(1)  # OK in sync routes — runs in thread pool
    return {"type": "sync", "message": "I ran in a thread pool"}


@app.get("/async-example", tags=["Async vs Sync"])
async def async_route():
    """
    ASYNC route (async def).
    Runs directly on the event loop. Use 'await' for I/O operations.
    NEVER call blocking functions (time.sleep, requests.get) in an async route.
    """
    await asyncio.sleep(1)  # NON-blocking — other requests are handled during this wait
    return {"type": "async", "message": "I ran on the event loop"}


@app.get("/wrong-async", tags=["Async vs Sync"])
async def wrong_async():
    """
    ❌ WRONG: Using blocking code in an async route.
    time.sleep() in an async function BLOCKS the entire server for 1 second.
    No other requests can be handled during that time.
    """
    time.sleep(1)  # THIS BLOCKS EVERYTHING — never do this!
    return {"message": "This blocked the server for 1 second"}


# ─────────────────────────────────────────────
# 4. CALLING EXTERNAL APIs ASYNC (httpx)
# ─────────────────────────────────────────────
# 'requests' is synchronous — never use it in async routes.
# 'httpx' has an async client — always use this in AI apps.

@app.get("/external-data", tags=["Async HTTP"])
async def fetch_external_data():
    """
    Demonstrates async HTTP calls using httpx.
    In real AI apps: replace with calls to OpenAI, HuggingFace, etc.
    """
    # Use httpx.AsyncClient as a context manager — it handles connection pooling
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # This await yields control to the event loop while waiting for the response.
            # Other requests CAN be handled during this network wait.
            response = await client.get("https://httpbin.org/json")
            response.raise_for_status()  # raises httpx.HTTPStatusError for 4xx/5xx
            return {"external_data": response.json()}
        except httpx.TimeoutException:
            # Always handle timeouts — external APIs can be slow or unavailable
            return {"error": "External API timed out"}
        except httpx.HTTPStatusError as e:
            return {"error": f"External API returned {e.response.status_code}"}


# ─────────────────────────────────────────────
# 5. PARALLEL ASYNC CALLS (gathering)
# ─────────────────────────────────────────────
# asyncio.gather() runs multiple async operations AT THE SAME TIME.
# Use this when calling multiple independent APIs (e.g., retrieve from 3 data sources).

async def fetch_documents(query: str) -> list:
    await asyncio.sleep(0.5)  # simulate DB query
    return [f"doc about {query} #1", f"doc about {query} #2"]

async def fetch_user_history(user_id: int) -> list:
    await asyncio.sleep(0.3)  # simulate another DB query
    return [f"history entry {i}" for i in range(3)]

async def fetch_system_prompt() -> str:
    await asyncio.sleep(0.1)  # simulate config fetch
    return "You are a helpful assistant."


@app.get("/rag/context", tags=["Parallel Async"])
async def get_rag_context(query: str, user_id: int):
    """
    Fetches all context needed for a RAG call in parallel.
    Sequential: 0.5 + 0.3 + 0.1 = 0.9 seconds
    Parallel:   max(0.5, 0.3, 0.1) = 0.5 seconds (almost 2x faster)
    """
    # Run all three fetches at the same time
    docs, history, system_prompt = await asyncio.gather(
        fetch_documents(query),
        fetch_user_history(user_id),
        fetch_system_prompt(),
    )

    return {
        "retrieved_docs": docs,
        "user_history": history,
        "system_prompt": system_prompt,
    }
