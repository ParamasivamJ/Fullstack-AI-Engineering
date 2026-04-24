# Level 6 — Expert Architecture Guide

## What This Level Covers

This level ties everything together into a system that you can
actually put in front of real users and real traffic.

Expert architecture means:
- The code is organized so any developer can find anything in under 30 seconds
- Every failure mode is handled gracefully
- Data is real-time (WebSockets) when needed
- APIs evolve without breaking clients (versioning)
- AI agents can call your endpoints as tools

---

## The Full Production Stack

```
┌───────────────────────────────────────────────────────────────────┐
│  CLIENT (Next.js / React)                                         │
│  ├── HTTP REST calls for CRUD                                     │
│  ├── SSE for streaming LLM output                                 │
│  └── WebSocket for real-time collaboration                        │
└───────────────────────────────┬───────────────────────────────────┘
                                │ HTTPS
┌───────────────────────────────▼───────────────────────────────────┐
│  REVERSE PROXY (nginx / AWS ALB)                                  │
│  ├── TLS termination                                              │
│  ├── Rate limiting (IP-level)                                     │
│  └── Load balancing across FastAPI instances                      │
└───────────────────────────────┬───────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────┐
│  FASTAPI APPLICATION                                              │
│  ├── Middleware (logging, security headers, CORS, rate limiting)  │
│  ├── Routers (auth, users, tasks, rag, agents)                    │
│  ├── Dependencies (get_db, get_current_user, require_role)        │
│  ├── Services (rag_pipeline, llm_client, embedding_service)       │
│  └── CRUD (all database queries)                                  │
└────────────┬──────────────────┬────────────────────┬─────────────┘
             │                  │                    │
    ┌────────▼──────┐  ┌───────▼──────┐   ┌────────▼────────┐
    │  PostgreSQL   │  │   pgvector   │   │  External APIs  │
    │  (relational  │  │  (semantic   │   │  OpenAI, HF,    │
    │  user/task    │  │  document    │   │  Qdrant, S3     │
    │  data)        │  │  search)     │   │                 │
    └───────────────┘  └──────────────┘   └─────────────────┘
```

---

## Resilience: The Four Patterns

```
                     LLM API Call
                          │
                ┌─────────▼──────────┐
                │  1. TIMEOUT (10s)  │ ← fail fast, don't hang
                └─────────┬──────────┘
                          │ fails
                ┌─────────▼──────────┐
                │  2. RETRY (3x)     │ ← handle transient errors
                │  with backoff:     │
                │  1s → 2s → 4s      │
                └─────────┬──────────┘
                          │ still failing
                ┌─────────▼──────────┐
                │  3. FALLBACK       │ ← degrade gracefully
                │  try cheaper model │
                └─────────┬──────────┘
                          │ all models fail
                ┌─────────▼──────────┐
                │  4. CIRCUIT BREAKER│ ← stop trying for 60s
                │  return cached or  │
                │  sorry message     │
                └────────────────────┘
```

---

## WebSocket vs SSE vs HTTP: Decision Guide

| Situation | Protocol |
|-----------|---------|
| AI token streaming (one direction) | SSE — simpler, works through proxies |
| User sends follow-up mid-stream | WebSocket — bidirectional |
| Real-time collaboration (multi-user) | WebSocket — broadcast support |
| Background job status updates | SSE or polling |
| Batch AI processing | HTTP with 202 Accepted + status polling |

---

## Agent Tool Design Principles

1. **Every tool has one clear purpose.** Never build a "do everything" tool.
2. **Tools must be stateless.** The agent manages state, not the tool.
3. **Tools validate all input strictly.** Agents can hallucinate parameters.
4. **Tools return structured output.** Agents parse JSON, not English sentences.
5. **Tools have fast timeouts.** If a tool hangs, the whole agent loop hangs.
6. **Tools are scoped by user.** Always pass `user_id` for tenant isolation.

---

## API Versioning Decision

```
Is the change backward-compatible?
(Adding optional field, new endpoint, bug fix)
    │
    ├── YES → No version needed
    │         Just deploy the change
    │
    └── NO → Create v2
             ├── Keep v1 running for 6–12 months
             ├── Add Deprecation header to v1 responses
             ├── Set Sunset date for v1
             └── Communicate to all clients
```

---

## PostgreSQL + pgvector: When to Upgrade to Qdrant

| Situation | Use |
|-----------|-----|
| < 1 million vectors | pgvector — simpler, one DB |
| Need to join vectors with SQL data | pgvector — native SQL joins |
| > 10 million vectors | Qdrant — purpose-built, faster |
| Need advanced filtering | Qdrant — richer filter API |
| Distributed multi-region | Qdrant — native clustering |

For projects 1–8 in our roadmap: pgvector is perfect.

---

## Files in This Level

| File | What to learn |
|------|--------------|
| `01_project_structure.md` | Folder layout, naming, layered architecture |
| `02_database_full_template/` | Full PostgreSQL + pgvector setup ready to use |
| `03_retries_and_timeouts.py` | timeout, retry, fallback, circuit breaker |
| `05_websockets.py` | Real-time streaming chat + multi-user rooms |
| `06_api_versioning.py` | v1/v2 side by side, deprecation headers |
| `07_agent_orchestration.py` | Tool server with discovery endpoint |

---

## What to Build Next

You now have every piece of knowledge needed to build:

```
Project 1  ✅ CRUD App with Auth
Project 2     Smart Document Uploader → uses: file uploads, pgvector, background tasks
Project 3     RAG Chatbot → uses: rag_pipeline_template, streaming
Project 4     RAG + Evaluation → uses: logging, test patterns, metrics
Project 5     Agentic Assistant → uses: agent_orchestration, WebSockets, LangGraph
...
Project 10    Enterprise Capstone → everything combined
```

Every file in this learning resource was written to directly prepare you for
one or more of those 10 projects. The patterns here ARE the projects.
