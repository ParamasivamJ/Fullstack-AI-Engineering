# Level 2 — FastAPI Fundamentals Guide

## What This Level Covers

Before writing any code, understand the three pillars of every FastAPI route:

```
Request comes in
       │
       ▼
┌─────────────────────────────────────┐
│  WHERE is the data?                 │
│  ├── In the URL path → Path Param   │
│  ├── After the ? → Query Param      │
│  └── In the body → Pydantic Model   │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  IS the data valid?                 │
│  Pydantic runs all validators       │
│  ├── Type correct?                  │
│  ├── Length in range?               │
│  ├── Custom validators pass?        │
│  └── Cross-field logic passes?      │
└─────────────────────────────────────┘
       │
       ▼
Your function runs
       │
       ▼
┌─────────────────────────────────────┐
│  WHAT goes back to the client?      │
│  response_model filters the output  │
│  ├── Strips internal fields         │
│  ├── Removes None values (optional) │
│  └── Sets correct status code       │
└─────────────────────────────────────┘
```

---

## Path vs Query vs Body — Decision Guide

| Question | Answer |
|----------|--------|
| Am I identifying a specific resource? | Path param → `/users/{id}` |
| Am I filtering or sorting a list? | Query param → `/tasks?status=done` |
| Am I creating or updating data? | Request body → JSON in POST/PUT/PATCH |
| Can I use a body with GET? | Technically yes, but never do this |

---

## Pydantic Mental Model

```
Raw JSON from client
        │
        ▼
   Type coercion
   "42" → 42 (int)     # Pydantic converts strings to numbers automatically
        │
        ▼
   Field constraints
   min_length, max_length, ge, le, regex...
        │
        ▼
   @field_validator
   Your custom logic runs here
        │
        ▼
   @model_validator
   Cross-field checks run here
        │
        ▼
   Python object is created
   task.title, task.priority, etc.
```

### The Three Levels of Validation

1. **Type validation** — happens automatically. `title: str` means only strings accepted.
2. **Constraint validation** — `Field(min_length=1, max_length=200)`. FastAPI handles.
3. **Business logic validation** — `@field_validator`. You write this.

---

## Response Model Data Flow

```
Database returns TaskInDB:
{
  "id": 1,
  "title": "Write tests",
  "completed": false,
  "owner_id": 42,          ← should NOT leave the server
  "internal_score": 0.97,  ← definitely should NOT leave the server
  "hashed_password": "..."  ← NEVER should leave the server
}

FastAPI filters through TaskOut:
{
  "id": 1,
  "title": "Write tests",
  "completed": false
  // owner_id, internal_score, hashed_password — ALL stripped automatically
}
```

---

## Common Mistakes

### ❌ Mistake 1: Using the same model for input and output

```python
# WRONG — the password could be returned
class User(BaseModel):
    id: int
    username: str
    password: str

@app.post("/users", response_model=User)  # This would return the password!
def create_user(user: User): ...
```

```python
# CORRECT — separate schemas
class UserIn(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str

@app.post("/users", response_model=UserOut)
def create_user(user: UserIn): ...
```

---

### ❌ Mistake 2: Returning bare lists

```python
# WRONG — you can never add pagination metadata later without breaking clients
@app.get("/tasks")
def list_tasks() -> list[Task]:
    return [...]
```

```python
# CORRECT — always wrap in a pagination envelope
class TaskList(BaseModel):
    total: int
    page: int
    items: list[TaskOut]

@app.get("/tasks", response_model=TaskList)
def list_tasks(page: int = 1) -> TaskList: ...
```

---

### ❌ Mistake 3: Putting business logic in validators

```python
# WRONG — validator saves to DB. Validators should ONLY validate.
@field_validator("username")
def check_username(cls, v):
    db.save(v)  # NEVER DO THIS
    return v
```

---

## Why This Matters for AI Apps

In an AI application, Pydantic is your first line of defense:

```python
class ChatRequest(BaseModel):
    message: str = Field(..., max_length=4000)  # prevents prompt injection via giant inputs
    model: Literal["gpt-4o", "gpt-4o-mini"] = "gpt-4o-mini"  # controls cost
    max_tokens: int = Field(default=500, le=4000)  # limits output length = limits cost
```

Without validation, a malicious user could:
- Send a 100,000 token prompt (expensive)
- Request a more expensive model than they are authorized for
- Crash your app with unexpected data types

---

## Files in This Level

| File | What to learn |
|------|--------------|
| `01_routes_and_params.py` | Path, query, body — run it and use `/docs` to test each endpoint |
| `02_pydantic_validation.py` | Validators, enums, nested models, input/output separation |
| `03_response_models.py` | response_model, status codes, custom responses |

Next: `Level_3_Real_Backend_Skills/` — where you learn to handle real-world complexity.
