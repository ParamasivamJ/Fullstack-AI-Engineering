# Project 1: Full-Stack CRUD App with Authentication

A modern, full-stack Task Management application built as the foundation of the Full-Stack AI Engineering portfolio. This project demonstrates core web development skills including RESTful API design, relational database modeling, stateless authentication, and dynamic frontend UI construction.

## Architecture & Tech Stack

This project uses a decoupled Client-Server architecture:

### Backend
- **Framework:** FastAPI (Python)
- **Database:** SQLite (via SQLAlchemy ORM)
- **Validation:** Pydantic
- **Security:** JWT (JSON Web Tokens) & Passlib (Bcrypt hashing)

### Frontend
- **Framework:** Next.js 14 (App Router)
- **State Management:** React Context API (`AuthContext`)
- **Styling:** Pure Vanilla CSS with CSS Variables (No Tailwind)
- **Design System:** Custom "Glassmorphism" UI with dynamic Light/Dark modes

---

## Key Features

- **Secure Authentication Flow:** Users can register and log in. Passwords are cryptographically hashed using bcrypt before hitting the database.
- **Stateless Sessions:** Uses JWTs for session management. The frontend explicitly passes the token in the `Authorization` header for protected API routes.
- **Full CRUD Operations:** Users can Create, Read, and Delete tasks. Tasks are strictly bound to the `owner_id` (User A cannot see or delete User B's tasks).
- **Premium UI:** Features a translucent, blurred glass effect (`backdrop-filter`) that automatically adapts to the user's Light or Dark mode preference.

---

## Local Setup & Installation

Follow these steps to run the project locally.

### 1. Start the Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   
   # Windows:
   .\venv\Scripts\Activate.ps1
   # Mac/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload
   ```
   *The backend will now be running on `http://127.0.0.1:8000`.*

### 2. Start the Frontend

1. Open a new terminal window and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Run the Next.js development server:
   ```bash
   npm run dev
   ```
   *The frontend will now be running on `http://localhost:3000`.*

---

## API Documentation

Because we used FastAPI, interactive Swagger documentation is generated automatically! 

Once the backend is running, navigate to:
**[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

### Available Endpoints:
- `POST /register`: Create a new user account.
- `POST /token`: Authenticate and receive a JWT Bearer token.
- `POST /tasks`: Create a new task (Requires Auth).
- `GET /tasks`: Retrieve all tasks for the logged-in user (Requires Auth).
- `DELETE /tasks/{task_id}`: Delete a specific task (Requires Auth).

---

*Part of the 10-Step Full Stack AI Engineering Portfolio Roadmap.*
