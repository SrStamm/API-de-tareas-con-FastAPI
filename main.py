from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from api.v1.routers import group, project, task, user, auth, ws, comment
from db.database import create_db_and_tables
from core.logger import logger, register_exceptions_handlers
from core.limiter import limiter, _rate_limit_exceeded_handler, RateLimitExceeded
from core.auto import run_scheduler_job
from db.database import redis_client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
from apscheduler.triggers.interval import IntervalTrigger
from time import time

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()

    scheduler.add_job(
        run_scheduler_job, trigger=IntervalTrigger(hours=5), max_instances=1
    )
    scheduler.start()

    yield

    scheduler.shutdown()
    logger.info({"Atencion": "La base de datos se encuentra desactivada"})
    logger.info({"Atencion": "El servidor no se encuentra disponible"})


app = FastAPI(lifespan=lifespan)

register_exceptions_handlers(app)

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8080",
    "*",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(group.router)
app.include_router(project.router)
app.include_router(task.router)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(ws.router)
app.include_router(comment.router)


@app.get("/")
def root():
    return {"detail": "Bienvenido a esta API!"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time()
    response = await call_next(request)
    duration = time() - start_time
    user = request.state.user if hasattr(request.state, "user") else "anonymous"

    # Use request.url.scheme instead of request.scope["scheme"]
    scheme = request.url.scheme or "http"  # Fallback to 'http' if scheme is empty
    if not scheme:
        logger.warning(f"Invalid scheme in request URL: {request.url}")

    logger.info(
        f"method={request.method} path={request.url.path} user={user} duration={duration:.3f}s status={response.status_code}"
    )
    return response


@app.get("/test-redis")
async def test_redis():
    try:
        pong = await redis_client.ping()
        return {"connected": pong}
    except Exception as e:
        return {"error": str(e)}
