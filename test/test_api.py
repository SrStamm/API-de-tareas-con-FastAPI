# pytest -q --disable-warnings
# pytest -vv --disable-warnings
# pytest --cov=./routers --cov-report=html
# xdg-open htmlcov/index.html


import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from main import app
import pytest, os, errno
from sqlmodel import SQLModel, create_engine, Session
from db.database import get_session
from models import db_models

# Crea la BD, cierra las conexiones y elimina la BD
engine = create_engine("sqlite:///./test/test.db")

@pytest.fixture(scope="session")
def test_db():
    # Crear la base de datos de prueba
    SQLModel.metadata.create_all(engine)
    yield engine
    # Cerrar todas las conexiones del engine
    engine.dispose()
    # Eliminar la base de datos después de las pruebas
    try:
        os.remove("./test/test.db")
    except OSError as e:
        if e.errno != errno.ENOENT:  # Ignorar si el archivo no existe
            raise

# Crea la session
@pytest.fixture
def test_session(test_db):
    session = Session(test_db)
    try:
        yield session
    finally:
        session.close()

# Modifica la API para hacer consultas en BD de Testing
@pytest.fixture
def client(test_session):
    app.dependency_overrides[get_session] = lambda: test_session
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_root(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {'detail':'Bienvenido a esta API!'}

@pytest.mark.parametrize(
        'username, password, email, status, respuesta', [
            ('mirko', '0000', 'mirko@dev.com', 200, 'Se ha creado un nuevo usuario con exito'),
            ('mirko', '0000', 'mirko@dev.com', 406, 'Ya existe un usuario con este Username'),
            ('mirko_dev', '0000', 'mirko@dev.com', 406, 'Ya existe un usuario con este Email'),
            ('mirko_dev', '0000', 'mirko@gmail.com', 200, 'Se ha creado un nuevo usuario con exito'),
            ('moure_dev', '0000', 'moure@gmail.com', 200, 'Se ha creado un nuevo usuario con exito')
        ])
def test_create_user(client, username, password, email, status, respuesta):
    response = client.post('/user', json={"username":username, "email":email, "password":password})
    assert response.status_code == status
    assert response.json() == {'detail':respuesta}

def test_get_users(client):
    response = client.get('user')
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    for user in users:
        assert all(key in user for key in ['user_id', 'username'])

@pytest.fixture
def auth_headers(client):
    login_data = {"username":"mirko", "password":"0000"}  # Credenciales
    response = client.post("/login", data=login_data)  # OAuth usa 'data'
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers2(client):
    login_data = {"username":"mirko_dev", "password":"0000"}
    response = client.post("/login", data=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.parametrize (
        'username, password, status, detail', [
            ('a', '0000', 404, 'Usuario no encontrado o no existe'),
            ('mirko', '5555', 400, 'Contraseña incorrecta')
        ]
)
def test_failed_login(client, username, password, status, detail):
    login_data = {"username":username, "password":password}  # Credenciales
    response = client.post("/login", data=login_data)  # OAuth usa 'data'
    assert response.status_code == status
    assert response.json() == {'detail':detail}
    
def test_get_user_me(client, auth_headers):
    response = client.get('/user/me', headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {'user_id':1, 'username': 'mirko'}

def test_create_group(client, auth_headers):
    response = client.post('/group', headers=auth_headers, json={'name':'probando'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    response = client.post('/group', headers=auth_headers, json={'name':'test'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

def test_get_groups(client, auth_headers):
    response = client.get('/group', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['group_id', 'name', 'description', 'users'])

def test_get_groups_in_user(client, auth_headers):
    response = client.get('/group/me', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['group_id', 'name', 'users'])

@pytest.mark.parametrize(
        'group_id, user_id, status, respuesta', [
            (1, 2, 200,  'El usuario ha sido agregado al grupo'),
            (1, 100000, 404, 'User whit user_id 100000 not found'),
            (1, 2, 400, 'User whit user_id 2 is in Group with group_id 1'),
            (2, 2, 200, 'El usuario ha sido agregado al grupo')
        ]
)
def test_append_user_group(client, auth_headers, group_id, user_id, status, respuesta):
    response = client.post(f'/group/{group_id}/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail':respuesta}

def test_get_user_in_group(client, auth_headers):
    response = client.get('/group/1/users', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['user_id', 'username', 'role'])

def test_update_group(client, auth_headers):
    response = client.patch('/group/1', headers=auth_headers, json={'description':'probando otra vez', 'name':'probando el update'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha actualizado la informacion del grupo'}

def test_failed_update_group(client, auth_headers2):
    response = client.patch('/group/1', headers=auth_headers2, json={'description':'probando otra vez'})
    assert response.status_code == 401
    assert response.json() == {'detail': 'No estas autorizado'}

@pytest.mark.parametrize(
        'user_id, role, status, respuesta', [
            (2, db_models.Group_Role.ADMIN, 200, 'Se ha cambiado los permisos del usuario en el grupo'),
            (2, db_models.Group_Role.MEMBER, 200, 'Se ha cambiado los permisos del usuario en el grupo'),
            (3, db_models.Group_Role.ADMIN, 404, 'No se encontro el usuario')
        ]
)
def test_update_user_group(client, auth_headers, user_id, role, status, respuesta):
    response = client.patch(f'/group/1/{user_id}', headers=auth_headers, json={'role':role})
    assert response.status_code == status
    assert response.json() == {'detail':respuesta}

@pytest.mark.parametrize(
        'group_id, user_id, status, respuesta', [
            (1, 2, 200, 'El usuario ha sido eliminado al grupo'),
            (1, 2, 404, 'User whit user_id 2 not found')
        ]
)
def test_delete_user_group(client, auth_headers, group_id, user_id, status, respuesta):
    response = client.delete(f'/group/{group_id}/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': respuesta}

@pytest.mark.parametrize(
        'group_id, status, respuesta', [
            (1, 200, 'Se ha eliminado el grupo'),
            (100000, 404, 'Group whit group_id 100000 not found')
        ]
)
def test_delete_group(client, auth_headers, group_id, status, respuesta):
    response = client.delete(f'/group/{group_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': respuesta}

def test_get_projects(client, auth_headers):
    response = client.get('/project/1')
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    for project in projects:
        assert all(key in project for key in ['project_id', 'group_id', 'tittle', 'description', 'users'])

@pytest.mark.parametrize(
        'group_id, status, detail', [
            (2, 200, 'Se ha creado un nuevo proyecto de forma exitosa'),
            (2, 200, 'Se ha creado un nuevo proyecto de forma exitosa'),
        ]
)
def test_create_project(client, auth_headers, group_id, status, detail):
    response = client.post(f'/project/{group_id}', headers=auth_headers, json={'title':'creando un proyecto'})
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_update_project(client, auth_headers):
    response = client.patch('/project/2/1', headers=auth_headers, json={'title':'actualizando un proyecto', 'description':'actualizando...'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha actualizado la informacion del projecto'}

@pytest.mark.parametrize(
        'user_id, status, detail', [
            (2, 200, 'El usuario ha sido agregado al proyecto'),
            (2, 400, 'User whit user_id 2 is in project with project_id 1'),
            (3, 400, 'User whit user_id 3 is in Group with group_id 2'),
            (100, 404, 'User whit user_id 100 not found')
        ]
)
def test_add_user_to_project(client, auth_headers, user_id, status, detail):
    response = client.post(f'/project/2/1/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_get_user_in_project(client, auth_headers):
    response = client.get('/project/2/1/users', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['user_id', 'username', 'permission'])

@pytest.mark.parametrize(
        'project_id, datos, status, detail', [
            (1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[1]}, 200, 'Se ha creado una nueva tarea y asignado los usuarios con exito'),
            (1000000, {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[1, 2]}, 404, 'No se encontro el proyecto destinado'),
            (1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[3]}, 404, 'No se encontro el usuario en el proyecto'),
            (1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[1000]}, 404, 'No se encontro el usuario'),
        ]
)
def test_create_task(client, auth_headers, project_id, datos, status, detail):
    response = client.post(f'/task/{project_id}', headers=auth_headers, json= datos)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_failed_create_task(client, auth_headers2):
    response = client.post('/task/1', headers=auth_headers2, json= {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[1]})
    assert response.status_code == 403
    assert response.json() == {'detail': 'No tienes permisos'}

def test_get_task(client, auth_headers):
    response = client.get('/task', headers=auth_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    for task in tasks:
        assert all(key in task for key in ['task_id', 'description', 'date_exp', 'state', 'project_id'])

def test_get_task_in_project(client, auth_headers):
    response = client.get('/task/1', headers=auth_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    for task in tasks:
        assert all(key in task for key in ['task_id', 'description', 'date_exp', 'state', 'project_id'])

@pytest.mark.parametrize(
        'project_id, task_id, datos, status, detail', [
            (1, 1, {'description':'probando el testing... otra vez', 'date_exp':'2025-12-12', 'state':db_models.State.EN_PROCESO, 'exclude_user_ids': [1], 'append_user_ids': [2]}, 200, 'Se ha actualizado la tarea'),
            (1000, 1, {'description':'probando el testing', 'date_exp':'2025-10-10'}, 404, 'No se encontro el proyecto'),
            (1, 1000, {'description':'probando el testing', 'date_exp':'2025-10-10'}, 404, 'No se encontro la tarea'),
            (1, 1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'exclude_user_ids':[100000]}, 400, 'El usuario de id 100000 no esta asignado a esta tarea'),
            (1, 1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'append_user_ids':[2]}, 400, 'El usuario de id 2 esta asignado a esta tarea'),
            (1, 1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'append_user_ids':[100000]}, 404, 'No se encontro el usuario'),
        ]
)
def test_update_task(client, auth_headers, project_id, task_id, datos, status, detail):
    response = client.patch(f'/task/{project_id}/{task_id}', headers=auth_headers, json= datos)
    assert response.status_code == status
    assert response.json() == {'detail':detail}

@pytest.mark.parametrize(
        'task_id, status, detail', [
            (1, 200, 'Se ha eliminado la tarea'),
            (1, 404, 'No se encontro la tarea en el proyecto')
        ]
)
def test_delete_task(client, auth_headers, task_id, status, detail):
    response = client.delete(f'/task/1/{task_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_failed_delete_task(client, auth_headers2):
    response = client.delete(f'/task/1/2', headers=auth_headers2)
    assert response.status_code == 403
    assert response.json() == {'detail': 'No tienes la autorizacion para realizar esta accion'}

def test_get_users_for_task(client, auth_headers):
    response = client.get('/task/1/users', headers=auth_headers)
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    for user in users:
        assert all(key in user for key in ['user_id', 'username'])

@pytest.mark.parametrize(
        'project_id, user_id, permission, status, detail', [
            (1, 2, db_models.Project_Permission.ADMIN, 200, 'Se ha cambiado los permisos del usuario en el proyecto'),
            (1, 100000, db_models.Project_Permission.ADMIN, 400, 'User whit user_id 100000 is not in project with project_id 1')
            ]
)
def test_update_user_permission_in_project(client, auth_headers, project_id, user_id, permission, status, detail):
    response = client.patch(f'/project/2/{project_id}/{user_id}', headers=auth_headers, json={'permission': permission})
    assert response.status_code == status
    assert response.json() == {'detail': detail}

@pytest.mark.parametrize(
        'user_id, status, detail', [
            (2, 200, 'El usuario ha sido eliminado del proyecto'),
            (2, 400, 'User whit user_id 2 is not in project with project_id 1'),
            (3, 400, 'User whit user_id 3 is not in Group with group_id 2')
        ]
)
def test_remove_user_from_project(client, auth_headers, user_id, status, detail):
    response = client.delete(f'/project/2/1/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

@pytest.mark.parametrize(
        'project_id, status, detail', [
            (2, 200, 'Se ha eliminado el proyecto')
        ]
)
def test_delete_project(client, auth_headers, project_id, status, detail):
    response = client.delete(f'/project/2/{project_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_failed_delete_project(client, auth_headers2):
    response = client.delete(f'/project/2/1', headers=auth_headers2)
    assert response.status_code == 401
    assert response.json() == {'detail': 'User whit user_id 2 is Not Authorized'}

def test_get_tasks_in_project(client, auth_headers):
    response = client.get('/project/1/2/tasks', headers=auth_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    for task in tasks:
        assert all(key in task for key in ['task_id', 'description','state', 'user_id', 'username'])

def test_update_user(client, auth_headers2):
    response = client.patch('/user/me', headers=auth_headers2, json={'username':'SrStamm', 'email':'srstamm@gmail.com', 'password':'cambiado'})
    assert response.status_code == 200
    assert response.json() == {'detail':'Se ha actualizado el usuario'}

def test_delete_user(client, auth_headers):
    response = client.delete('/user/me', headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {'detail':'Se ha eliminado el usuario'}
