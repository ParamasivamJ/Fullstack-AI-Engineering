# FastAPI Expert Cheatsheet

## Route Decorators
```python
@app.get("/path")
@app.post("/path")
@app.put("/path/{id}")
@app.patch("/path/{id}")
@app.delete("/path/{id}")
```

## Parameter Types
```python
# Path param
def fn(id: int = Path(..., gt=0)): ...

# Query param
def fn(limit: int = Query(10, ge=1, le=100)): ...

# Body (Pydantic model)
def fn(data: MyModel): ...

# Header
def fn(x_api_key: str = Header(...)): ...
```

## Status Codes to Remember
| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Default success |
| 201 | Created | After POST |
| 204 | No Content | After DELETE |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | No/bad token |
| 403 | Forbidden | No permission |
| 404 | Not Found | Resource missing |
| 409 | Conflict | Duplicate |
| 422 | Unprocessable | Pydantic fail |
| 429 | Too Many Requests | Rate limited |
| 500 | Server Error | Unhandled crash |
| 504 | Gateway Timeout | LLM timed out |

## Dependency Pattern
```python
async def get_db(): yield db          # DB session
async def get_user(token=...): ...    # Auth
def require_admin(user=Depends(get_user)): ...  # RBAC

# In route:
def endpoint(db: DB, user: AuthUser, admin: AdminOnly): ...

# Annotated shorthand:
DB = Annotated[Session, Depends(get_db)]
```

## Response Model Pattern
```python
@app.post("/users", response_model=UserOut)
def create(user: UserIn): ...

# Always: UserIn != UserOut
# UserIn has password, UserOut does not
```

## Error Raising
```python
raise HTTPException(status_code=404, detail="Not found")

# Custom exception handler:
@app.exception_handler(MyError)
async def handler(req, exc): return JSONResponse(...)
```

## Streaming Response
```python
async def generate():
    for token in llm_stream():
        yield f"data: {json.dumps({'token': token})}\n\n"
    yield "event: done\ndata: {}\n\n"

return StreamingResponse(generate(), media_type="text/event-stream")
```

## Background Tasks
```python
def endpoint(bg: BackgroundTasks):
    bg.add_task(my_function, arg1, arg2)
    return {"status": "accepted"}  # returns BEFORE my_function runs
```

## Async Rules
- `async def` + `await` for I/O (DB, HTTP, LLM)
- `def` (sync) in thread pool — ok for CPU or sync libraries
- Never use `time.sleep()` in `async def` → use `await asyncio.sleep()`
- Never use `requests` in `async def` → use `httpx.AsyncClient`
- Use `asyncio.gather()` to run multiple awaits in parallel

## pgvector Query Pattern
```sql
-- Find top 5 similar chunks (cosine)
SELECT *, 1 - (embedding <=> '[0.1, 0.2, ...]') AS score
FROM document_chunks
ORDER BY embedding <=> '[0.1, 0.2, ...]'
LIMIT 5;
```

## JWT Pattern
```python
# Create: jwt.encode({"sub": username, "exp": ...}, SECRET_KEY, "HS256")
# Decode: jwt.decode(token, SECRET_KEY, ["HS256"])
# Protect: use OAuth2PasswordBearer + Depends()
```

## Folder Structure (Production)
```
project/
├── main.py          # App factory, startup events, routers included
├── database.py      # Engine, session, get_db()
├── models.py        # SQLAlchemy models
├── schemas.py       # Pydantic schemas (Input/Output separated)
├── crud.py          # All DB queries — no queries in routes!
├── auth.py          # JWT and password logic
├── config.py        # Settings from .env via pydantic-settings
└── routers/
    ├── users.py
    ├── tasks.py
    └── rag.py
```
