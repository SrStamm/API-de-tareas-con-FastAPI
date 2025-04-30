from fastapi import FastAPI
from routers import group, project, task, user, auth, ws
from db.database import create_db_and_tables
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield
    print({'Atencion':'La base de datos se encuentra desactivada'})

app = FastAPI(lifespan=lifespan)

app.include_router(group.router)
app.include_router(project.router)
app.include_router(task.router)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(ws.router)

@app.get('/')
def root():
    return {'detail':'Bienvenido a esta API!'}