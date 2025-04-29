# pytest -q --disable-warnings
# pytest -vv --disable-warnings
# pytest --cov=./routers --cov-report=html
# xdg-open htmlcov/index.html

import sys, os, pytest, errno
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from main import app
from sqlmodel import SQLModel, create_engine, Session
from db.database import get_session, select
from models import db_models
from routers.auth import encrypt_password

# Crea la BD, cierra las conexiones y elimina la BD
engine = create_engine("sqlite:///./test/test.db")

@pytest.fixture(scope="module")
def test_db():
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()
    try:
        os.remove("./test/test.db")
    except OSError as e:
        if e.errno != errno.ENOENT:
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

PASSWORD='0000'

@pytest.fixture
def test_user(test_session):
    user = db_models.User(username='mirko', email='mirko@dev.com', password=encrypt_password(PASSWORD))
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user

@pytest.fixture
def test_user2(test_session):
    user = db_models.User(username='moure', email='moure@dev.com', password=encrypt_password(PASSWORD))
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(client, test_user):
    response = client.post("/login", data={"username": test_user.username, "password": PASSWORD})
    assert response.status_code == 200, f"Error en login: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers2(client, test_user2):
    response = client.post("/login", data={"username":test_user2.username, "password":PASSWORD})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_create_group_init(client, auth_headers, test_user2):
    response = client.post('/group', headers=auth_headers, json={'name':'probando'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    client.post('/group/1/2', headers=auth_headers)
    return

@pytest.fixture
def test_create_project_init(client, auth_headers, test_user2, test_create_group_init, test_session):
    print("Ejecutando test_create_project_init")
    hola = test_create_group_init
    print(hola)

    # Crear proyecto
    response = client.post(f'/project/1', headers=auth_headers, json={'title':'creando un proyecto'})
    assert response.status_code == 200, f"Error al crear proyecto: {response.json()}"
    print("Proyecto 1 creado")

    # Asociar user2 (test_user2, user_id=2) al proyecto
    response = client.post('/project/1/1/2', headers=auth_headers)
    assert response.status_code == 200, f"Error al asociar user2: {response.json()}"
    print("Usuario 2 asociado al proyecto 1")

    # Verificar proyecto y asociaciones en la base de datos
    project = test_session.get(db_models.Project, 1)
    assert project is not None, "Proyecto 1 no encontrado en la base de datos"
    stmt = select(db_models.project_user).where(
        db_models.project_user.user_id == 1,
        db_models.project_user.project_id == 1
    )
    project_user1 = test_session.exec(stmt).first()
    assert project_user1 is not None, "Usuario 1 no está asociado al proyecto 1"
    stmt = select(db_models.project_user).where(
        db_models.project_user.user_id == 2,
        db_models.project_user.project_id == 1
    )
    project_user2 = test_session.exec(stmt).first()
    assert project_user2 is not None, "Usuario 2 no está asociado al proyecto 1"
    print("Verificado: Usuarios 1 y 2 están asociados al proyecto 1")

    # Crear una tarea
    response = client.post(
        '/task/1',
        headers=auth_headers,
        json={
            'description': 'Tarea inicial',
            'date_exp': '2025-10-10',
            'user_ids': [1]
        }
    )
    assert response.status_code == 200, f"Error al crear tarea: {response.json()}"
    print("Tarea creada")

    return

def test_root(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {'detail':'Bienvenido a esta API!'}