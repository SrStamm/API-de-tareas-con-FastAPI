# pytest -q --disable-warnings
# pytest -vv --disable-warnings
# pytest --cov=./routers --cov-report=html
# xdg-open htmlcov/index.html

import sys, os, pytest, pytest_asyncio, errno
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from main import app
from sqlmodel import SQLModel, create_engine, Session
from db.database import get_async_session, AsyncSession, get_session, select, redis_client
from models import db_models
from routers.auth import encrypt_password

from httpx import AsyncClient, ASGITransport

# Crea la BD, cierra las conexiones y elimina la BD
engine = create_engine("sqlite+aiosqlite:///./test/test.db", echo=False)

PASSWORD='0000'

@pytest_asyncio.fixture(scope="module")
async def test_db():
    async with AsyncSession(engine) as session:
        async with session.begin():
            SQLModel.metadata.create_all(engine)
    yield engine
    async with AsyncSession(engine) as session:
        async with session.begin():
            SQLModel.metadata.drop_all(engine)
            os.remove("./test/test.db")
            print("Base de datos test.db eliminada")
    await engine.dispose()

@pytest_asyncio.fixture
async def test_session(test_db):
    async with AsyncSession(test_db) as session:
        try:
            yield session
        finally:
            await session.close()

@pytest_asyncio.fixture
async def async_client(test_session):
    async def override_get_async_session():
        yield test_session

    app.dependency_overrides[get_async_session] = override_get_async_session
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="function")
async def clean_redis():
    yield
    async for key in redis_client.scan_iter('groups:*:limit:*:offset:*'):
        await redis_client.delete(key)
    async for key in redis_client.scan_iter('projects:*:limit:*:offset:*'):
        await redis_client.delete(key)
    async for key in redis_client.scan_iter('users:limit:*:offset:*'):
        await redis_client.delete(key)
    async for key in redis_client.scan_iter('task:*:limit:*:offset:*'):
        await redis_client.delete(key)

@pytest_asyncio.fixture(scope="module", autouse=True)
async def manage_redis():
    yield
    # Cierra la conexión de Redis solo al final del módulo
    try:
        await redis_client.aclose()
    except RuntimeError:
        pass

@pytest_asyncio.fixture
async def test_user(test_session):
    user = db_models.User(username='mirko', email='mirko@dev.com', password=encrypt_password(PASSWORD))
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def test_user2(test_session):
    user = db_models.User(username='moure', email='moure@dev.com', password=encrypt_password(PASSWORD))
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def test_user3(test_session):
    user = db_models.User(username='dalto', email='dalto@dev.com', password=encrypt_password(PASSWORD))
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def auth_headers(async_client, test_user):
    response = await async_client.post("/login", data={"username": test_user.username, "password": PASSWORD})
    assert response.status_code == 200, f"Error en login: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def auth_headers2(async_client, test_user2):
    response = await async_client.post("/login", data={"username": test_user2.username, "password": PASSWORD})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def test_create_group_init(async_client, auth_headers, test_user2):
    response = await async_client.post('/group', headers=auth_headers, json={'name': 'probando'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    response = await async_client.post('/group/1/2', headers=auth_headers)
    assert response.status_code == 200
    return

@pytest_asyncio.fixture
async def test_create_project_init(async_client, auth_headers, test_user2, test_user3, test_create_group_init, test_session):
    print("Ejecutando test_create_project_init")
    
    response = await async_client.post('/project/1', headers=auth_headers, json={'title': 'creando un proyecto'})
    assert response.status_code == 200, f"Error al crear proyecto: {response.json()}"
    print("Proyecto 1 creado")

    response = await async_client.get('/project/1/1/users', headers=auth_headers)
    if response.status_code != 200:
        response = await async_client.post('/project/1/1/1', headers=auth_headers)
        assert response.status_code == 200, f"Error al asociar user1: {response.json()}"

    await async_client.post('/group/1/2', headers=auth_headers)

@pytest_asyncio.fixture
async def test_create_project_init_for_tasks(async_client, auth_headers, test_user2, test_user3, test_create_group_init, test_session):
    print("Ejecutando test_create_project_init")
    
    response = await async_client.post('/project/1', headers=auth_headers, json={'title': 'creando un proyecto'})
    assert response.status_code == 200, f"Error al crear proyecto: {response.json()}"
    print("Proyecto 1 creado")

    response = await async_client.get('/project/1/1/users', headers=auth_headers)
    if response.status_code != 200:
        response = await async_client.post('/project/1/1/1', headers=auth_headers)
        assert response.status_code == 200, f"Error al asociar user1: {response.json()}"
    
    await async_client.post('/project/1/1/2', headers=auth_headers)