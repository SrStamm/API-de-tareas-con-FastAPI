English | [Español](README.es.md)

# 🗂️ API de Tareas con FastAPI

Una API REST para gestionar tareas y usuarios en proyectos dentro de grupos — con autenticación JWT, permisos basados en roles, chat en tiempo real por proyecto, comentarios en tareas y notificaciones asíncronas. Proyecto personal de portafolio enfocado en diseño de backend escalable, sistemas colaborativos y comunicación en tiempo real.

[![CI - Lint & Test](https://github.com/SrStamm/API-de-tareas-con-FastAPI/actions/workflows/test.yaml/badge.svg)](https://github.com/SrStamm/API-de-tareas-con-FastAPI/actions/workflows/test.yaml)

- **Estado:** En desarrollo activo / MVP estable
- **Deploy:** VM local (Docker Compose + PostgreSQL)

---

## 🚀 Descripción general

Jerarquía: **grupos → proyectos → tareas → comentarios**. Los usuarios se registran, se unen a grupos, obtienen roles y colaboran en proyectos en tiempo real.

### Autenticación y seguridad

- Registro, login, logout y refresh de tokens con JWT (HS256)
- Access token (15 min por defecto) + refresh token (7 días por defecto)
- El logout revoca sesiones mediante filas de sesión en la base de datos (lista de permitidos)
- Roles y permisos con alcance por grupo y por proyecto
- Todos los secretos se manejan mediante variables de entorno

### Grupos y proyectos

- Crear, editar y eliminar grupos
- Gestionar miembros del grupo
- Crear y administrar proyectos dentro de grupos

### Tareas y comentarios

- Crear, editar, eliminar y asignar tareas
- Comentarios en tareas asignadas
- Control de estado y fechas de vencimiento

### Tiempo real

- Notificaciones en la aplicación vía WebSockets (tarea asignada, tarea actualizada, mención en un comentario, …)
- Chat por proyecto (WebSocket + Redis pub/sub, canales `user:{id}` y `project:{id}`)
- Notificaciones pendientes persistidas de forma asíncrona con Celery (broker Redis)

---

## 🧱 Arquitectura

Arquitectura modular **en capas** — cada capa tiene una única responsabilidad, lo que mantiene la lógica de negocio aislada y testeable y desacopla la API de la infraestructura:

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

Flujo de notificaciones — los usuarios en línea reciben el push de inmediato; los usuarios fuera de línea obtienen una notificación pendiente almacenada para recuperarla después:

```mermaid
flowchart LR
    Ev["Event (assigned · updated · mention)"] --> Redis[("Redis pub/sub")]
    Redis --> SM["Socket manager"]
    SM -->|"push if online"| Client["WebSocket client"]
    SM -->|"else enqueue"| Celery["Celery worker"]
    Celery -->|"persist pending"| PG[("PostgreSQL")]
```

- **Routers** (`api/v1/routers/`): definición de endpoints HTTP + WebSocket
- **Dependencies** (`dependency/`): inyección de dependencias por endpoint (auth, permisos, sesiones)
- **Services** (`services/`): lógica de negocio
- **Repositories** (`repositories/`): persistencia, SQLModel sobre PostgreSQL
- **Models** (`models/`): modelos de base de datos, esquemas de request/response, excepciones
- **Capa de tiempo real** (`core/socket_manager.py`, `core/event_ws.py`): registro de conexiones + distribución vía Redis pub/sub
- **Tareas en segundo plano**: worker de Celery (`tasks.py`) para notificaciones pendientes; APScheduler (lifespan) ejecuta una tarea de limpieza de sesiones cada 5 h (`core/auto.py`)

---

## 🛠️ Stack tecnológico

| Categoría | Tecnología |
|---|---|
| Lenguaje | Python 3.12 |
| Framework web | FastAPI |
| ORM / validación | SQLModel (Pydantic) |
| Base de datos | PostgreSQL (+ migraciones Alembic) |
| Cache / pub-sub | Redis |
| Tareas asíncronas | Celery (broker Redis) |
| Scheduler | APScheduler |
| Autenticación | JWT (python-jose, HS256) |
| Tests | pytest, pytest-cov |
| CI | GitHub Actions |
| Contenedores | Docker & Docker Compose |

---

## 🚀 Puesta en marcha

### Requisitos previos

- Python 3.12
- PostgreSQL y Redis (o solo Docker + Docker Compose)

### Clonar

```bash
git clone git@github.com:SrStamm/API-de-tareas-con-FastAPI.git
cd API-de-tareas-con-FastAPI
```

### Instalación local

```bash
python -m venv env
source env/bin/activate     # Linux / macOS
env\Scripts\activate        # Windows

# App dependencies
pip install -r requirements.txt

# Test dependencies (optional, needed to run the suite)
pip install -r requirements-test.txt
```

Crea un archivo `.env` (ver [Variables de entorno](#variables-de-entorno)) y luego:

```bash
uvicorn main:app --reload
```

La API estará disponible en `http://localhost:8000`.

### Docker

```bash
docker-compose up --build
```

La API estará disponible en `http://localhost:8000` (PostgreSQL y Redis incluidos en el stack).

---

## 🔐 Variables de entorno

Crea un archivo `.env` en la raíz del proyecto. `SECRET_KEY` y `ALGORITHM` son **obligatorias** — la aplicación falla al iniciar sin ellas. Si `DATABASE_URL` está definida, tiene prioridad sobre los valores individuales de `POSTGRES_*`.

| Variable | Uso | Valor por defecto | Notas |
|---|---|---|---|
| `POSTGRES_USER` | `db/database.py` | — | Obligatoria |
| `POSTGRES_PASSWORD` | `db/database.py` | — | Obligatoria |
| `POSTGRES_DB` | `db/database.py` | — | Obligatoria |
| `POSTGRES_HOST` | `db/database.py` | — | Obligatoria |
| `POSTGRES_PORT` | `db/database.py` | — | Obligatoria |
| `DATABASE_URL` | `db/database.py` | — | URL completa de SQLAlchemy; tiene prioridad sobre `POSTGRES_*` |
| `REDIS_HOST` | `db/database.py` | `localhost` | |
| `REDIS_PORT` | `db/database.py` | `6379` | |
| `REDIS_DB` | `db/database.py` | `0` | |
| `REDIS_PASSWORD` | Cliente Redis | — | Obligatoria en la configuración con Docker |
| `REDIS_URL` | Celery (`tasks.py`) | — | URL del broker |
| `SECRET_KEY` | Auth | — | **Obligatoria — la aplicación falla al iniciar sin ella** |
| `ALGORITHM` | Auth | — | **Obligatoria — p. ej. `HS256`** |
| `ACCESS_TOKEN_DURATION` | `services/auth_services.py` | `15` | Vigencia del access token en **minutos** |
| `REFRESH_TOKEN_DURATION` | `services/auth_services.py` | `7` | Vigencia del refresh token en **días** |

Ejemplo para copiar y pegar (valores ficticios únicamente — genera los tuyos):

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

## 📖 Documentación de la API

Una vez que el servidor esté en ejecución:

- **Swagger UI:** <http://localhost:8000/docs>
- **Redoc:** <http://localhost:8000/redoc>

---

## 🧪 Testing

| Comando | Qué hace |
|---|---|
| `pytest -q --disable-warnings` | Ejecuta la suite completa (requiere Redis en `localhost:6379`) |
| `pytest -vv` | Ejecución en modo verbose |
| `pytest --cov=./api/v1 --cov-report=html` | Cobertura de los routers → `htmlcov/index.html` |
| `pytest --cov=. --cov-report=html` | Cobertura del proyecto completo → `htmlcov/index.html` |
| `src/ci-test.sh` | Entrada de CI — termina con error si un test falla |

Notas:

- Los tests se ejecutan sobre **SQLite** (`test/conftest.py`) con **Redis en `localhost:6379`**.
- `src/test.sh` inicia Redis por ti (`docker start redis-stack`) antes de ejecutar pytest.
- Los requisitos están separados: `requirements.txt` (app) vs `requirements-test.txt` (pytest, pytest-cov, …).

**CI:** GitHub Actions (`.github/workflows/test.yaml`) se ejecuta en cada push / PR a `main`: pytest sobre `./test/test_routers`, más una pasada de flake8 no bloqueante.

---

## 🖥️ Demo

- **Frontend:** <https://front-task-api-vanilla.vercel.app/dashboard/tasks>
- **Usuario:** `test`
- **Contraseña:** `test123`

> Estas credenciales son solo para el **frontend público de demostración**. El frontend es un cliente de demostración; el enfoque principal de este proyecto es el diseño y la arquitectura del backend.

### Capturas de pantalla

<!-- TODO: add screenshot — tasks dashboard → save as docs/images/dashboard.png -->
<!-- TODO: add screenshot — task detail with comments → save as docs/images/task-detail.png -->
<!-- TODO: add screenshot — real-time project chat → save as docs/images/chat.png -->
<!-- TODO: add screenshot — Swagger UI → save as docs/images/swagger.png -->

<!-- After recording, embed them here, e.g.:
![Tasks dashboard](docs/images/dashboard.png)
Store image files under docs/images/.
-->

---

## ⚠️ Limitaciones conocidas

Lista honesta de lo que *aún* no está implementado — cada punto indica por qué importa:

1. **Canales de notificación** — la entrega en tiempo real es solo WebSocket + dentro de la aplicación; no hay email ni push móvil. No se han implementado el restablecimiento de contraseña ni la verificación de email.
2. **Despliegue de instancia única** — la demo corre en una sola VM local; el escalado horizontal y el fan-out de WebSocket entre múltiples instancias no se han probado bajo carga.
3. **Deriva entre tests y base de datos** — la suite automatizada se ejecuta sobre SQLite mientras que dev/staging usan PostgreSQL; las consultas específicas de Postgres no se ejercitan en CI, por lo que persiste un pequeño riesgo de deriva de comportamiento.
4. **Rate limiting desactivado actualmente** — existen límites por endpoint (`core/limiter.py`) pero el middleware está comentado en `main.py`; debe reactivarse y corregirse la respuesta de "límite excedido" a HTTP 429 antes de exponer el API públicamente.
5. **Observabilidad** — existe logging estructurado (structlog), pero todavía no hay endpoint `/health`, métricas ni tracing.
6. **Cobertura reportada pero sin umbral** — CI no exige un porcentaje mínimo de cobertura y las rutas de integración de WebSocket tienen cobertura ligera (tests unitarios con mocks, sin un test end-to-end de pub/sub).

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT ([referencia OSI](https://opensource.org/licenses/MIT)).
