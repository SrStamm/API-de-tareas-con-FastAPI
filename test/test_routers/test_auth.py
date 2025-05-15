from conftest import client, test_user
import pytest
from sqlalchemy.exc import SQLAlchemyError
from models import exceptions, db_models
from routers import auth
from datetime import datetime, timezone, timedelta
from routers.auth import SECRET, ALGORITHM, JWTError

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

@pytest.mark.asyncio
async def test_auth_user_success(mocker):
    mock_session = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)
    expected_user_id = "user123"
    mock_user.user_id = expected_user_id

    mock_session.get.return_value = mock_user

    # Configura el payload que simula jwt.decode
    current_time = datetime.now(timezone.utc)
    expiration_time = current_time + timedelta(hours=1)
    mock_payload = {
        "sub": expected_user_id,
        "exp": expiration_time.timestamp(),
        "scope": 'api_access'
    }

    # Mockea jwt.decode DENTRO del módulo 'auth' donde se usa
    mock_jwt_decode = mocker.patch('routers.auth.jwt.decode', return_value=mock_payload)

    mocker.patch('routers.auth.datetime')

    auth.datetime.now.return_value = current_time
    
    auth.datetime.fromtimestamp = datetime.fromtimestamp

    test_token = "valid.fake.token"

    # 2. Ejecución
    returned_user = await auth.auth_user(token=test_token, session=mock_session)

    # 3. Verificaciones
    assert returned_user == mock_user
    
    # Verifica que jwt.decode fue llamado correctamente
    mock_jwt_decode.assert_called_once_with(test_token, SECRET, algorithms=ALGORITHM)
    
    # Verifica que session.get fue llamado correctamente
    mock_session.get.assert_called_once_with(db_models.User, expected_user_id)
    
    # Verifica que datetime.now fue llamado para la comprobación de expiración
    auth.datetime.now.assert_called_with(timezone.utc)

@pytest.mark.asyncio
async def test_auth_user_jwt_error(mocker):
    mock_session = mocker.Mock()

    # Mockea jwt.decode para que lance un JWTError
    mock_jwt_decode = mocker.patch('routers.auth.jwt.decode', side_effect=JWTError("Invalid signature"))
    test_token = "invalid.token"

    with pytest.raises(exceptions.InvalidToken):
        await auth.auth_user(token=test_token, session=mock_session)

    mock_jwt_decode.assert_called_once_with(test_token, SECRET, algorithms=ALGORITHM)
    mock_session.get.assert_not_called() # No debería llegar a buscar en la BD

@pytest.mark.asyncio
async def test_auth_user_no_sub(mocker):
    mock_session = mocker.Mock()
    expiration_time = datetime.now(timezone.utc) + timedelta(hours=1)

    # Payload sin 'sub'
    mock_payload = {"exp": expiration_time.timestamp()}
    mocker.patch('routers.auth.jwt.decode', return_value=mock_payload)
    test_token = "token.without.sub"

    with pytest.raises(exceptions.InvalidToken):
        await auth.auth_user(token=test_token, session=mock_session)

    mock_session.get.assert_not_called()

@pytest.mark.asyncio
async def test_auth_user_not_found_in_db(mocker):
    mock_session = mocker.Mock()
    expected_user_id = "unknown_user"

    # Configura session.get para devolver None
    mock_session.get.return_value = None

    current_time = datetime.now(timezone.utc)
    expiration_time = current_time + timedelta(hours=1)
    mock_payload = {
        "sub": expected_user_id,
        "exp": expiration_time.timestamp(),
        "scope": 'api_access'
    }

    mocker.patch('routers.auth.jwt.decode', return_value=mock_payload)
    mocker.patch('routers.auth.datetime')

    auth.datetime.now.return_value = current_time
    auth.datetime.fromtimestamp = datetime.fromtimestamp

    test_token = "token.for.unknown.user"

    with pytest.raises(exceptions.UserNotFoundError) as exc_info:
        await auth.auth_user(token=test_token, session=mock_session)

@pytest.mark.asyncio
async def test_auth_user_no_exp(mocker):
    mock_session = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)
    expected_user_id = "user456"
    mock_user.user_id = expected_user_id
    mock_session.get.return_value = mock_user

    # Payload sin 'exp'
    mock_payload = {"sub": expected_user_id, "scope": 'api_access'}
    mocker.patch('routers.auth.jwt.decode', return_value=mock_payload)

    test_token = "token.without.exp"

    with pytest.raises(exceptions.InvalidToken):
        await auth.auth_user(token=test_token, session=mock_session)

    mock_session.get.assert_called_once_with(db_models.User, expected_user_id)

@pytest.mark.asyncio
async def test_auth_user_expired_token(mocker):
    mock_session = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)
    expected_user_id = "user789"
    mock_user.user_id = expected_user_id
    mock_session.get.return_value = mock_user

    # Crea una fecha de expiración en el PASADO
    current_time = datetime.now(timezone.utc)
    expiration_time = current_time - timedelta(hours=1) # Expiró hace 1 hora
    mock_payload = {
        "sub": expected_user_id,
        "exp": expiration_time.timestamp(),
        "scope": 'api_access'
    }

    mocker.patch('routers.auth.jwt.decode', return_value=mock_payload)

    # Mockea datetime.now para devolver la hora actual
    mocker.patch('routers.auth.datetime')
    auth.datetime.now.return_value = current_time

    # Asegúrate de que fromtimestamp siga funcionando
    auth.datetime.fromtimestamp = datetime.fromtimestamp # Necesario para convertir exp
    
    test_token = "expired.token"

    with pytest.raises(exceptions.InvalidToken):
        await auth.auth_user(token=test_token, session=mock_session)

    mock_session.get.assert_called_once_with(db_models.User, expected_user_id)


    mock_session = mocker.Mock()
    expiration_time = datetime.now(timezone.utc) + timedelta(hours=1)

    # Payload sin 'sub'
    mock_payload = {"exp": expiration_time.timestamp()}
    mocker.patch('routers.auth.jwt.decode', return_value=mock_payload)
    test_token = "token.without.sub"

    with pytest.raises(exceptions.InvalidToken):
        await auth.auth_user(token=test_token, session=mock_session)

    mock_session.get.assert_not_called()

@pytest.mark.asyncio
async def test_logout(client, auth_headers):
    response = client.post('/logout', headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {'detail':'Cerradas todas las sesiones'}