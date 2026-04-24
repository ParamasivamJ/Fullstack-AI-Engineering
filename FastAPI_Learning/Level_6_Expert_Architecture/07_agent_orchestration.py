"""
Level 6 — FastAPI as a Tool Server for AI Agents
==================================================

In agentic AI systems (LangGraph, CrewAI, AutoGen), agents need to call tools.
A "tool server" is a FastAPI app that exposes capabilities as HTTP endpoints,
which the agent orchestrator calls as part of its reasoning loop.

This is one of the most important patterns for AI engineering because:
  - Your tools are just FastAPI endpoints (easy to test, deploy, monitor)
  - Agents call them via HTTP (language/framework agnostic)
  - You can swap LangGraph for CrewAI without rewriting tools
  - Each tool is independently scalable and observable

Typical agent tools:
  - web_search(query) → list of results
  - document_search(query, user_id) → relevant chunks
  - summarize(text) → summary
  - calculator(expression) → result
  - get_weather(city) → weather data
  - database_query(question) → structured answer

HOW TO RUN:
  uvicorn 07_agent_orchestration:app --reload

INTEGRATION WITH LANGGRAPH:
  from langchain.tools import tool
  import httpx

  @tool
  def document_search(query: str) -> str:
    resp = httpx.post("http://localhost:8000/tools/document_search",
                      json={"query": query, "user_id": "user_1"})
    return resp.json()["results"]
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import math

app = FastAPI(
    title="AI Agent Tool Server",
    description="FastAPI endpoints designed to be called by AI agents as tools",
)


# ─────────────────────────────────────────────
# TOOL INPUT/OUTPUT SCHEMAS
# ─────────────────────────────────────────────
# Every tool should have strict input/output schemas.
# Agents rely on these to understand what they can pass and what to expect back.

# -- Web Search Tool --
class WebSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    max_results: int = Field(default=3, ge=1, le=10)

class WebSearchResult(BaseModel):
    title: str
    url: str
    snippet: str

class WebSearchResponse(BaseModel):
    query: str
    results: list[WebSearchResult]
    result_count: int


# -- Document Search Tool --
class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    user_id: str = Field(..., description="Scopes search to this user's documents")
    top_k: int = Field(default=3, ge=1, le=10)

class DocumentSearchResponse(BaseModel):
    query: str
    chunks: list[dict]
    chunk_count: int


# -- Summarize Tool --
class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=50, max_length=20000)
    max_sentences: int = Field(default=3, ge=1, le=10)
    style: str = Field(default="concise", description="'concise', 'detailed', or 'bullet_points'")

class SummarizeResponse(BaseModel):
    original_length: int
    summary: str
    reduction_ratio: float


# -- Calculator Tool --
class CalculatorRequest(BaseModel):
    expression: str = Field(..., description="Math expression to evaluate, e.g. '2 * (3 + 4)'")

class CalculatorResponse(BaseModel):
    expression: str
    result: float
    formatted: str


# -- Data Query Tool --
class DataQueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question about data")
    dataset: str = Field(..., description="Name of the dataset to query")

class DataQueryResponse(BaseModel):
    question: str
    answer: str
    data: Optional[list[dict]] = None


# ─────────────────────────────────────────────
# TOOL ENDPOINTS
# ─────────────────────────────────────────────

@app.post(
    "/tools/web_search",
    response_model=WebSearchResponse,
    tags=["Agent Tools"],
    summary="Search the web and return relevant results",
)
async def web_search(req: WebSearchRequest):
    """
    Tool: Web Search
    Called by agents when they need current information.
    In production: integrate with Serper, Tavily, or Google Custom Search.
    """
    await asyncio.sleep(0.3)  # simulate search latency

    # Simulated results (replace with real search API)
    results = [
        WebSearchResult(
            title=f"Result {i+1} for '{req.query}'",
            url=f"https://example.com/result-{i+1}",
            snippet=f"This is a snippet about {req.query} from source {i+1}.",
        )
        for i in range(req.max_results)
    ]

    return WebSearchResponse(
        query=req.query,
        results=results,
        result_count=len(results),
    )


@app.post(
    "/tools/document_search",
    response_model=DocumentSearchResponse,
    tags=["Agent Tools"],
    summary="Search indexed documents using semantic similarity",
)
async def document_search(req: DocumentSearchRequest):
    """
    Tool: Document Search (RAG retrieval step)
    Called by agents when they need information from a user's knowledge base.
    In production: queries pgvector or Qdrant with a real embedding.
    """
    await asyncio.sleep(0.2)  # simulate vector DB query latency

    # Simulated retrieval results
    chunks = [
        {
            "chunk_id": f"chunk_{i}",
            "content": f"Relevant document chunk {i} about '{req.query}'",
            "document": f"document_{i}.pdf",
            "page": i + 1,
            "similarity_score": round(0.95 - (i * 0.05), 2),
        }
        for i in range(req.top_k)
    ]

    return DocumentSearchResponse(
        query=req.query,
        chunks=chunks,
        chunk_count=len(chunks),
    )


@app.post(
    "/tools/summarize",
    response_model=SummarizeResponse,
    tags=["Agent Tools"],
    summary="Summarize a long text into a shorter form",
)
async def summarize(req: SummarizeRequest):
    """
    Tool: Text Summarizer
    Called by agents when they need to condense long retrieved documents.
    In production: call an LLM with a summarization prompt.
    """
    await asyncio.sleep(0.5)  # simulate LLM latency

    # Simulated summary (replace with real LLM call)
    if req.style == "bullet_points":
        summary = f"• Key point 1 from the text\n• Key point 2 from the text\n• Key point 3 from the text"
    else:
        summary = f"This text discusses important topics. The main themes are summarized in {req.max_sentences} sentences."

    return SummarizeResponse(
        original_length=len(req.text),
        summary=summary,
        reduction_ratio=round(len(summary) / len(req.text), 2),
    )


@app.post(
    "/tools/calculator",
    response_model=CalculatorResponse,
    tags=["Agent Tools"],
    summary="Evaluate a mathematical expression safely",
)
def calculator(req: CalculatorRequest):
    """
    Tool: Safe Calculator
    Called by agents that need to perform numerical calculations.
    """
    # Safe evaluation — NEVER use eval() directly (code injection risk)
    # Allow only basic math operations
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
    allowed_names.update({"abs": abs, "round": round, "min": min, "max": max})

    try:
        # Restrict to safe expression evaluation
        result = float(eval(req.expression, {"__builtins__": {}}, allowed_names))  # noqa: S307
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid expression: {str(e)}")

    return CalculatorResponse(
        expression=req.expression,
        result=result,
        formatted=f"{req.expression} = {result:,.4f}",
    )


# ─────────────────────────────────────────────
# TOOLS DISCOVERY ENDPOINT
# ─────────────────────────────────────────────
# Agents can query this to discover available tools and their descriptions.
# This is the foundation for dynamic tool selection.

@app.get("/tools", tags=["Agent Tools"])
def list_tools():
    """
    Returns a machine-readable list of all available tools.
    Agents can use this to dynamically decide which tools to call.
    """
    return {
        "tools": [
            {
                "name": "web_search",
                "description": "Search the web for current information on any topic",
                "endpoint": "POST /tools/web_search",
                "input": {"query": "string", "max_results": "int (1-10)"},
                "output": {"results": "list of {title, url, snippet}"},
                "use_when": "Need current information, news, or facts not in the knowledge base",
            },
            {
                "name": "document_search",
                "description": "Search through indexed user documents using semantic similarity",
                "endpoint": "POST /tools/document_search",
                "input": {"query": "string", "user_id": "string", "top_k": "int (1-10)"},
                "output": {"chunks": "list of relevant document chunks with similarity scores"},
                "use_when": "Need information from the user's uploaded documents",
            },
            {
                "name": "summarize",
                "description": "Condense a long text into a shorter summary",
                "endpoint": "POST /tools/summarize",
                "input": {"text": "string (50-20000 chars)", "max_sentences": "int", "style": "string"},
                "output": {"summary": "string"},
                "use_when": "Retrieved content is too long to include directly in the prompt",
            },
            {
                "name": "calculator",
                "description": "Evaluate mathematical expressions precisely",
                "endpoint": "POST /tools/calculator",
                "input": {"expression": "string (e.g. '2 * (3 + 4)')"},
                "output": {"result": "float"},
                "use_when": "Need to perform numerical calculations",
            },
        ]
    }
