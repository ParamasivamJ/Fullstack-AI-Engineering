# Level 5 — Professional Engineering Guide

## The Professional Mindset

Levels 1–4 taught you to build features that work.
Level 5 teaches you to build systems that are:
- **Secure** — can't be abused or broken into
- **Observable** — you know what's happening in production
- **Reliable** — tested, so regressions are caught immediately
- **Multi-tenant** — built for multiple users from the start

These are not optional upgrades. They are the baseline for professional work.

---

## Auth: The Full JWT Flow

```
User submits username + password
            │
            ▼
    POST /auth/login
            │
    ┌───────────────────────────────────────┐
    │  1. Look up user by username          │
    │  2. bcrypt.verify(password, hash)     │
    │     ❌ wrong → 401 Unauthorized       │
    │     ✅ correct → continue             │
    │  3. Create Access Token (30 min)      │
    │     jwt.encode({"sub": username,      │
    │                 "exp": now + 30min})  │
    │  4. Create Refresh Token (7 days)     │
    │     jwt.encode({"sub": username,      │
    │                 "exp": now + 7days})  │
    │  5. Return both tokens                │
    └───────────────────────────────────────┘
            │
            ▼
    Client stores tokens
    (Access in memory, Refresh in httpOnly cookie)
            │
            │  Later: Protected API call
            ▼
    GET /tasks
    Authorization: Bearer <access_token>
            │
    ┌───────────────────────────────────────┐
    │  Depends(get_current_user)            │
    │  1. Extract Bearer token from header  │
    │  2. jwt.decode(token, SECRET_KEY)     │
    │     ❌ expired/invalid → 401          │
    │     ✅ valid → get username           │
    │  3. Fetch user from DB                │
    │  4. Return user object                │
    └───────────────────────────────────────┘
            │
            ▼
    Route function runs with current_user
```

---

## Logging: What to Log and What Not to Log

### ✅ ALWAYS LOG
- Request method + path
- Status code
- Latency (ms)
- User ID (for AI calls)
- Model name (for AI calls)
- Token counts (for cost tracking)
- Error type and message
- Request ID (for tracing)

### ❌ NEVER LOG
- Passwords (even hashed)
- JWT tokens
- API keys
- Full user messages (they may contain PII)
- Credit card numbers or financial data
- Health information

---

## Testing: The Testing Pyramid

```
                    ╔═══════════════╗
                    ║  E2E Tests    ║  ← few, slow, cover full user flows
                    ╚═══════════════╝
              ╔═════════════════════════╗
              ║  Integration Tests      ║  ← some, test routes + DB together
              ╚═════════════════════════╝
        ╔═══════════════════════════════════╗
        ║  Unit Tests                        ║  ← many, fast, test one function
        ╚═══════════════════════════════════╝
```

For FastAPI, the recommended approach:
- **TestClient** for route-level tests (like integration tests, but fast)
- **pytest fixtures** for shared setup
- **parametrize** for boundary value testing
- **mock** (`unittest.mock.patch`) for external APIs (LLMs, S3)

### Most Important Tests to Write First

1. Happy path (valid input → correct response)
2. Auth gates (unauth request → 401, wrong role → 403)
3. Validation failures (bad input → 422 with correct field errors)
4. Not found (missing resource → 404)
5. Ownership check (User A cannot access User B's data)

---

## Rate Limiting Strategy

| Endpoint Type | Limit | Window |
|--------------|-------|--------|
| Health check | None | — |
| Registration | 5 requests | per hour per IP |
| Login | 10 attempts | per hour per IP |
| Standard API | 60 requests | per minute per user |
| AI chat | 10 requests | per minute per user |
| Document upload | 5 uploads | per hour per user |
| Embedding search | 30 requests | per minute per user |

---

## Multi-User Isolation Checklist

For every database query, ask: "Am I filtering by owner_id?"

```python
# Pattern for every query:
SELECT * FROM tasks WHERE id = $1 AND owner_id = $2  ← both conditions!

# Pattern for every list:
SELECT * FROM tasks WHERE owner_id = $1 ORDER BY created_at DESC

# Pattern for vector search:
WHERE documents.owner_id = $1  ← join up to the owner
```

For vector DBs (Qdrant), filter by owner metadata on every search.

---

## Environment Variable Security

```
Development:  .env file (never committed to git)
CI/CD:        GitHub Secrets / GitLab CI Variables
Staging:      Container environment variables
Production:   AWS Secrets Manager / GCP Secret Manager / HashiCorp Vault
```

**The rules:**
1. `.env` is always in `.gitignore`
2. Secrets are never hardcoded in source code
3. Secrets are never logged
4. Each environment has its own set of secrets

---

## Files in This Level

| File | How to test |
|------|------------|
| `01_jwt_auth_full.py` | Register, login, use token, test with wrong token |
| `02_logging_structured.py` | Check terminal output — all logs are JSON |
| `03_testing_with_pytest.py` | `pytest 03_testing_with_pytest.py -v` |
| `04_rate_limiting.py` | Hit `/test` 11+ times and see 429 response |
| `05_env_management.py` | Create a `.env` file, run app, check `/config/public` |
| `06_multi_user_design.py` | `/demo/setup` then compare alice vs bob task lists |

Next: `Level_6_Expert_Architecture/` — production structure, WebSockets, retries, agents.
