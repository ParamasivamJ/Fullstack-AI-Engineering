# Level 1 — The Request Lifecycle

Understanding the full journey of a request is what separates developers
who debug by guessing from developers who debug by knowing.

---

## The Complete Journey (FastAPI + PostgreSQL)

```
Browser / Frontend
        │
        │  HTTP Request (POST /tasks, with JWT in header)
        ▼
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Application                  │
│                                                         │
│  1. MIDDLEWARE LAYER (runs first, on every request)     │
│     ├── CORS middleware (is this origin allowed?)       │
│     ├── Logging middleware (log the incoming request)   │
│     └── Rate limit middleware (is this user throttled?) │
│                                                         │
│  2. ROUTER (which function handles this path?)          │
│     └── Matches POST /tasks → create_task()             │
│                                                         │
│  3. DEPENDENCIES (run before the function)              │
│     ├── get_db()       → opens a DB session             │
│     └── get_current_user() → validates the JWT token    │
│                                                         │
│  4. VALIDATION (Pydantic runs automatically)            │
│     └── Is the request body a valid TaskCreate schema?  │
│         ├── YES → continue to the function              │
│         └── NO  → return 422 Unprocessable Entity       │
│                                                         │
│  5. ROUTE FUNCTION (your actual business logic)         │
│     └── create_task(task, current_user, db)             │
│         ├── calls crud.create_task(db, task, user.id)   │
│         └── PostgreSQL inserts and returns the row      │
│                                                         │
│  6. RESPONSE SERIALIZATION                              │
│     └── Pydantic converts the DB object → JSON          │
│                                                         │
└─────────────────────────────────────────────────────────┘
        │
        │  HTTP Response (201 Created, JSON body)
        ▼
Browser / Frontend
```

---

## Step-by-Step Breakdown

### Step 1: Middleware

Middleware is code that wraps every single request before and after your route function.
It runs **before** your function sees the request, and can also run **after** it sends the response.

Think of middleware as the security guard and receptionist at the building entrance.
Every visitor goes through them, no matter which office they are visiting.

**Examples of what middleware does:**
- Add CORS headers so the browser allows the response
- Log the request method, path, and timestamp
- Check if the user has exceeded their rate limit
- Add a unique request ID to the request for tracing

### Step 2: Routing

FastAPI looks at the incoming URL path and HTTP method, then finds which Python function
you registered to handle it.

```python
@app.post("/tasks")  # ← This is the "router registration"
def create_task(...):
    ...
```

If no route matches, FastAPI automatically returns `404 Not Found`.

### Step 3: Dependencies

Before calling your function, FastAPI runs all functions marked with `Depends()`.
These resolve in order, and their results are injected as arguments.

This is one of FastAPI's most powerful features — it enforces reuse and keeps
your route functions clean.

```
Depends(get_db)           → opens a DB session, yields it, closes it after
Depends(get_current_user) → decodes the JWT, fetches the user from DB, returns them
```

If any dependency raises an `HTTPException`, the route function never runs.
The error is returned immediately.

### Step 4: Pydantic Validation

The request body is automatically passed through your Pydantic schema.
This is not optional — FastAPI enforces it before your function runs.

If validation fails (e.g., you sent a number where a string was expected),
FastAPI returns a detailed `422 Unprocessable Entity` response with field-level errors.

### Step 5: Your Function

Only now does your actual business logic run.
At this point, you know:
- The request body is valid
- The user is authenticated
- The database session is open
- The rate limit has not been exceeded

### Step 6: Response Serialization

Your function returns a Python object (e.g., a SQLAlchemy model).
FastAPI uses your `response_model` Pydantic schema to:
1. Filter out fields that should not be in the response (e.g., `hashed_password`)
2. Convert Python types to JSON-serializable types
3. Set the appropriate `Content-Type: application/json` header

---

## The Error Path

What if something goes wrong at any step?

```
                raise HTTPException(status_code=404, detail="Task not found")
                        │
                        ▼
              FastAPI exception handler catches it
                        │
                        ▼
              Returns JSON: {"detail": "Task not found"}
              With status code: 404
```

FastAPI has built-in exception handlers. You can also write custom ones to
format errors exactly the way your frontend expects.

---

## Why This Matters for AI Apps

In an AI application, the request lifecycle adds more steps:

```
Request → Middleware → Router → Dependencies → Validation
    → Your Function:
        ├── Retrieve documents from vector DB (Qdrant / pgvector)
        ├── Build a prompt with retrieved context
        ├── Call the LLM API (OpenAI / HuggingFace)
        │   └── This is slow — use async!
        └── Stream the response back to the frontend
```

Understanding this full lifecycle is why you can:
- Add cost controls BEFORE calling the LLM (in a dependency)
- Add rate limiting BEFORE the function runs (in middleware)
- Log every AI call AFTER the response (in middleware)

---

## Key Takeaways

1. Every request passes through **Middleware → Router → Dependencies → Validation → Function → Serialization**.
2. Failure at any step short-circuits the rest and returns an appropriate error.
3. Dependencies are where you put reusable logic (auth, DB, rate limits).
4. Pydantic validation is automatic and happens before your code runs.
5. In AI apps, your function itself has multiple sub-steps — design each one to fail gracefully.

Next: `Level_2_FastAPI_Fundamentals/` — Now start building with code.
