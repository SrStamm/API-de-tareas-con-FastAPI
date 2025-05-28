# pytest -q --disable-warnings
# pytest -vv --disable-warnings
# pytest --cov=./routers --cov-report=html
# xdg-open htmlcov/index.html

import sys, os, pytest, pytest_asyncio, errno
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from main import app
from sqlmodel import SQLModel, create_engine, Session
from db.database import get_session, select, redis
from models import db_models
from api.v1.routers.auth import encrypt_password

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

@pytest.fixture
def test_session(test_db):
    session = Session(test_db)
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(test_session):
    app.dependency_overrides[get_session] = lambda: test_session
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def async_client(test_session):
    app.dependency_overrides[get_session] = lambda: test_session
    
    transport = ASGITransport(app=app) # Se usa esto para transportar la app, ya que no sabe como manejar FastAPI

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()

# Asegúrate de tener un fixture 'redis_client' que configure la conexión a Redis.
# Si tu redis_client ya existe, este fixture lo usará.
# Si no lo tienes, aquí tienes un ejemplo de cómo podría verse:
@pytest.fixture(scope="function") # 'function' para asegurar limpieza por cada test
async def redis_client():
    # Asegúrate de que el host y puerto coincidan con tu configuración de GitHub Actions services
    client = redis.Redis(host='redis', port=6379, db=0)
    try:
        # Intenta un ping para verificar la conexión al inicio del test
        await client.ping()
        print("Conexión a Redis establecida y verificada.")
    except ConnectionError as e:
        print(f"ERROR: No se pudo conectar a Redis al inicio del test: {e}")
        # Considera levantar una excepción aquí si la conexión a Redis es crítica
        raise
    yield client
    # El teardown se ejecuta después del test/función
    try:
        await client.close() # Cierra la conexión
        print("Conexión a Redis cerrada.")
    except Exception as e:
        # Manejo básico de errores si el cierre falla (poco probable)
        print(f"ADVERTENCIA: Error al cerrar la conexión de Redis: {e}")

@pytest.fixture(scope="function") # Mantener 'function' para aislamiento de tests
async def clean_redis(redis_client): # Este fixture ahora depende de redis_client
    # El código dentro de 'yield' se ejecuta ANTES de cada test que lo use.
    # Aquí puedes hacer alguna configuración si es necesario.
    yield

    # El código después de 'yield' se ejecuta como TEARDOWN después de cada test.
    try:
        # Para CI/CD, la limpieza completa es lo más fiable.
        await redis_client.flushdb()
        print("Redis flushed successfully during teardown.")
    except ConnectionError as e:
        # Capturamos específicamente el error de conexión de Redis
        print(f"ADVERTENCIA: Error al limpiar Redis en teardown (probablemente cierre de red): {e}")
    except Exception as e:
        # Captura cualquier otra excepción inesperada
        print(f"ADVERTENCIA: Error inesperado al limpiar Redis en teardown: {e}")



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

@pytest_asyncio.fixture
async def test_create_group_init(async_client, auth_headers, test_user2):
    response = await async_client.post('/group', headers=auth_headers, json={'name':'probando'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    await async_client.post('/group/1/2', headers=auth_headers)
    return

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