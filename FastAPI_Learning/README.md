# FastAPI Learning Resource — From Zero to Expert

This directory is a complete, self-paced FastAPI training resource.
Every concept is explained as a teacher would explain it, and every code file
runs as a real template you can use in production AI applications.

## How to Use This Resource

1. Read the `.md` files to understand concepts first.
2. Open the `.py` files, read every comment, then run them.
3. Modify the code to experiment — that is how real learning happens.
4. The levels build on each other: do not skip ahead.

---

## Learning Path

```
Level 1 → Level 2 → Level 3 → Level 4 → Level 5 → Level 6
  HTTP    FastAPI   Backend    AI Apps   Pro Eng   Expert Arch
 Basics   Basics    Skills    Patterns   Skills    & Production
```

| Level | Folder | What You Will Learn |
|-------|--------|---------------------|
| 1 | `Level_1_HTTP_Basics/` | HTTP, methods, status codes, headers, JSON |
| 2 | `Level_2_FastAPI_Fundamentals/` | Routes, Pydantic, validation, response models |
| 3 | `Level_3_Real_Backend_Skills/` | Errors, DI, CORS, files, async, background tasks |
| 4 | `Level_4_AI_App_Patterns/` | Chat, streaming, RAG, document ingestion, cost control |
| 5 | `Level_5_Professional_Engineering/` | Auth, logging, testing, rate limiting, multi-user |
| 6 | `Level_6_Expert_Architecture/` | Production DB, retries, WebSockets, versioning, agents |

---

## Tech Stack Used

- **FastAPI** — the web framework
- **Pydantic v2** — data validation
- **SQLAlchemy 2** — database ORM
- **PostgreSQL** — relational database
- **pgvector** — vector similarity search inside PostgreSQL
- **python-jose** — JWT authentication
- **httpx** — async HTTP client (for calling LLMs, external APIs)
- **pytest** — testing framework
- **slowapi** — rate limiting

---

## Quick Reference

See `Quick_Reference/cheatsheet.md` for a one-page summary of all patterns.
See `Quick_Reference/patterns.md` for AI production patterns at a glance.

---

## Mindset

> A good API is not just code that works.
> It is code that is secure, observable, testable, and maintainable by someone else.
> Every file here teaches you to think that way from the beginning.
