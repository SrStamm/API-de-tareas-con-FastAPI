from sqlmodel import SQLModel, create_engine, Session, select, or_
from sqlalchemy import text, func
from sqlalchemy.orm import selectinload, joinedload, sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import redis.asyncio as redis
from dotenv import load_dotenv
import os
from models import db_models
from urllib.parse import urlparse
from core.logger import logger

load_dotenv()

user = os.environ.get("POSTGRES_USER")
db_name = os.environ.get("POSTGRES_DB")
password = os.environ.get("POSTGRES_PASSWORD")
db_host = os.environ.get("POSTGRES_HOST")
db_port = os.environ.get("POSTGRES_PORT")

# url = f'postgresql+psycopg2://{user}:{password}@localhost:5432/{db_name}'

DATABASE_URL = os.environ.get("DATABASE_URL")
print("DEBUG DATABASE_URL:", DATABASE_URL)

engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print(f"Conectado a PostgreSQL: {result.fetchone()}")
    except Exception as e:
        raise Exception(f"Error al conectar a la base de datos: {e}, {e.args}")


SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
sessionlocal = Session(engine)


def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


# Usar para Docker
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_db = int(os.getenv("REDIS_DB", "0"))

redis_url = os.getenv("REDIS_URL")

if redis_url:
    parsed = urlparse(redis_url)

    redis_host = parsed.hostname
    redis_port = parsed.port
    # redis_password = parsed.password
    redis_db = int(parsed.path.replace("/", "") or 0)

    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        # password=redis_password,
        db=redis_db,
    )
else:
    # fallback local para desarrollo
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
    )
