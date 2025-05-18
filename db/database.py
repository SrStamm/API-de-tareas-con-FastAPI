from sqlmodel import SQLModel, create_engine, Session, select, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import os
from models.db_models import Group, Project, User, Task

load_dotenv()

user = os.environ.get('POSTGRES_USER')
db_name = os.environ.get('POSTGRES_DB')
password = os.environ.get('POSTGRES_PASSWORD')

url = f'postgresql+psycopg2://{user}:{password}@localhost:5432/{db_name}'

engine = create_engine(url) # echo=True, pool_pre_ping=True

# Asincrono
async_engine = create_async_engine(f'postgresql+asyncpg://{user}:{password}@localhost:5432/{db_name}') 

"""def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print(f'Conectado a PostgreSQL: {result.fetchone()}')
    except Exception as e:
        raise Exception(f"Error al conectar a la base de datos: {e}, {e.args}")"""

async def create_db_and_tables():
    async with async_engine.connect() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)  # Ejecuta creación síncrona en contexto asíncrono
        result = await connection.execute(text("SELECT 1"))
        print(f'Conectado a PostgreSQL: {result.fetchone()}')

def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

async def get_async_session():
    async with AsyncSession(async_engine) as session:
        try:
            yield session
        finally:
            await session.close()

import redis.asyncio as redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)