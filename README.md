English | [Español](README.es.md)

# 🗂️ Tasks API with FastAPI

A REST API for managing tasks and users across projects within groups — with JWT authentication, role-based permissions, per-project real-time chat, task comments, and async notifications. Built as a personal portfolio project focused on scalable backend design, collaborative systems, and real-time communication.

[![CI - Lint & Test](https://github.com/SrStamm/API-de-tareas-con-FastAPI/actions/workflows/test.yaml/badge.svg)](https://github.com/SrStamm/API-de-tareas-con-FastAPI/actions/workflows/test.yaml)

- **Status:** Active development / stable MVP
- **Deploy:** Local VM (Docker Compose + PostgreSQL)

---

## 🚀 Overview

Hierarchy: **groups → projects → tasks → comments**. Users register, join groups, get roles, and collaborate on projects in real time.

### Authentication & security

- Register, login, logout, and token refresh with JWT (HS256)
- Access token (default 15 min) + refresh token (default 7 days)
- Logout revokes sessions via DB-backed session rows (allowlist)
- Roles and permissions scoped per group and per project
- All secrets come from environment variables

### Groups & projects

- Create, edit, and delete groups
- Manage group members
- Create and administer projects inside groups

### Tasks & comments

- Create, edit, delete, and assign tasks
- Comments on assigned tasks
- Status tracking and due-date control

### Real-time

- In-app notifications over WebSockets (task assigned, task updated, comment mention, …)
- Per-project chat (WebSocket + Redis pub/sub, channels `user:{id}` and `project:{id}`)
- Pending notifications persisted asynchronously with Celery (Redis broker)

---

## 🧱 Architecture

Modular **layered architecture** — each layer has one job, which keeps business logic testable in isolation and decouples the API from infrastructure:

```mermaid
flowchart LR
    Client["Client (Web / REST)"] -->|"HTTP + JWT"| API["FastAPI routers<br/>auth · user · group · project · task · comment"]
    Client <-->|"WebSocket"| WS["WS router /ws"]
    API --> Services["Services (business logic)"]
    Services --> Repos["Repositories"]
    Repos --> PG[("PostgreSQL")]
    WS --> SM["Socket manager"]
    SM <-->|"pub/sub"| Redis[("Redis")]
    SM -->|"push events"| Client
    Celery["Celery worker"] <-->|"broker / results"| Redis
    Celery --> PG
    Sched["Scheduler (5h)"] --> PG
```

Notification flow — live users get an immediate push; offline users get a pending notification stored for later retrieval:

```mermaid
flowchart LR
    Ev["Event (assigned · updated · mention)"] --> Redis[("Redis pub/sub")]
    Redis --> SM["Socket manager"]
    SM -->|"push if online"| Client["WebSocket client"]
    SM -->|"else enqueue"| Celery["Celery worker"]
    Celery -->|"persist pending"| PG[("PostgreSQL")]
```

- **Routers** (`api/v1/routers/`): HTTP + WebSocket endpoint definitions
- **Dependencies** (`dependency/`): per-endpoint DI wiring (auth, permissions, sessions)
- **Services** (`services/`): business logic
- **Repositories** (`repositories/`): persistence, SQLModel over PostgreSQL
- **Models** (`models/`): DB models, request/response schemas, exceptions
- **Real-time layer** (`core/socket_manager.py`, `core/event_ws.py`): connection registry + Redis pub/sub fan-out
- **Background jobs**: Celery worker (`tasks.py`) for pending notifications; APScheduler (lifespan) runs a session-cleanup job every 5h (`core/auto.py`)

---

## 🛠️ Tech stack

| Category | Technology |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI |
| ORM / validation | SQLModel (Pydantic) |
| Database | PostgreSQL (+ Alembic migrations) |
| Cache / pub-sub | Redis |
| Async tasks | Celery (Redis broker) |
| Scheduler | APScheduler |
| Auth | JWT (python-jose, HS256) |
| Tests | pytest, pytest-cov |
| CI | GitHub Actions |
| Containers | Docker & Docker Compose |

---

## 🚀 Getting started

### Prerequisites

- Python 3.12
- PostgreSQL and Redis (or just Docker + Docker Compose)

### Clone

```bash
git clone git@github.com:SrStamm/API-de-tareas-con-FastAPI.git
cd API-de-tareas-con-FastAPI
```

### Local install

```bash
python -m venv env
source env/bin/activate     # Linux / macOS
env\Scripts\activate        # Windows

# App dependencies
pip install -r requirements.txt

# Test dependencies (optional, needed to run the suite)
pip install -r requirements-test.txt
```

Create a `.env` file (see [Environment variables](#environment-variables)), then:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

### Docker

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000` (PostgreSQL and Redis included in the stack).

---

## 🔐 Environment variables

Create a `.env` file at the project root. `SECRET_KEY` and `ALGORITHM` are **required** — the app fails at startup without them. If `DATABASE_URL` is set, it takes precedence over the individual `POSTGRES_*` values.

| Variable | Used in | Default | Notes |
|---|---|---|---|
| `POSTGRES_USER` | `db/database.py` | — | Required |
| `POSTGRES_PASSWORD` | `db/database.py` | — | Required |
| `POSTGRES_DB` | `db/database.py` | — | Required |
| `POSTGRES_HOST` | `db/database.py` | — | Required |
| `POSTGRES_PORT` | `db/database.py` | — | Required |
| `DATABASE_URL` | `db/database.py` | — | Full SQLAlchemy URL; takes precedence over `POSTGRES_*` |
| `REDIS_HOST` | `db/database.py` | `localhost` | |
| `REDIS_PORT` | `db/database.py` | `6379` | |
| `REDIS_DB` | `db/database.py` | `0` | |
| `REDIS_PASSWORD` | Redis client | — | Required in the Docker setup |
| `REDIS_URL` | Celery (`tasks.py`) | — | Broker URL |
| `SECRET_KEY` | auth | — | **Required — startup fails without it** |
| `ALGORITHM` | auth | — | **Required — e.g. `HS256`** |
| `ACCESS_TOKEN_DURATION` | `services/auth_services.py` | `15` | Access token lifetime in **minutes** |
| `REFRESH_TOKEN_DURATION` | `services/auth_services.py` | `7` | Refresh token lifetime in **days** |

Copy-pasteable example (fake values only — generate your own):

```bash
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-me
POSTGRES_DB=tasks_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
# DATABASE_URL takes precedence when set:
# DATABASE_URL=postgresql+psycopg2://postgres:change-me@localhost:5432/tasks_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=change-me
REDIS_URL=redis://localhost:6379/0

# Auth (required — startup fails without these)
SECRET_KEY=replace-with-a-long-random-string
ALGORITHM=HS256
ACCESS_TOKEN_DURATION=15
REFRESH_TOKEN_DURATION=7
```

---

## 📖 API documentation

Once the server is running:

- **Swagger UI:** <http://localhost:8000/docs>
- **Redoc:** <http://localhost:8000/redoc>

---

## 🧪 Testing

| Command | What it does |
|---|---|
| `pytest -q --disable-warnings` | Run the full suite (needs Redis on `localhost:6379`) |
| `pytest -vv` | Verbose run |
| `pytest --cov=./api/v1 --cov-report=html` | Coverage of routers → `htmlcov/index.html` |
| `pytest --cov=. --cov-report=html` | Full-project coverage → `htmlcov/index.html` |
| `src/ci-test.sh` | CI entrypoint — exits non-zero on test failure |

Notes:

- Tests run against **SQLite** (`test/conftest.py`) with **Redis at `localhost:6379`**.
- `src/test.sh` starts Redis for you (`docker start redis-stack`) before running pytest.
- Requirements are split: `requirements.txt` (app) vs `requirements-test.txt` (pytest, pytest-cov, …).

**CI:** GitHub Actions (`.github/workflows/test.yaml`) runs on every push / PR to `main`: pytest over `./test/test_routers`, plus a non-blocking flake8 lint pass.

---

## 🖥️ Demo

- **Frontend:** <https://front-task-api-vanilla.vercel.app/dashboard/tasks>
- **Username:** `test`
- **Password:** `test123`

> These credentials are for the **public demo frontend only**. The frontend is a demo client; the main focus of this project is the backend design and architecture.

### Screenshots

<!-- TODO: add screenshot — tasks dashboard → save as docs/images/dashboard.png -->
<!-- TODO: add screenshot — task detail with comments → save as docs/images/task-detail.png -->
<!-- TODO: add screenshot — real-time project chat → save as docs/images/chat.png -->
<!-- TODO: add screenshot — Swagger UI → save as docs/images/swagger.png -->

<!-- After recording, embed them here, e.g.:
![Tasks dashboard](docs/images/dashboard.png)
Store image files under docs/images/.
-->

---

## ⚠️ Known limitations

Honest list of what is *not* there yet — each entry includes why it matters:

1. **Notification channels** — real-time delivery is WebSocket + in-app only; no email or mobile push. Password reset and email verification are not implemented.
2. **Single-instance deployment** — the demo runs on a single local VM; horizontal scaling and multi-instance WebSocket fan-out have not been load-tested.
3. **Test/database drift** — the automated suite runs on SQLite while dev/staging use PostgreSQL; Postgres-specific queries are not exercised in CI, so a small behavioral drift risk remains.
4. **Rate limiting currently disabled** — per-endpoint limits exist (`core/limiter.py`) but the middleware wiring is commented out in `main.py`; it must be re-enabled and its "limit exceeded" response fixed to HTTP 429 before public exposure.
5. **Observability** — structured logging (structlog) exists, but there is no `/health` endpoint, metrics, or tracing yet.
6. **Coverage is reported but not gated** — no minimum coverage threshold is enforced in CI, and WebSocket integration paths are only lightly tested (mocked unit tests, no end-to-end pub/sub test).

---

## 📄 License

This project is licensed under the MIT License ([OSI reference](https://opensource.org/licenses/MIT)).
