# Level 1 — HTTP Concepts

This is the foundation everything else is built on.
You do not need to memorise all of this immediately —
read it once, then refer back when something is unclear.

---

## What is HTTP?

HTTP stands for **HyperText Transfer Protocol**.
It is the language that computers use to send requests and receive responses over the internet.

When you open a browser and type a URL, your browser sends an **HTTP Request** to a server.
The server reads that request, does some work, and sends back an **HTTP Response**.

Every API call your frontend makes is an HTTP request.
Every reply from FastAPI is an HTTP response.

---

## The Anatomy of an HTTP Request

```
METHOD  /path?query=value  HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{ "message": "hello" }
```

| Part | What it is | Example |
|------|-----------|---------|
| **Method** | The action you want to take | `GET`, `POST`, `PUT`, `DELETE` |
| **Path** | Which resource to act on | `/users/42` |
| **Query Params** | Optional filters in the URL | `?limit=10&page=2` |
| **Headers** | Metadata about the request | `Authorization`, `Content-Type` |
| **Body** | Data you are sending (POST/PUT only) | `{"username": "alice"}` |

---

## HTTP Methods — The Verbs

Think of methods like verbs in English. They tell the server what you want to DO.

| Method | Meaning | Example Use |
|--------|---------|-------------|
| `GET` | Fetch / Read | Get a list of tasks |
| `POST` | Create | Create a new user |
| `PUT` | Replace entirely | Replace a task with new data |
| `PATCH` | Update partially | Update only the task title |
| `DELETE` | Remove | Delete a task |

> **Rule:** GET requests never have a body. They only pass data through the URL.

---

## HTTP Status Codes — The Response Signal

Every HTTP response includes a **status code** — a 3-digit number that tells you
what happened without reading the full response body.

### 2xx — Success

| Code | Name | When to use |
|------|------|-------------|
| `200` | OK | Request succeeded, returning data |
| `201` | Created | A new resource was successfully created |
| `204` | No Content | Success but nothing to return (e.g., after DELETE) |

### 4xx — Client Error (the requester did something wrong)

| Code | Name | When to use |
|------|------|-------------|
| `400` | Bad Request | Invalid input, failed validation |
| `401` | Unauthorized | No token, or token is invalid |
| `403` | Forbidden | Token is valid, but you do not have permission |
| `404` | Not Found | The resource does not exist |
| `409` | Conflict | Resource already exists (e.g., duplicate username) |
| `422` | Unprocessable Entity | FastAPI's default for validation errors |
| `429` | Too Many Requests | Rate limit exceeded |

### 5xx — Server Error (the server made a mistake)

| Code | Name | When to use |
|------|------|-------------|
| `500` | Internal Server Error | Something crashed on the server side |
| `503` | Service Unavailable | Server is down or overloaded |

---

## Headers — The Metadata Envelope

Headers carry context about the request or response.
They are key-value pairs sent alongside the body.

### Common Request Headers

| Header | Purpose | Example |
|--------|---------|---------|
| `Authorization` | Send a JWT token | `Bearer eyJhbGc...` |
| `Content-Type` | Tell the server what format the body is in | `application/json` |
| `Accept` | Tell the server what format you want back | `application/json` |
| `X-Request-ID` | Unique ID for tracing this specific request | `uuid-abc-123` |

### Common Response Headers

| Header | Purpose |
|--------|---------|
| `Content-Type` | What format the response body is in |
| `X-RateLimit-Remaining` | How many requests you have left |

---

## JSON — The Universal Language

JSON (JavaScript Object Notation) is the format APIs use to send structured data.
FastAPI reads and returns JSON automatically.

```json
{
  "id": 1,
  "username": "alice",
  "tasks": [
    { "id": 10, "title": "Write tests", "completed": false }
  ]
}
```

**Rules:**
- Keys must be in double quotes
- Values can be: string, number, boolean, null, array, or another object
- No trailing commas

---

## URL Structure

```
https://api.example.com/v1/users/42?include_tasks=true
|_____|  |_____________| |_| |___| |_| |________________|
scheme      host         ver resource id  query parameter
```

- **Scheme:** `https` means encrypted, `http` means plain text
- **Host:** the server's domain or IP address
- **Path:** identifies the specific resource
- **Query string:** starts with `?`, key-value pairs separated by `&`

---

## Key Takeaways

1. Every API interaction is a request + response cycle.
2. The **method** says what to do, the **path** says what to do it to.
3. **Status codes** are your API's way of communicating outcomes clearly.
4. **Headers** carry authentication and metadata.
5. **JSON** is how structured data travels over HTTP.

Next: `02_request_lifecycle.md` — what actually happens between a browser click and a response.
