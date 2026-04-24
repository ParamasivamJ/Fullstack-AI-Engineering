"""
Level 5 — Full JWT Authentication System
==========================================

This is a complete, production-ready authentication system.
It implements:
  - Password hashing with bcrypt
  - JWT access tokens (short-lived: 30 min)
  - JWT refresh tokens (long-lived: 7 days)
  - Protected routes via dependencies
  - Role-based access control (RBAC)

HOW TO RUN:
  pip install python-jose[cryptography] passlib[bcrypt] python-multipart
  uvicorn 01_jwt_auth_full:app --reload
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Annotated
from enum import Enum

app = FastAPI(title="Level 5: Full JWT Auth")


# ─────────────────────────────────────────────
# CONFIGURATION (move these to .env in production)
# ─────────────────────────────────────────────

SECRET_KEY = "your-256-bit-secret-key-here-change-in-production"
REFRESH_SECRET_KEY = "different-secret-key-for-refresh-tokens"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ─────────────────────────────────────────────
# PASSWORD HASHING
# ─────────────────────────────────────────────

# CryptContext manages password hashing schemes.
# bcrypt is the industry standard — it is intentionally slow to resist brute-force.
# deprecated="auto" will warn you when a hash uses an outdated scheme.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hashes a plain-text password. NEVER store plain passwords."""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Returns True if plain matches the hash. Handles timing-safe comparison."""
    return pwd_context.verify(plain, hashed)


# ─────────────────────────────────────────────
# JWT TOKEN CREATION AND VALIDATION
# ─────────────────────────────────────────────

class TokenType(str, Enum):
    access = "access"
    refresh = "refresh"


def create_token(data: dict, expires_delta: timedelta, token_type: TokenType) -> str:
    """
    Creates a signed JWT token.

    JWT structure:
      Header:  {"alg": "HS256", "typ": "JWT"}
      Payload: {"sub": "alice", "exp": 1234567890, "type": "access"}
      Signature: HMAC-SHA256(header + "." + payload, SECRET_KEY)

    The signature is what makes the token tamper-proof.
    If any part of the token changes, the signature no longer matches.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta

    to_encode.update({
        "exp": expire,             # expiry timestamp — jose validates this automatically
        "iat": datetime.utcnow(), # issued at — useful for audit logs
        "type": token_type.value, # custom claim to distinguish token types
    })

    # Choose the correct secret based on token type
    secret = REFRESH_SECRET_KEY if token_type == TokenType.refresh else SECRET_KEY
    return jwt.encode(to_encode, secret, algorithm=ALGORITHM)


def decode_token(token: str, token_type: TokenType) -> dict:
    """
    Decodes and validates a JWT token.
    Raises HTTPException if the token is invalid, expired, or wrong type.
    """
    secret = REFRESH_SECRET_KEY if token_type == TokenType.refresh else SECRET_KEY
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])

        # Verify this is the correct token type
        if payload.get("type") != token_type.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─────────────────────────────────────────────
# ROLE-BASED ACCESS CONTROL
# ─────────────────────────────────────────────

class UserRole(str, Enum):
    admin = "admin"
    user = "user"
    viewer = "viewer"


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.user


class UserOut(BaseModel):
    id: int
    username: str
    role: UserRole


class TokenPair(BaseModel):
    """Both tokens returned on login."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


# ─────────────────────────────────────────────
# FAKE DATABASE (replace with SQLAlchemy + PostgreSQL)
# ─────────────────────────────────────────────

fake_db: dict[str, dict] = {}
next_id = 1


# ─────────────────────────────────────────────
# OAUTH2 + DEPENDENCIES
# ─────────────────────────────────────────────

# tokenUrl="token" tells Swagger UI where to send login requests
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """
    Validates the access token and returns the current user.
    This dependency is injected into every protected route.
    """
    payload = decode_token(token, TokenType.access)
    username = payload.get("sub")

    if not username or username not in fake_db:
        raise HTTPException(status_code=401, detail="User not found")

    return fake_db[username]


def require_role(required_role: UserRole):
    """
    Factory function that returns a dependency enforcing a specific role.
    Usage: admin_only = Depends(require_role(UserRole.admin))
    """
    def role_checker(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        if current_user["role"] != required_role.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires the '{required_role.value}' role",
            )
        return current_user
    return role_checker


# Type aliases for clean route signatures
AuthUser = Annotated[dict, Depends(get_current_user)]
AdminOnly = Annotated[dict, Depends(require_role(UserRole.admin))]


# ─────────────────────────────────────────────
# AUTH ENDPOINTS
# ─────────────────────────────────────────────

@app.post("/auth/register", response_model=UserOut, status_code=201, tags=["Auth"])
def register(user: UserCreate):
    global next_id
    if user.username in fake_db:
        raise HTTPException(status_code=409, detail="Username already taken")

    fake_db[user.username] = {
        "id": next_id,
        "username": user.username,
        "hashed_password": hash_password(user.password),
        "role": user.role.value,
    }
    next_id += 1
    return UserOut(**fake_db[user.username])


@app.post("/auth/login", response_model=TokenPair, tags=["Auth"])
def login(form: OAuth2PasswordRequestForm = Depends()):
    """
    Accepts username + password (as form data — required by OAuth2 spec).
    Returns both access and refresh tokens.
    """
    user = fake_db.get(form.username)
    if not user or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {"sub": user["username"], "role": user["role"]}

    access_token = create_token(
        token_data,
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        TokenType.access,
    )
    refresh_token = create_token(
        token_data,
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        TokenType.refresh,
    )

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@app.post("/auth/refresh", response_model=TokenPair, tags=["Auth"])
def refresh_tokens(req: RefreshRequest):
    """
    Issues a new access token using a valid refresh token.
    This lets users stay logged in without re-entering their password.
    """
    payload = decode_token(req.refresh_token, TokenType.refresh)
    username = payload.get("sub")

    if not username or username not in fake_db:
        raise HTTPException(status_code=401, detail="User not found")

    user = fake_db[username]
    token_data = {"sub": user["username"], "role": user["role"]}

    new_access = create_token(token_data, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), TokenType.access)
    new_refresh = create_token(token_data, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), TokenType.refresh)

    return TokenPair(access_token=new_access, refresh_token=new_refresh)


# ─────────────────────────────────────────────
# PROTECTED ROUTES
# ─────────────────────────────────────────────

@app.get("/me", response_model=UserOut, tags=["Protected"])
def get_me(current_user: AuthUser):
    """Any logged-in user can access this."""
    return UserOut(**current_user)


@app.get("/admin/users", tags=["Protected"])
def list_users(admin: AdminOnly):
    """Only admins can access this route."""
    return {
        "users": [{"id": u["id"], "username": u["username"], "role": u["role"]}
                  for u in fake_db.values()],
        "requested_by": admin["username"],
    }
