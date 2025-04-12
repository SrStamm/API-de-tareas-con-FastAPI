from fastapi import FastAPI
from routers import group


app = FastAPI()

app.include_router(group.router)

@app.get('/')
def root():
    return {f'Bienvenido a esta API! Aqui podras crear un grupo, crear proyectos y asignar tareas a los miembros del grupo para completar un proyecto especifico!'}