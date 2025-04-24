import pytest
from conftest import auth_headers, client

def test_get_user_me(client, auth_headers):
    response = client.get('/user/me', headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {'user_id':1, 'username': 'mirko'}

@pytest.mark.parametrize(
        'username, password, email, status, respuesta', [
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
def auth_headers2(client):
    response = client.post("/login", data={"username":"moure_dev", "password":"0000"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_update_user(client, auth_headers2):
    response = client.patch('/user/me', headers=auth_headers2, json={'username':'SrStamm', 'email':'srstamm@gmail.com', 'password':'cambiado'})
    assert response.status_code == 200
    assert response.json() == {'detail':'Se ha actualizado el usuario'}

def test_delete_user(client, auth_headers):
    response = client.delete('/user/me', headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {'detail':'Se ha eliminado el usuario'}