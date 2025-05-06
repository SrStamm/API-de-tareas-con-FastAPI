from conftest import client, test_user
import pytest
from sqlalchemy.exc import SQLAlchemyError
from models import exceptions
from routers import auth

def test_root(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {'detail':'Bienvenido a esta API!'}

def test_failed_login_not_found(client):
    response = client.post("/login", data= {"username":'a', "password":'0000'})
    assert response.status_code == 404
    assert response.json() == {'detail':'User not found'}

def test_failed_login_incorrect_password(client, test_user):
    response = client.post("/login", data= {"username":test_user.username, "password":'5555'})
    assert response.status_code == 400
    assert response.json() == {'detail':'Password incorrect'}

@pytest.mark.asyncio
async def test_login_error(mocker):
    form_mock = mocker.Mock()
    form_mock.username = "fake"
    form_mock.password = "555555"

    session_mock = mocker.Mock()
    session_mock.exec.side_effect = SQLAlchemyError('Error en la base de datos')

    with pytest.raises(exceptions.DatabaseError):
        await auth.login( form=form_mock, session=session_mock)
    
    session_mock.rollback.assert_called_once()