# pytest -q --disable-warnings
# pytest -vv --disable-warnings
# pytest --cov=./routers --cov-report=html
# xdg-open htmlcov/index.html

import sys, os, pytest, pytest_asyncio, errno
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from main import app
from sqlmodel import SQLModel, create_engine, Session
from db.database import get_session, select
from models import db_models
from api.v1.routers.auth import encrypt_password
from core.logger import logger
import asyncio

import redis.asyncio as redis

from httpx import AsyncClient, ASGITransport

# Crea la BD, cierra las conexiones y elimina la BD
engine = create_engine("sqlite:///./test/test.db")

PASSWORD='0000'

@pytest.fixture(scope="module")
def test_db():
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()
    try:
        os.remove("./test/test.db")
        print("Base de datos test.db eliminada")
    except OSError as e:
        if e.errno != errno.ENOENT:
            print(f"Error al eliminar test.db: {e}")
            raise

@pytest.fixture(scope="session")
def redis_host():
    return os.getenv("REDIS_HOST", "localhost")

# Fixture para tests asíncronos
@pytest_asyncio.fixture(scope="function")
async def async_redis_client():
    client = await redis.Redis(host='localhost', port=6379, db=0)
    yield client

    await client.flushdb()
    await client.close()

# Actualiza tus fixtures que dependen de Redis
@pytest.fixture
def test_session(test_db):  # Usa la versión síncrona
    session = Session(test_db)
    try:
        yield session
    finally:
        session.close()

# Asegúrate de que tu fixture clean_redis use el redis_client inyectado
@pytest_asyncio.fixture(scope="function")
async def clean_redis(async_redis_client):  # Cambia de redis_client a async_redis_client
    yield
    try:
        await async_redis_client.flushdb()
        print("Redis flushed successfully during teardown.")
    except redis.ConnectionError as e:
        print(f"ADVERTENCIA: Error al limpiar Redis en teardown: {e}")
    except Exception as e:
        print(f"ADVERTENCIA: Error inesperado al limpiar Redis en teardown: {e}")

@pytest_asyncio.fixture(scope="function")
async def async_client(test_session, async_redis_client):
    app.dependency_overrides[get_session] = lambda: test_session
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture
def client(test_session):
    app.dependency_overrides[get_session] = lambda: test_session
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(test_session):
    user = db_models.User(username='mirko', email='mirko@dev.com', password=encrypt_password(PASSWORD))
    test_session.add(user)
    test_session.commit()

@pytest.fixture
def test_user2(test_session):
    user = db_models.User(username='moure', email='moure@dev.com', password=encrypt_password(PASSWORD))
    test_session.add(user)
    test_session.commit()

@pytest.fixture
def test_user3(test_session):
    user = db_models.User(username='dalto', email='dalto@dev.com', password=encrypt_password(PASSWORD))
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(client, test_user):
    response = client.post("/login", data={"username": 'mirko', "password": PASSWORD})
    assert response.status_code == 200, f"Error en login: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_tokens(client, test_user):
    response = client.post("/login", data={"username": 'mirko', "password": PASSWORD})
    assert response.status_code == 200, f"Error en login: {response.json()}"
    return response.json()

@pytest.fixture
def auth_headers2(client, test_user2):
    response = client.post("/login", data={"username":'moure', "password":PASSWORD})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture(scope="function")
async def test_create_group_init(async_client, auth_headers, test_user2):
    loop = asyncio.get_running_loop()
    logger.debug(f"Event loop running: {loop.is_running()}, closed: {loop.is_closed()}")
    response = await async_client.post('/group', headers=auth_headers, json={'name': 'probando'})
    logger.debug(f"After POST, loop closed: {loop.is_closed()}")
    assert response.status_code == 200
    await async_client.post('/group/1/2', headers=auth_headers)


@pytest_asyncio.fixture
async def test_create_project_init(async_client, auth_headers, test_user2, test_user3, test_create_group_init, test_session):
    print("Ejecutando test_create_project_init")
    
    # Crear proyecto
    response = await async_client.post('/project/1', headers=auth_headers, json={'title': 'creando un proyecto'})
    assert response.status_code == 200, f"Error al crear proyecto: {response.json()}"
    print("Proyecto 1 creado")

    # Verificar si el usuario 1 ya está asociado antes de intentar asociarlo
    check_response = await async_client.get('/project/1/1/users', headers=auth_headers)
    if check_response.status_code == 200:
        print("Usuario 1 ya está asociado al proyecto 1")
    else:
        # Asociar user1 solo si no está ya asociado
        response = await async_client.post('/project/1/1/1', headers=auth_headers)
        assert response.status_code == 200, f"Error al asociar user1: {response.json()}"

    await async_client.post('/group/1/2', headers=auth_headers)

@pytest.fixture
async def test_create_project_init_for_tasks(async_client, auth_headers, test_user2, test_user3, test_create_group_init, test_session):
    # Crear proyecto
    response = await async_client.post('/project/1', headers=auth_headers, json={'title': 'creando un proyecto'})
    assert response.status_code == 200, f"Error al crear proyecto: {response.json()}"

    check_response = await async_client.get('/project/1/1/users', headers=auth_headers)
    if check_response.status_code == 200:
        print("Usuario 1 ya está asociado al proyecto 1")
    else:
        # Asociar user1 solo si no está ya asociado
        response = await async_client.post('/project/1/1/1', headers=auth_headers)
        assert response.status_code == 200, f"Error al asociar user1: {response.json()}"
    
    await async_client.post('/project/1/1/2', headers=auth_headers)