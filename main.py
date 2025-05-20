from fastapi import FastAPI, Request
from api.v1.routers import group, project, task, user, auth, ws, comment
from db.database import create_db_and_tables
from contextlib import asynccontextmanager
from core.logger import logger
from core.limiter import limiter, _rate_limit_exceeded_handler, RateLimitExceeded
from time import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield
    logger.info({'Atencion':'La base de datos se encuentra desactivada'})
    logger.info({'Atencion':'El servidor no se encuentra disponible'})
    

app = FastAPI(lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(group.router)
app.include_router(project.router)
app.include_router(task.router)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(ws.router)
app.include_router(comment.router)

@app.get('/')
def root():
    return {'detail':'Bienvenido a esta API!'}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time()
    response = await call_next(request)
    duration = time() - start_time
    user = request.state.user if hasattr(request.state, 'user') else 'anonymous'
    logger.info(
        f"method={request.method} path={request.url.path} user={user} duration={duration:.3f}s status={response.status_code}"
    )
    return response