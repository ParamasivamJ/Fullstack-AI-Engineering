"""
Level 6 — Routers: Users
=========================
Production-pattern router for user management.
Thin routes → call service layer → service calls CRUD.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# In a real project these imports would be:
# from database import get_async_db
# from dependencies.auth import get_current_user, require_admin
# from schemas.user import UserCreate, UserOut, UserUpdate
# from crud import user as user_crud
# Here we use simplified placeholders so the file runs standalone.

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Annotated
from uuid import UUID, uuid4
from datetime import datetime

router = APIRouter()


# ─── Simplified schemas (normally imported from schemas/user.py) ──────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(...)
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[str] = None

class UserOut(BaseModel):
    id: str
    username: str
    email: str
    role: str = "user"
    created_at: str


# ─── Fake DB ─────────────────────────────────────────────────────────────

_users: dict[str, dict] = {}


# ─── Routes ──────────────────────────────────────────────────────────────

@router.post("/", response_model=UserOut, status_code=201,
             summary="Register a new user account")
async def create_user(user: UserCreate):
    """
    Creates a new user.
    In production: calls user_crud.create_user(db, user).
    Hashing happens in the CRUD layer, not here.
    """
    if any(u["username"] == user.username for u in _users.values()):
        raise HTTPException(status_code=409, detail="Username already taken")

    user_id = str(uuid4())
    record = {
        "id": user_id,
        "username": user.username,
        "email": user.email,
        "role": "user",
        "created_at": datetime.utcnow().isoformat(),
    }
    _users[user_id] = record
    return UserOut(**record)


@router.get("/me", response_model=UserOut, summary="Get the current user's profile")
async def get_me(token: str = ""):
    """
    Protected: returns the current user's profile.
    In production: current_user = Depends(get_current_user)
    """
    if not token or token not in _users:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserOut(**_users[token])


@router.patch("/me", response_model=UserOut, summary="Update the current user's profile")
async def update_me(updates: UserUpdate, token: str = ""):
    if not token or token not in _users:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = _users[token]
    if updates.email:
        user["email"] = updates.email
    return UserOut(**user)


@router.get("/{user_id}", response_model=UserOut, summary="Get a user by ID (admin only)")
async def get_user(user_id: str, token: str = ""):
    """
    In production: restricted with Depends(require_admin).
    Regular users should never be able to look up other users by ID.
    """
    user = _users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(**user)
