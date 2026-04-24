"""
Level 6 — WebSockets (Real-Time AI Chat)
==========================================

WebSockets are a persistent, two-way connection between client and server.
Unlike HTTP (request → response → closed), WebSockets stay open.

When to use WebSockets vs SSE:
  - SSE (Server-Sent Events): server pushes data to client (one direction)
    → Best for: streaming LLM tokens, live notifications
  - WebSocket: both sides can send messages at any time (two directions)
    → Best for: live chat, collaborative editing, live agent feedback

For LLM streaming, SSE is simpler and usually sufficient.
Use WebSockets when the CLIENT also needs to send messages mid-stream
(e.g., interrupt the AI, provide more context, multi-agent live console).

HOW TO RUN:
  uvicorn 05_websockets:app --reload

TEST with wscat (install with: npm install -g wscat):
  wscat -c ws://localhost:8000/ws/chat?token=test-token
  Then type messages and see responses.

Or use the browser console:
  const ws = new WebSocket('ws://localhost:8000/ws/chat?token=test-token');
  ws.onmessage = (e) => console.log(JSON.parse(e.data));
  ws.send(JSON.stringify({message: "Hello AI!"}));
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
import asyncio
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

app = FastAPI(title="Level 6: WebSockets")


# ─────────────────────────────────────────────
# CONNECTION MANAGER
# ─────────────────────────────────────────────
# In real multi-user apps, you need to track all active connections.
# This manager lets you broadcast to all users or send to a specific user.

class ConnectionManager:
    def __init__(self):
        # user_id → WebSocket connection
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept the WebSocket handshake and register the connection."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected: {user_id}. Total: {len(self.active_connections)}")

    def disconnect(self, user_id: str):
        """Remove a disconnected user."""
        self.active_connections.pop(user_id, None)
        logger.info(f"WebSocket disconnected: {user_id}. Total: {len(self.active_connections)}")

    async def send_to_user(self, user_id: str, data: dict):
        """Send a JSON message to a specific user."""
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_text(json.dumps(data))

    async def broadcast(self, data: dict, exclude_user: Optional[str] = None):
        """Send a JSON message to all connected users."""
        for uid, ws in self.active_connections.items():
            if uid != exclude_user:
                try:
                    await ws.send_text(json.dumps(data))
                except Exception:
                    pass  # Connection may have dropped — handled by disconnect


manager = ConnectionManager()


# ─────────────────────────────────────────────
# MESSAGE TYPES
# ─────────────────────────────────────────────

class IncomingMessage(BaseModel):
    """Message sent from client to server."""
    message: str
    session_id: Optional[str] = None


class OutgoingToken(BaseModel):
    """One streamed token from the AI."""
    type: str = "token"
    token: str


class OutgoingDone(BaseModel):
    """Signals that streaming is complete."""
    type: str = "done"
    session_id: str


class OutgoingError(BaseModel):
    """Error message."""
    type: str = "error"
    detail: str


# ─────────────────────────────────────────────
# FAKE STREAMING LLM
# ─────────────────────────────────────────────

async def stream_llm_tokens(message: str):
    """Simulates token-by-token LLM output."""
    response = f"WebSocket response to '{message}': This demonstrates real-time token streaming over a persistent connection."
    for word in response.split():
        await asyncio.sleep(0.08)
        yield word + " "


# ─────────────────────────────────────────────
# 1. SIMPLE WEBSOCKET CHAT
# ─────────────────────────────────────────────

@app.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    # Auth via query param — WebSocket handshake can't easily use headers
    token: str = Query(..., description="Authentication token"),
):
    """
    WebSocket endpoint for streaming AI chat.

    Message flow:
      Client → {"message": "Hello!"} → Server
      Server → {"type": "token", "token": "Hi "} → Client (repeated per token)
      Server → {"type": "done", "session_id": "..."} → Client
    """
    # Simple token-based auth (replace with JWT validation in production)
    if not token or token == "invalid":
        await websocket.close(code=1008, reason="Unauthorized")
        return

    user_id = f"user_{token}"  # derive user from token

    await manager.connect(websocket, user_id)

    try:
        while True:
            # Wait for a message from the client
            raw_data = await websocket.receive_text()

            try:
                incoming = IncomingMessage.model_validate_json(raw_data)
            except Exception:
                await websocket.send_text(
                    OutgoingError(detail="Invalid message format. Send JSON: {\"message\": \"...\"}").model_dump_json()
                )
                continue

            logger.info(f"[WS] {user_id}: {incoming.message[:50]}")

            # Stream the response token by token
            async for token_text in stream_llm_tokens(incoming.message):
                await websocket.send_text(
                    json.dumps({"type": "token", "token": token_text})
                )

            # Signal completion
            session_id = incoming.session_id or "default"
            await websocket.send_text(
                json.dumps({"type": "done", "session_id": session_id})
            )

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"[WS] {user_id} disconnected gracefully")
    except Exception as e:
        logger.error(f"[WS] {user_id} unexpected error: {e}")
        manager.disconnect(user_id)


# ─────────────────────────────────────────────
# 2. MULTI-USER BROADCAST (collaboration)
# ─────────────────────────────────────────────

@app.websocket("/ws/room/{room_id}")
async def websocket_room(websocket: WebSocket, room_id: str, username: str = Query(...)):
    """
    A shared room where all connected users receive each other's messages.
    Useful for: collaborative AI workspaces, live agent monitoring dashboards.
    """
    connection_key = f"{room_id}:{username}"
    await manager.connect(websocket, connection_key)

    # Notify everyone else in the room
    await manager.broadcast(
        {"type": "system", "message": f"{username} joined room {room_id}"},
        exclude_user=connection_key,
    )

    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast the message to all users in the room
            await manager.broadcast(
                {"type": "message", "from": username, "content": data},
                exclude_user=connection_key,  # don't echo back to sender
            )
    except WebSocketDisconnect:
        manager.disconnect(connection_key)
        await manager.broadcast(
            {"type": "system", "message": f"{username} left the room"},
        )


# ─────────────────────────────────────────────
# HTTP ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/ws/connections", tags=["WebSocket"])
def active_connections():
    return {
        "active_connections": list(manager.active_connections.keys()),
        "count": len(manager.active_connections),
    }
