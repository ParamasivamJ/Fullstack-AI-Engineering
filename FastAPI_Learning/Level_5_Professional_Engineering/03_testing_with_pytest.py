"""
Level 5 — Testing FastAPI with pytest
=======================================

Tests are not optional in AI apps — they are how you know:
  - Your API routes work correctly
  - Your Pydantic validation rejects bad input
  - Your auth system actually blocks unauthorized access
  - Your RAG pipeline returns the right schema
  - Refactoring hasn't broken anything

Expert testing means:
  - TestClient for HTTP-level route testing (no running server needed)
  - Fixtures for shared setup (fake DB, test users, tokens)
  - Parametrize for testing many inputs in one test function
  - Mock for external APIs (LLM, S3) — tests should be fast and offline

HOW TO RUN:
  pip install pytest pytest-asyncio httpx
  pytest Level_5_Professional_Engineering/03_testing_with_pytest.py -v
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from typing import Optional
import pytest

# ─────────────────────────────────────────────
# THE APP TO TEST (usually imported from your main app)
# ─────────────────────────────────────────────

app = FastAPI(title="Test Target App")

# Fake in-memory database
_users_db: dict = {}
_tasks_db: dict = {}
_next_id = 1

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1)
    priority: int = Field(1, ge=1, le=5)

class TaskOut(BaseModel):
    id: int
    title: str
    priority: int
    username: str

def get_current_user(token: str = ""):
    if token not in _users_db:
        raise HTTPException(401, "Invalid token")
    return _users_db[token]

@app.post("/register", status_code=201)
def register(user: UserCreate):
    if user.username in {u["username"] for u in _users_db.values()}:
        raise HTTPException(409, "Username taken")
    # Use username as token for simplicity in tests
    _users_db[user.username] = {"username": user.username, "token": user.username}
    return {"token": user.username}

@app.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(task: TaskCreate, token: str = ""):
    user = get_current_user(token)
    global _next_id
    task_id = _next_id
    _next_id += 1
    _tasks_db[task_id] = {"id": task_id, "title": task.title, "priority": task.priority, "username": user["username"]}
    return _tasks_db[task_id]

@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, token: str = ""):
    get_current_user(token)  # auth check
    task = _tasks_db.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


# ─────────────────────────────────────────────
# TEST SETUP
# ─────────────────────────────────────────────

# TestClient wraps the FastAPI app — it makes real HTTP requests without
# starting a server. Tests run fast and work completely offline.
client = TestClient(app)


# Fixtures are shared setup that run before each test (or before the whole session).
# @pytest.fixture creates a reusable piece of setup.

@pytest.fixture(autouse=True)
def reset_db():
    """Clears the in-memory DB before each test — ensures tests are isolated."""
    global _next_id
    _users_db.clear()
    _tasks_db.clear()
    _next_id = 1
    yield  # test runs here
    # cleanup after test (none needed in this case)


@pytest.fixture
def registered_user():
    """Creates a test user and returns their token."""
    response = client.post("/register", json={"username": "testuser", "password": "password123"})
    assert response.status_code == 201
    return response.json()["token"]


# ─────────────────────────────────────────────
# 1. REGISTRATION TESTS
# ─────────────────────────────────────────────

class TestRegistration:
    """Group related tests in a class for organization."""

    def test_register_success(self):
        """Happy path — valid registration returns 201 with a token."""
        response = client.post("/register", json={
            "username": "alice",
            "password": "securepass1",
        })
        assert response.status_code == 201
        data = response.json()
        assert "token" in data
        assert data["token"] == "alice"  # our simple token scheme

    def test_register_duplicate_username(self):
        """Registering the same username twice returns 409 Conflict."""
        client.post("/register", json={"username": "alice", "password": "securepass1"})
        response = client.post("/register", json={"username": "alice", "password": "differentpass"})
        assert response.status_code == 409
        assert "taken" in response.json()["detail"].lower()

    # @pytest.mark.parametrize runs the SAME test with MANY inputs
    # Each tuple is one test case: (username, password, expected_status)
    @pytest.mark.parametrize("username,password,expected", [
        ("ab", "password123", 422),         # username too short
        ("alice", "short", 422),            # password too short
        ("", "password123", 422),           # empty username
        ("valid_user", "validpass1", 201),  # valid
    ])
    def test_register_validation(self, username, password, expected):
        """Tests multiple invalid inputs with one parametrized test."""
        response = client.post("/register", json={"username": username, "password": password})
        assert response.status_code == expected


# ─────────────────────────────────────────────
# 2. TASK TESTS
# ─────────────────────────────────────────────

class TestTasks:

    def test_create_task_authenticated(self, registered_user):
        """Authenticated user can create a task."""
        response = client.post(
            "/tasks",
            json={"title": "Write tests", "priority": 3},
            params={"token": registered_user},  # pass auth token
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Write tests"
        assert data["priority"] == 3
        assert data["username"] == "testuser"
        assert "id" in data

    def test_create_task_unauthenticated(self):
        """Unauthenticated request returns 401."""
        response = client.post(
            "/tasks",
            json={"title": "Some task"},
            params={"token": "invalid-token"},
        )
        assert response.status_code == 401

    def test_get_task_not_found(self, registered_user):
        """Returns 404 for a task that does not exist."""
        response = client.get("/tasks/9999", params={"token": registered_user})
        assert response.status_code == 404

    def test_task_response_shape(self, registered_user):
        """Response must match the TaskOut schema exactly."""
        create_resp = client.post(
            "/tasks",
            json={"title": "Test task"},
            params={"token": registered_user},
        )
        task_id = create_resp.json()["id"]

        get_resp = client.get(f"/tasks/{task_id}", params={"token": registered_user})
        assert get_resp.status_code == 200

        data = get_resp.json()
        # Verify ALL expected fields are present
        required_fields = {"id", "title", "priority", "username"}
        assert required_fields.issubset(data.keys()), f"Missing fields: {required_fields - data.keys()}"

    @pytest.mark.parametrize("priority,expected_status", [
        (0, 422),   # below minimum
        (1, 201),   # minimum valid
        (5, 201),   # maximum valid
        (6, 422),   # above maximum
    ])
    def test_task_priority_bounds(self, registered_user, priority, expected_status):
        """Priority must be between 1 and 5 inclusive."""
        response = client.post(
            "/tasks",
            json={"title": "Task", "priority": priority},
            params={"token": registered_user},
        )
        assert response.status_code == expected_status


# ─────────────────────────────────────────────
# HOW TO RUN THESE TESTS
# ─────────────────────────────────────────────
# Run all tests:
#   pytest 03_testing_with_pytest.py -v
#
# Run a specific class:
#   pytest 03_testing_with_pytest.py::TestRegistration -v
#
# Run a specific test:
#   pytest 03_testing_with_pytest.py::TestTasks::test_create_task_authenticated -v
#
# Run with coverage report:
#   pip install pytest-cov
#   pytest 03_testing_with_pytest.py --cov=. --cov-report=term-missing
