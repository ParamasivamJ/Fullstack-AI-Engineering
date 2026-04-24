# Level 3 — Real Backend Skills: Guide and Flow Diagrams

## What This Level Covers

After Level 2, you know how to accept and return data.
Level 3 teaches you what happens when things go wrong,
how to share logic across routes, and how to handle the
real-world complexity every production app faces.

---

## Error Handling: The Decision Tree

```
Something goes wrong in your route
            │
            ▼
 Is it a client mistake?  (bad input, not found, wrong auth)
  ├── YES → raise HTTPException(4xx)
  │         Always include a clear "detail" message
  └── NO  → Is it an expected server error? (LLM timeout, DB down)
              ├── YES → raise your custom domain exception
              │         The global handler converts it to 5xx
              └── NO  → Let it bubble up to the catch-all handler
                         Log the full stack trace
                         Return generic 500 to the client
```

### Error Response Shape — ALWAYS consistent

```json
{
  "detail": "Task with ID 42 does not exist",
  "code": "TASK_NOT_FOUND",
  "context": { "task_id": 42 }
}
```

The `code` field is the key: the frontend switches on it to show
specific error messages or UI behavior per error type.

---

## Dependency Injection: The Chain

```
Route Function
    │
    ├── Depends(get_db)
    │       └── Opens DB session
    │           Yields it
    │           Closes it after request
    │
    ├── Depends(get_current_user)
    │       └── Depends(oauth2_scheme)  ← extracts Bearer token from header
    │               └── Decodes JWT
    │                   Fetches user from DB
    │                   Returns user object (or raises 401)
    │
    └── Depends(require_admin)
            └── Depends(get_current_user)  ← chains to auth
                    └── Checks user.role == "admin"
                        Returns user (or raises 403)
```

**Expert rule:** If any dependency raises an exception,
the chain stops immediately. The route function never runs.
This makes dependencies the correct place for auth and permission checks.

---

## CORS: Why It Exists and How to Configure It

```
Browser Tab (localhost:3000)
       │
       │  Wants to call: localhost:8000
       │
       ▼
Browser checks: is this cross-origin?
  localhost:3000 ≠ localhost:8000  → YES, different port = different origin
       │
       │  Browser sends a "preflight" OPTIONS request first
       ▼
FastAPI CORSMiddleware responds:
  Access-Control-Allow-Origin: http://localhost:3000
  Access-Control-Allow-Methods: GET, POST, PUT, DELETE
  Access-Control-Allow-Headers: Authorization, Content-Type
       │
       │  If browser is satisfied → actual request is allowed
       │  If not listed → browser BLOCKS the request
       ▼
Your API call succeeds
```

**Production CORS config:**
```python
allow_origins=[
    "https://yourapp.com",
    "https://www.yourapp.com",
]
# Never use allow_origins=["*"] with allow_credentials=True
```

---

## Middleware Execution Order

Middleware is applied in reverse order of registration.
The last `add_middleware()` call wraps the outermost layer.

```
Request →  SecurityHeaders → RequestLogging → CORS → Router → Route Function
Response ← SecurityHeaders ← RequestLogging ← CORS ← Router ← Route Function
```

If you add:
```python
app.add_middleware(CORSMiddleware)       # added 1st → inner
app.add_middleware(RequestLogging)       # added 2nd → middle  
app.add_middleware(SecurityHeaders)      # added 3rd → outermost
```

---

## Async Mental Model

```
EVENT LOOP (single thread)
    │
    ├── handles request A
    │   └── await db.query()  → pauses A, starts waiting
    │
    ├── handles request B  ← EVENT LOOP is FREE to do this!
    │   └── await llm.call() → pauses B, starts waiting
    │
    ├── DB query returns for A
    │   └── resumes A
    │
    └── LLM call returns for B
        └── resumes B
```

**Key rule:** `await` yields control to the event loop.
The event loop can handle other requests during that wait.
This is why async is so powerful for I/O-bound workloads.

---

## File Upload Security Checklist

| Check | Why |
|-------|-----|
| Validate MIME type (not extension) | `.jpg` can be renamed `malware.exe` |
| Validate magic bytes (first bytes of file) | MIME type header can be faked too |
| Limit file size before reading | Giant files exhaust RAM |
| Use UUID filename (not original) | `../../../etc/passwd` is a filename |
| Store outside web root | Files should not be directly accessible by URL |
| Scan for malware | In enterprise apps |

---

## Background Tasks vs Celery

| Feature | BackgroundTasks | Celery + Redis |
|---------|----------------|----------------|
| Setup | Zero — built-in | Requires Redis/RabbitMQ |
| Persistence | No — if server restarts, tasks are lost | Yes — tasks survive restarts |
| Retry logic | No | Yes |
| Task queue | No | Yes |
| Monitoring | No | Yes (Flower UI) |
| **Use for** | Simple fire-and-forget | Long jobs, retries, scheduling |

**Decision:** Use `BackgroundTasks` for small jobs like sending emails.
Use Celery for document ingestion, batch embeddings, and report generation.

---

## Common Mistakes at This Level

### ❌ Inconsistent error responses
Some routes return `{"error": "..."}`, others return `{"detail": "..."}`.
The frontend has to handle two formats. Use a global handler instead.

### ❌ DB session not closed on error
Without `try/finally` in `get_db()`, an exception leaks the connection.
SQLAlchemy connection pool fills up and new requests hang.

### ❌ Blocking code in async routes
```python
async def my_route():
    time.sleep(5)       # ❌ blocks entire server for 5 seconds
    requests.get(url)   # ❌ blocks entire server during network call
```
Use `await asyncio.sleep()` and `httpx.AsyncClient` instead.

### ❌ Saving original filename
```python
open(file.filename, "wb")  # ❌ path traversal vulnerability
open(f"uploads/{uuid4()}", "wb")  # ✅ safe
```

---

## Files in This Level

| File | Run command |
|------|------------|
| `01_error_handling.py` | `uvicorn 01_error_handling:app --reload` → test `/tasks/0`, `/tasks/200`, `/crash` |
| `02_dependency_injection.py` | `uvicorn 02_dependency_injection:app --reload` → add `X-API-Key: admin-key-123` header |
| `03_cors_and_middleware.py` | `uvicorn 03_cors_and_middleware:app --reload` → check response headers |
| `04_file_uploads.py` | `uvicorn 04_file_uploads:app --reload` → upload a PDF via `/docs` |
| `05_background_tasks.py` | `uvicorn 05_background_tasks:app --reload` → watch logs after `/register` |

Next: `Level_4_AI_App_Patterns/` — where we build the actual AI features.
