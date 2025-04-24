import pytest
from conftest import auth_headers, client, auth_headers2, test_create_group_init, test_user2
from models import db_models

def test_get_projects(client, auth_headers, auth_headers2):
    hola = auth_headers
    hola = auth_headers2

    response = client.get('/project/1')
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    for project in projects:
        assert all(key in project for key in ['project_id', 'group_id', 'tittle', 'description', 'users'])

@pytest.mark.parametrize(
        'group_id, status, detail', [
            (1, 200, 'Se ha creado un nuevo proyecto de forma exitosa'),
            (1, 200, 'Se ha creado un nuevo proyecto de forma exitosa'),
        ]
)
def test_create_project(client, auth_headers, test_create_group_init, group_id, status, detail):
    response = client.post(f'/project/{group_id}', headers=auth_headers, json={'title':'creando un proyecto'})
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_update_project(client, auth_headers):
    response = client.patch('/project/1/1', headers=auth_headers, json={'title':'actualizando un proyecto', 'description':'actualizando...'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha actualizado la informacion del projecto'}

@pytest.mark.parametrize(
        'user_id, status, detail', [
            (2, 200, 'El usuario ha sido agregado al proyecto'),
            (2, 400, 'User whit user_id 2 is in project with project_id 1'),
            (3, 400, 'User whit user_id 3 is in Group with group_id 1'),
            (100, 404, 'User whit user_id 100 not found')
        ]
)
def test_add_user_to_project(client, auth_headers, user_id, status, detail):
    response = client.post(f'/project/1/1/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_get_user_in_project(client, auth_headers):
    response = client.get('/project/1/1/users', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['user_id', 'username', 'permission'])

@pytest.mark.parametrize(
        'project_id, user_id, permission, status, detail', [
            (1, 1, db_models.Project_Permission.ADMIN, 200, 'Se ha cambiado los permisos del usuario en el proyecto'),
            (1, 100000, db_models.Project_Permission.ADMIN, 400, 'User whit user_id 100000 is not in project with project_id 1')
            ]
)
def test_update_user_permission_in_project(client, auth_headers, project_id, user_id, permission, status, detail, test_create_group_init):
    response = client.patch(f'/project/1/{project_id}/{user_id}', headers=auth_headers, json={'permission': permission})
    assert response.status_code == status
    assert response.json() == {'detail': detail}

@pytest.mark.parametrize(
        'user_id, status, detail', [
            (2, 200, 'El usuario ha sido eliminado del proyecto'),
            (2, 400, 'User whit user_id 2 is not in project with project_id 1'),
            (3, 400, 'User whit user_id 3 is not in Group with group_id 1')
        ]
)
def test_remove_user_from_project(client, auth_headers, user_id, status, detail, test_create_group_init):
    response = client.delete(f'/project/1/1/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_get_tasks_in_project(client, auth_headers):
    response = client.get('/project/1/2/tasks', headers=auth_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    for task in tasks:
        assert all(key in task for key in ['task_id', 'description','state', 'user_id', 'username'])

def test_failed_delete_project(client, auth_headers2):
    response = client.delete(f'/project/1/1', headers=auth_headers2)
    assert response.status_code == 401
    assert response.json() == {'detail': 'User whit user_id 2 is Not Authorized'}

@pytest.mark.parametrize(
        'project_id, status, detail', [
            (2, 200, 'Se ha eliminado el proyecto')
        ]
)
def test_delete_project(client, auth_headers, project_id, status, detail):
    response = client.delete(f'/project/1/{project_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}
