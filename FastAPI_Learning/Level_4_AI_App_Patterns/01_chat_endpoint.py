"""
Level 4 — Chat Endpoint and Streaming (AI App Pattern)
=======================================================

This is the heart of every AI application.
Streaming is non-negotiable for LLM apps — nobody wants to stare at a loading
spinner for 5 seconds waiting for a full response.

Streaming sends tokens to the client AS THEY ARRIVE from the model.
The chat interface updates in real-time, like ChatGPT's output.

HOW TO RUN:
  uvicorn 01_chat_endpoint:app --reload

To test streaming, open a terminal and run:
  curl -N http://localhost:8000/chat/stream -X POST \
    -H "Content-Type: application/json" \
    -d '{"message": "Explain RAG in simple terms", "stream": true}'
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Literal, AsyncGenerator
import asyncio
import json

app = FastAPI(title="Level 4: Chat and Streaming")


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class ChatMessage(BaseModel):
    """A single message in a conversation."""
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """
    Request schema for a chat endpoint.
    Mirrors the OpenAI chat completion request format —
    learning this shape means you already know how to call OpenAI, Anthropic, etc.
    """
    message: str = Field(..., min_length=1, max_length=4000,
                         description="The user's latest message")

    # Conversation history — allows multi-turn conversations
    history: list[ChatMessage] = Field(default=[],
                                       description="Previous messages in this conversation")

    # Model selection — in real apps, validate user has access to this model
    model: Literal["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet"] = "gpt-4o-mini"

    temperature: float = Field(default=0.7, ge=0.0, le=2.0,
                               description="Higher = more creative, lower = more deterministic")

    max_tokens: int = Field(default=1000, ge=1, le=4096,
                            description="Maximum tokens in the response")

    stream: bool = Field(default=False, description="Enable token-by-token streaming")


class ChatResponse(BaseModel):
    """Response schema for non-streaming chat."""
    message: str
    model: str
    input_tokens: int      # Track for cost monitoring
    output_tokens: int     # Track for cost monitoring
    finish_reason: str     # "stop" = natural end, "length" = hit max_tokens


# ─────────────────────────────────────────────
# FAKE LLM (replace with real LLM calls in production)
# ─────────────────────────────────────────────
# This simulates what an LLM returns.
# In production, replace with: openai.chat.completions.create(...)

async def fake_llm_complete(message: str, model: str, max_tokens: int) -> ChatResponse:
    """Simulates a complete (non-streaming) LLM response."""
    await asyncio.sleep(1.5)  # simulate API latency

    response_text = (
        f"This is a simulated response from {model} to your message: '{message}'. "
        f"In production, this would be a real LLM response."
    )

    return ChatResponse(
        message=response_text,
        model=model,
        input_tokens=len(message.split()),
        output_tokens=len(response_text.split()),
        finish_reason="stop",
    )


async def fake_llm_stream(message: str, model: str) -> AsyncGenerator[str, None]:
    """
    Simulates a streaming LLM response.
    In production, replace with:
      async for chunk in openai.chat.completions.create(stream=True, ...):
          yield chunk.choices[0].delta.content or ""
    """
    # Simulate token-by-token output
    words = f"Streaming response from {model}: Here is a word-by-word answer to: {message}".split()

    for word in words:
        await asyncio.sleep(0.1)  # simulate time between tokens
        yield word + " "          # yield one word at a time


# ─────────────────────────────────────────────
# 1. NON-STREAMING CHAT ENDPOINT
# ─────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(req: ChatRequest):
    """
    Standard chat endpoint — waits for full response then returns it.
    Use this for: background processing, structured JSON output, testing.
    Avoid for: user-facing chat UIs (latency is painful).
    """
    try:
        response = await fake_llm_complete(req.message, req.model, req.max_tokens)
        return response
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="LLM API timed out")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")


# ─────────────────────────────────────────────
# 2. STREAMING CHAT ENDPOINT
# ─────────────────────────────────────────────

def create_sse_event(data: str, event: str = "message") -> str:
    """
    Formats data as a Server-Sent Event (SSE).

    SSE format:
      event: message
      data: {"token": "hello"}

      (blank line separates events)

    The browser's EventSource API reads this format natively.
    """
    payload = json.dumps({"token": data})
    return f"event: {event}\ndata: {payload}\n\n"


async def streaming_generator(message: str, model: str) -> AsyncGenerator[str, None]:
    """
    Wraps the LLM stream in SSE format.
    This is what the frontend's EventSource receives.
    """
    try:
        async for token in fake_llm_stream(message, model):
            # Send each token as an SSE event
            yield create_sse_event(token)

        # Send a special 'done' event so the frontend knows streaming is complete
        yield create_sse_event("", event="done")

    except Exception as e:
        # Send an error event — the frontend can handle this gracefully
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@app.post("/chat/stream", tags=["Chat"])
async def chat_stream(req: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    The frontend connects like this (JavaScript):
      const source = new EventSource('/chat/stream');
      source.onmessage = (e) => {
        const { token } = JSON.parse(e.data);
        appendToUI(token);
      };
      source.addEventListener('done', () => source.close());
    """
    return StreamingResponse(
        # Pass the async generator — FastAPI streams it automatically
        streaming_generator(req.message, req.model),
        # text/event-stream is the MIME type for SSE
        media_type="text/event-stream",
        headers={
            # These headers are required for SSE to work correctly
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if using nginx
        },
    )


# ─────────────────────────────────────────────
# 3. MULTI-TURN CHAT (conversation history)
# ─────────────────────────────────────────────

@app.post("/chat/multi-turn", tags=["Chat"])
async def multi_turn_chat(req: ChatRequest):
    """
    Shows how to handle conversation history.
    The client sends the full conversation history with each request.
    The server is stateless — history management is the client's responsibility.

    In production, you would:
    1. Load history from DB (for long conversations)
    2. Truncate history to fit within token limits
    3. Pass formatted history to the LLM
    """
    # Build the full message list for the LLM
    messages_for_llm = []

    # Add conversation history
    for msg in req.history[-10:]:  # Limit to last 10 messages to control token count
        messages_for_llm.append({
            "role": msg.role,
            "content": msg.content,
        })

    # Add the current user message
    messages_for_llm.append({"role": "user", "content": req.message})

    # In production: pass messages_for_llm to OpenAI/Anthropic/etc.
    response_text = f"Echo (multi-turn): {req.message} [history: {len(req.history)} messages]"

    return {
        "message": response_text,
        "history_received": len(req.history),
        "model": req.model,
    }
