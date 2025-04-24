import pytest
from conftest import auth_headers, client, auth_headers2, test_create_group_init, test_user2
from models import db_models

def test_create_group(client, auth_headers, test_user2):
    response = client.post('/group', headers=auth_headers, json={'name':'probando'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    response = client.post('/group', headers=auth_headers, json={'name':'test'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    hola = test_user2

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
    assert response.json() == {'detail': 'User whit user_id 2 is Not Authorized'}

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
