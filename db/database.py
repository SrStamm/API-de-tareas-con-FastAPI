from sqlmodel import SQLModel, create_engine, Session, select, or_
from sqlalchemy import text
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import os
from models.db_models import Group, Project, User, Task

load_dotenv()

user = os.environ.get('POSTGRES_USER')
db_name = os.environ.get('POSTGRES_DB')
password = os.environ.get('POSTGRES_PASSWORD')

url = f'postgresql+psycopg2://{user}:{password}@localhost:5432/{db_name}'

engine = create_engine(url, echo=True, pool_pre_ping=True)

def create_db_and_tables():
    print(url)
    print('Intentando crear las tablas')
    SQLModel.metadata.create_all(engine)
    print('Tablas creadas o ya existentes')

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