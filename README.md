# AturModal 🍳📈

[![CI Pipeline](https://github.com/Harinzu47/JuaraVibeCoding/actions/workflows/ci.yml/badge.svg)](https://github.com/Harinzu47/JuaraVibeCoding/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB)](https://reactjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**AturModal** is a production-grade, micro-merchant financial assistant web application. It is designed to help local culinary home industries (e.g., *ibu-ibu penjual makanan*) track daily financial performance (total spending, dynamic Cost of Goods Sold / COGS, portion-level costing, daily revenue, and net profit evaluation) through a friendly conversational interface powered by Google Gemini AI with automatic structural data extraction.

---

## 🏗️ Architectural Design (Clean Architecture)

The backend is built with FastAPI following **Clean Architecture** patterns (separation of concerns, Repository Pattern for database decoupling, and Service Layer for third-party SDK integration):

```text
AturModal/
 ├── .github/
 │    └── workflows/
 │         └── ci.yml             # GitHub Actions running Linting & Tests
 ├── app/
 │    ├── api/
 │    │    ├── v1/
 │    │    │    ├── auth.py       # Authentication endpoints (Register/Login)
 │    │    │    ├── chat.py       # AI assistant conversation & costing
 │    │    │    └── sessions.py   # Daily financial tracking sessions management
 │    │    └── deps.py            # FastAPI dependency injections
 │    ├── core/
 │    │    ├── config.py          # Unified Pydantic settings config
 │    │    └── security.py        # Password hashing & JWT helpers
 │    ├── db/
 │    │    ├── session.py         # SQLAlchemy engine and async session creation
 │    │    └── base.py            # Declarative base class
 │    ├── models/
 │    │    ├── user.py            # User database model
 │    │    ├── session.py         # Daily financial session model
 │    │    └── message.py         # Chat history model
 │    ├── schemas/
 │    │    ├── auth.py            # Pydantic schemas for auth
 │    │    ├── session.py         # Pydantic schemas for daily sessions
 │    │    └── chat.py            # Pydantic schemas for chat
 │    ├── repositories/
 │    │    ├── base.py            # Generic CRUDRouter repository pattern
 │    │    ├── user.py            # User-specific CRUD operations
 │    │    ├── session.py         # DailySession-specific database logic
 │    │    └── message.py         # ChatMessage database operations
 │    ├── services/
 │    │    ├── gemini.py          # LLM API connections, fallback models, JSON schemas
 │    │    └── pdf.py             # Laporan PDF generation via WeasyPrint
 │    ├── middleware/
 │    │    └── rate_limit.py      # Redis sliding-window IP rate limiter
 │    └── main.py                 # FastAPI application entrypoint
 ├── tests/                       # Async SQLite unit & integration tests
 │    ├── conftest.py
 │    ├── test_integration_auth.py
 │    ├── test_integration_chat.py
 │    ├── test_unit_hpp.py
 │    └── test_unit_koreksi.py
 ├── templates/                   # HTML templates for PDF rendering (Jinja2)
 ├── alembic/                     # Database migrations history
 ├── frontend/                    # React frontend client
 ├── .editorconfig
 ├── .gitignore
 ├── .env.example
 ├── LICENSE                      # MIT License
 ├── CONTRIBUTING.md
 ├── Dockerfile
 ├── requirements.txt
 └── requirements-dev.txt         # Developer dependencies (pytest, black, flake8, mypy)
```

### Key Architectural Features:
* **Separation of Concerns:** Controllers (under `app/api`) only handle HTTP requests, routing, and schema validation. Database operations are delegated to `repositories`, and heavy external logic goes into `services`.
* **Repository Pattern:** Database transactions and raw SQLAlchemy operations are decoupled from routers to facilitate mock testing.
* **Service Layer:** `GeminiService` encapsulates LLM client initialization, structured JSON schema parsing, and a fallback chain. `PDFService` offloads HTML rendering and PDF conversion to a worker thread pool.
* **Security Hardening:** Centralized JWT verification, bcrypt password hashing, fail-safe CORS configuration, and Redis sliding-window rate limiting.

---

## 🛠️ Technology Stack

* **Backend:** FastAPI, Python (Uvicorn server)
* **Database:** PostgreSQL (Production) / SQLite (Testing & Development)
* **ORM:** SQLAlchemy 2.0 (Async/Await)
* **AI:** Google GenAI SDK (Gemini Flash Model Fallback Chain)
* **Caching/Rate Limiting:** Redis (Sliding-window middleware)
* **PDF Engine:** WeasyPrint (HTML to PDF converter) + Jinja2 Templates
* **Testing:** Pytest, pytest-asyncio, pytest-cov, HTTPX AsyncClient
* **Frontend:** React (Vite), Tailwind CSS

---

## ⚙️ Configuration & Environment Variables

Copy `.env.example` to `.env` in the root directory:
```bash
cp .env.example .env
```

Define the following environment variables:
| Variable Name | Required | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://postgres:postgres@localhost:5432/aturmodal` | Database connection URL |
| `GEMINI_API_KEY` | Yes | - | Google AI Studio Gemini API Key |
| `JWT_SECRET_KEY` | Yes | - | Secret key used to sign JWT authorization tokens |
| `JWT_ALGORITHM` | No | `HS256` | Hash algorithm for JWT signing |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` | JWT expiration duration in minutes |
| `REDIS_URL` | No | `redis://localhost:6379` | Redis server address |
| `CORS_ORIGINS` | No | `["http://localhost:5173"]` | Authorized origin URL list (JSON array) |
| `GEMINI_TIMEOUT_SECONDS` | No | `30.0` | Timeout per Gemini request |

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* Redis server (optional, rate limiting will gracefully fallback to inactive if unavailable)
* GTK+ or WeasyPrint dependencies (WeasyPrint requires certain system libraries to be installed. On Windows, WeasyPrint runs fine out of the box in modern versions, but refer to WeasyPrint docs if rendering issues arise).

### Backend Setup

1. **Create and Activate Virtual Environment:**
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install Core & Dev Dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Initialize Database Migrations & Seed Data:**
   ```bash
   alembic upgrade head
   python seed_db.py
   ```

4. **Run FastAPI Server:**
   ```bash
   python -m uvicorn app.main:app --reload --port 8082
   ```
   The backend API is now running on [http://127.0.0.1:8082](http://127.0.0.1:8082). Swagger documentation is available at `/docs`.

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install node packages:**
   ```bash
   npm install
   ```

3. **Run Vite Development Server:**
   ```bash
   npm run dev
   ```
   The frontend application is now accessible at [http://localhost:5173](http://localhost:5173). Requests to `/api/*` are configured to automatically proxy to `http://localhost:8082` through `vite.config.js`.

---

## 🧪 Testing & Code Quality Audits

We maintain strict quality control standards. Tests run asynchronously using an in-memory SQLite database (`sqlite+aiosqlite`).

### 1. Run the Test Suite
```bash
python -m pytest
```

### 2. Run Linting Checks (Flake8)
```bash
flake8 app/ tests/ --ignore=E501,W503
```

### 3. Run Static Type Checking (Mypy)
```bash
mypy app/ --explicit-package-bases
```

### 4. Auto-format Code (Black & Isort)
```bash
black app/ tests/
isort app/ tests/
```

---

## 📦 Docker Containerization

To run the application inside Docker:

1. **Build the Docker Image:**
   ```bash
   docker build -t aturmodal-backend .
   ```

2. **Run Backend Container:**
   ```bash
   docker run -p 8082:8082 --env-file .env aturmodal-backend
   ```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](file:///d:/JuaraVibeCoding/LICENSE) file for details.
