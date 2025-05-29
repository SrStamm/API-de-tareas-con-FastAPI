from sqlmodel import SQLModel, create_engine, Session, select, or_
from sqlalchemy import text
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import os
from models.db_models import Group, Project, User, Task
import redis.asyncio as redis
import redis.exceptions as redis_basic

load_dotenv()

user = os.environ.get('POSTGRES_USER')
db_name = os.environ.get('POSTGRES_DB')
password = os.environ.get('POSTGRES_PASSWORD')

# url = f'postgresql+psycopg2://{user}:{password}@localhost:5432/{db_name}'

url = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://postgres:amaterasu@postgres:5432/database')
engine = create_engine(url) # echo=True, pool_pre_ping=True 

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print(f'Conectado a PostgreSQL: {result.fetchone()}')
    except Exception as e:
        raise Exception(f"Error al conectar a la base de datos: {e}, {e.args}")

def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

# Usar para Docker
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_db = int(os.getenv("REDIS_DB", 0))

# En CI, usa una conexión síncrona para simplificar
if os.getenv("CI") == "true":
    import redis as redis_sync
    redis_client = redis_sync.Redis(host=redis_host, port=redis_port, db=redis_db)
else:
    import redis.asyncio as redis
    redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)