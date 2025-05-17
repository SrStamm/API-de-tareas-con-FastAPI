import pytest
from conftest import auth_headers, client, async_client, clean_redis
from models import schemas, db_models, exceptions
from routers import user
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Request

def test_get_user_me(client, auth_headers):
    response = client.get('/user/me', headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {'user_id':1, 'username': 'mirko'}

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'username, password, email, status, respuesta', [
            ('mirko', '0000', 'mirko@dev.com', 406, 'Ya existe un usuario con este Username'),
            ('mirko_dev', '0000', 'mirko@dev.com', 406, 'Ya existe un usuario con este Email'),
            ('mirko_dev', '0000', 'mirko@gmail.com', 200, 'Se ha creado un nuevo usuario con exito'),
            ('moure_dev', '0000', 'moure@gmail.com', 200, 'Se ha creado un nuevo usuario con exito')
        ])
async def test_create_user(async_client, username, password, email, status, respuesta):
    response = await async_client.post('/user', json={"username":username, "email":email, "password":password})
    assert response.status_code == status
    assert response.json() == {'detail':respuesta}

@pytest.mark.asyncio
async def test_get_users(async_client, clean_redis):
    response = await async_client.get('user')
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    for user in users:
        assert all(key in user for key in ['user_id', 'username'])

    response = await async_client.get('user')
    assert response.status_code == 200

@pytest.fixture
def auth_headers2(client):
    response = client.post("/login", data={"username":"moure_dev", "password":"0000"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_update_user(async_client, auth_headers2):
    response = await async_client.patch('/user/me', headers=auth_headers2, json={'username':'SrStamm', 'email':'srstamm@gmail.com', 'password':'cambiado'})
    assert response.status_code == 200
    assert response.json() == {'detail':'Se ha actualizado el usuario con exito'}

@pytest.mark.asyncio
async def test_delete_user(async_client, auth_headers):
    response = await async_client.delete('/user/me', headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {'detail':'Se ha eliminado el usuario'}

@pytest.mark.asyncio
async def test_get_users_error(mocker):
    db_session_mock = mocker.Mock() 
    mock_request = mocker.Mock(spec=Request)
    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await user.get_users(request=mock_request, session=db_session_mock)

@pytest.mark.asyncio
async def test_create_user_error(mocker):
    db_session_mock = mocker.Mock()
    mock_request = mocker.Mock(spec=Request)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await user.create_user(
            request=mock_request,
            session=db_session_mock,
            new_user=schemas.CreateUser(
                username='Falso',
                email='falso@gmail.com',
                password='5555')
                )

    db_session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_update_user_me_error(mocker):
    session_mock = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)

    mock_request = mocker.Mock(spec=Request)

    session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await user.update_user_me(
                request=mock_request,
                updated_user=schemas.UpdateUser(username='Falso', email='falso@gmail.com', password='5555'),
                user=mock_user,
                session=session_mock)

    session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_delete_user_me_error(mocker):
    session_mock = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)

    mock_request = mocker.Mock(spec=Request)

    session_mock.delete.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await user.delete_user_me(
                request=mock_request,
                user=mock_user,
                session=session_mock)

    session_mock.rollback.assert_called_once()