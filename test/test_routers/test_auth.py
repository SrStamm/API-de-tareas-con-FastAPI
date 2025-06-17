from conftest import (
    client,
    test_user,
    async_client,
    auth_headers,
    auth_tokens,
    PASSWORD,
)
import pytest
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Request
from models import exceptions, db_models, schemas
from api.v1.routers import auth
from datetime import datetime, timezone, timedelta
from api.v1.routers.auth import SECRET, ALGORITHM, JWTError, ACCESS_TOKEN_DURATION
from jose import jwt
import uuid
from core.logger import logger


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"detail": "Bienvenido a esta API!"}


def test_failed_login_not_found(client):
    response = client.post("/login", data={"username": "a", "password": "0000"})
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_failed_login_incorrect_password(client, test_user):
    response = client.post("/login", data={"username": "mirko", "password": "5555"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Password incorrect"}


"""@pytest.mark.asyncio
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
        "scope": "api_access",
    }

    # Mockea jwt.decode DENTRO del módulo 'auth' donde se usa
    mock_jwt_decode = mocker.patch(
        "api.v1.routers.auth.jwt.decode", return_value=mock_payload
    )

    mocker.patch("api.v1.routers.auth.datetime")

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
    mock_jwt_decode = mocker.patch(
        "api.v1.routers.auth.jwt.decode", side_effect=JWTError("Invalid signature")
    )
    test_token = "invalid.token"

    with pytest.raises(exceptions.InvalidToken):
        await auth.auth_user(token=test_token, session=mock_session)

    mock_jwt_decode.assert_called_once_with(test_token, SECRET, algorithms=ALGORITHM)
    mock_session.get.assert_not_called()  # No debería llegar a buscar en la BD


@pytest.mark.asyncio
async def test_auth_user_no_sub(mocker):
    mock_session = mocker.Mock()
    expiration_time = datetime.now(timezone.utc) + timedelta(hours=1)

    # Payload sin 'sub'
    mock_payload = {"exp": expiration_time.timestamp(), "sub": None}
    mocker.patch("api.v1.routers.auth.jwt.decode", return_value=mock_payload)
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
        "scope": "api_access",
    }

    mocker.patch("api.v1.routers.auth.jwt.decode", return_value=mock_payload)
    mocker.patch("api.v1.routers.auth.datetime")

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
    mock_payload = {"sub": expected_user_id, "scope": "api_access"}
    mocker.patch("api.v1.routers.auth.jwt.decode", return_value=mock_payload)

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
    expiration_time = current_time - timedelta(hours=1)  # Expiró hace 1 hora
    mock_payload = {
        "sub": expected_user_id,
        "exp": expiration_time.timestamp(),
        "scope": "api_access",
    }

    mocker.patch("api.v1.routers.auth.jwt.decode", return_value=mock_payload)

    # Mockea datetime.now para devolver la hora actual
    mocker.patch("api.v1.routers.auth.datetime")
    auth.datetime.now.return_value = current_time

    # Asegúrate de que fromtimestamp siga funcionando
    auth.datetime.fromtimestamp = datetime.fromtimestamp  # Necesario para convertir exp

    test_token = "expired.token"

    with pytest.raises(exceptions.InvalidToken):
        await auth.auth_user(token=test_token, session=mock_session)

    mock_session.get.assert_called_once_with(db_models.User, expected_user_id)

    mock_session = mocker.Mock()
    expiration_time = datetime.now(timezone.utc) + timedelta(hours=1)

    # Payload sin 'sub'
    mock_payload = {"exp": expiration_time.timestamp()}
    mocker.patch("api.v1.routers.auth.jwt.decode", return_value=mock_payload)
    test_token = "token.without.sub"

    with pytest.raises(exceptions.InvalidToken):
        await auth.auth_user(token=test_token, session=mock_session)

    mock_session.get.assert_not_called()
"""


@pytest.mark.asyncio
async def test_logout(client, auth_headers):
    response = client.post("/logout", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"detail": "Closed all sessions"}


"""@pytest.mark.asyncio
async def test_logout_error(mocker):
    user_mock = mocker.Mock(spec=db_models.User)

    mock_request = mocker.Mock(spec=Request)

    session_mock = mocker.Mock()
    session_mock.exec.return_value.all.return_value = None

    with pytest.raises(exceptions.SessionNotFound):
        await auth.logout(
            request=mock_request,
            session=session_mock,
            user=user_mock
        )
    
    session_db_mocker = mocker.Mock(spec=db_models.Session)

    session_mock.exec.return_value.all.return_value = session_db_mocker

    session_mock.exec.side_effect = SQLAlchemyError('Error en la base de datos')
    
    with pytest.raises(exceptions.DatabaseError):
        await auth.logout(
            request=mock_request,
            session=session_mock,
            user=user_mock
        )
    
    session_mock.rollback.assert_called_once()"""

"""
def test_refresh_token(client):
    login_response = client.post("/login", data={"username": 'mirko', "password": PASSWORD})
    tokens = login_response.json()
    refresh_token = tokens["refresh_token"]

    token = schemas.RefreshTokenRequest(refresh=refresh_token).model_dump_json()
    print(refresh_token)
    print(token)

    response = client.post("/refresh", json={"refresh": token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_token_format(client, auth_headers):
    h = auth_headers
    login_response = client.post("/login", data={"username": 'mirko', "password": PASSWORD})
    tokens = login_response.json()
    refresh_token = tokens["refresh_token"]

    # Verifica el contenido del refresh token
    claims = jwt.get_unverified_claims(refresh_token)
    print("Refresh token payload:", claims)

@pytest.mark.asyncio
async def test_refresh_success(mocker):
    # Setup
    mock_session = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)
    expected_user_id = "123"
    mock_user.user_id = expected_user_id
    mock_session.get.return_value = mock_user
    
    mock_actual_session = mocker.Mock(spec=db_models.Session)
    mock_actual_session.jti = str(uuid.uuid4())
    mock_actual_session.is_active = True
    mock_session.exec.return_value.first.return_value = mock_actual_session
    
    mock_request = mocker.Mock(spec=Request)
    
    # Use the real datetime for generating timestamps for the payload
    current_time_for_payload = datetime.now(timezone.utc)
    expiration_time_for_payload = current_time_for_payload + timedelta(hours=1)
    mock_payload = {
        "jti": mock_actual_session.jti,
        "sub": expected_user_id,
        "exp": expiration_time_for_payload.timestamp(),
        "scope": "token_refresh"
    }
    
    # This will be the controlled 'current time' within the function under test
    controlled_current_time = datetime.now(timezone.utc) 

    # Mock dependencies
    mocker.patch('api.v1.routers.auth.jwt.get_unverified_claims', return_value=mock_payload)
    mocker.patch('api.v1.routers.auth.jwt.decode', return_value=mock_payload)

    # Correctly mock datetime within the 'auth' module
    mocked_auth_datetime = mocker.patch('api.v1.routers.auth.datetime')
    mocked_auth_datetime.now.return_value = controlled_current_time
    # Ensure fromtimestamp uses the real datetime.fromtimestamp from the test's global scope
    # (imported via 'from datetime import datetime')
    mocked_auth_datetime.fromtimestamp = datetime.fromtimestamp 
    
    mock_jwt_encode = mocker.patch('api.v1.routers.auth.jwt.encode', side_effect=[
        "new_access_token",  # First call for access token
        "new_refresh_token"  # Second call for refresh token
    ])
    
    test_token = "valid.fake.token"
    
    # Execution
    result = await auth.refresh(
        refresh=schemas.RefreshTokenRequest(refresh=test_token), 
        request=mock_request, 
        session=mock_session
    )
    
    # Assertions
    assert isinstance(result, schemas.Token)
    assert result.access_token == "new_access_token"
    assert result.refresh_token == "new_refresh_token"
    assert result.token_type == "bearer"
    
    # Verify session interactions
    mock_session.exec.assert_called_once()
    mock_session.delete.assert_called_once_with(mock_actual_session)
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()
    
    # Verify JWT encode calls
    assert mock_jwt_encode.call_count == 2
    access_token_call_args = mock_jwt_encode.call_args_list[0][0][0]
    assert access_token_call_args["sub"] == expected_user_id
    assert access_token_call_args["scope"] == "api_access"
    # Check that the mocked 'now' was used for expiry calculation for access token
    expected_access_exp = controlled_current_time + timedelta(minutes=ACCESS_TOKEN_DURATION) # Assuming ACCESS_TOKEN_DURATION is accessible or known
    assert access_token_call_args["exp"] == expected_access_exp.timestamp()

    refresh_token_call_args = mock_jwt_encode.call_args_list[1][0][0]
    assert refresh_token_call_args["scope"] == "token_refresh"
    assert refresh_token_call_args["sub"] == expected_user_id
    # Check that the mocked 'now' was used for expiry calculation for refresh token
    # This requires knowing REFRESH_TOKEN_DURATION or checking the 'new_session.expires_at' directly if it's based on the mocked time.
    # The code under test does: new_session.expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DURATION)
    # So, the 'exp' in the refresh token should be based on 'controlled_current_time'.

    # To properly verify expirations, ensure ACCESS_TOKEN_DURATION and REFRESH_TOKEN_DURATION
    # are defined or imported in your test file if you want to check exact timestamps.
    # For example:
    # from api.v1.routers.auth import ACCESS_TOKEN_DURATION, REFRESH_TOKEN_DURATION

    # ... (other test cases remain unchanged)

@pytest.mark.asyncio
async def test_refresh_invalid_session(mocker):
    # Setup
    mock_session = mocker.Mock()
    mock_session.exec.return_value.first.return_value = None
    mock_request = mocker.Mock(spec=Request)
    
    current_time = datetime.now(timezone.utc)
    mock_payload = {
        "jti": str(uuid.uuid4()),
        "sub": "123",
        "exp": (current_time + timedelta(hours=1)).timestamp(),
        "scope": "token_refresh"
    }
    
    mocker.patch('api.v1.routers.auth.jwt.get_unverified_claims', return_value=mock_payload)
    
    # Execution and Assertion
    with pytest.raises(exceptions.InvalidToken):
        await auth.refresh(
            refresh=schemas.RefreshTokenRequest(refresh="invalid.session.token"),
            request=mock_request,
            session=mock_session
        )

@pytest.mark.asyncio
async def test_refresh_invalid_scope(mocker):
    # Setup
    mock_session = mocker.Mock()
    mock_actual_session = mocker.Mock(spec=db_models.Session)
    mock_actual_session.jti = str(uuid.uuid4())
    mock_actual_session.is_active = True
    mock_session.exec.return_value.first.return_value = mock_actual_session
    mock_request = mocker.Mock(spec=Request)
    
    current_time = datetime.now(timezone.utc)
    mock_payload = {
        "jti": mock_actual_session.jti,
        "sub": "123",
        "exp": (current_time + timedelta(hours=1)).timestamp(),
        "scope": "invalid_scope"
    }
    
    mocker.patch('api.v1.routers.auth.jwt.get_unverified_claims', return_value=mock_payload)
    mocker.patch('api.v1.routers.auth.jwt.decode', return_value=mock_payload)
    
    # Execution and Assertion
    with pytest.raises(exceptions.InvalidToken):
        await auth.refresh(
            refresh=schemas.RefreshTokenRequest(refresh="invalid.scope.token"),
            request=mock_request,
            session=mock_session
        )

@pytest.mark.asyncio
async def test_refresh_expired_token(mocker):
    # Setup
    mock_session = mocker.Mock()
    mock_actual_session = mocker.Mock(spec=db_models.Session)
    mock_actual_session.jti = str(uuid.uuid4())
    mock_actual_session.is_active = True
    mock_session.exec.return_value.first.return_value = mock_actual_session
    mock_request = mocker.Mock(spec=Request)
    
    # This is the time the token is supposedly checked
    controlled_current_time = datetime.now(timezone.utc) 
    
    mock_payload = {
        "jti": mock_actual_session.jti,
        "sub": "123",
        "exp": (controlled_current_time - timedelta(hours=1)).timestamp(),  # Expired
        "scope": "token_refresh"
    }
    
    mocker.patch('api.v1.routers.auth.jwt.get_unverified_claims', return_value=mock_payload)
    mocker.patch('api.v1.routers.auth.jwt.decode', return_value=mock_payload)

    # Correctly mock datetime within the 'auth' module
    mocked_auth_datetime = mocker.patch('api.v1.routers.auth.datetime')
    mocked_auth_datetime.now.return_value = controlled_current_time
    mocked_auth_datetime.fromtimestamp = datetime.fromtimestamp
    
    # Execution and Assertion
    with pytest.raises(exceptions.InvalidToken):
        await auth.refresh(
            refresh=schemas.RefreshTokenRequest(refresh="expired.token"),
            request=mock_request,
            session=mock_session
        )

@pytest.mark.asyncio
async def test_refresh_user_not_found(mocker):
    # Setup
    mock_session = mocker.Mock()
    mock_actual_session = mocker.Mock(spec=db_models.Session)
    mock_actual_session.jti = str(uuid.uuid4())
    mock_actual_session.is_active = True
    mock_session.exec.return_value.first.return_value = mock_actual_session
    mock_session.get.return_value = None
    mock_request = mocker.Mock(spec=Request)
    
    current_time = datetime.now(timezone.utc)
    mock_payload = {
        "jti": mock_actual_session.jti,
        "sub": "123",
        "exp": (current_time + timedelta(hours=1)).timestamp(),
        "scope": "token_refresh"
    }
    
    mocker.patch('api.v1.routers.auth.jwt.get_unverified_claims', return_value=mock_payload)
    mocker.patch('api.v1.routers.auth.jwt.decode', return_value=mock_payload)
    
    # Execution and Assertion
    with pytest.raises(exceptions.UserNotFoundError):
        await auth.refresh(
            refresh=schemas.RefreshTokenRequest(refresh="user.not.found.token"),
            request=mock_request,
            session=mock_session
        )

@pytest.mark.asyncio
async def test_refresh_jwt_error(mocker):
    # Setup
    mock_session = mocker.Mock()
    mock_request = mocker.Mock(spec=Request)
    
    mocker.patch('api.v1.routers.auth.jwt.get_unverified_claims', side_effect=JWTError("Invalid JWT"))
    
    # Execution and Assertion
    with pytest.raises(exceptions.InvalidToken):
        await auth.refresh(
            refresh=schemas.RefreshTokenRequest(refresh="invalid.jwt.token"),
            request=mock_request,
            session=mock_session
        )

@pytest.mark.asyncio
async def test_refresh_database_error(mocker):
    # Setup
    mock_session = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)
    expected_user_id = "123"
    mock_user.user_id = expected_user_id
    mock_session.get.return_value = mock_user
    
    mock_actual_session = mocker.Mock(spec=db_models.Session)
    mock_actual_session.jti = str(uuid.uuid4())
    mock_actual_session.is_active = True
    mock_session.exec.return_value.first.return_value = mock_actual_session
    mock_session.commit.side_effect = SQLAlchemyError("Database error")
    
    mock_request = mocker.Mock(spec=Request)
    
    # This will be the controlled 'current time'
    controlled_current_time = datetime.now(timezone.utc)
    
    mock_payload = {
        "jti": mock_actual_session.jti,
        "sub": expected_user_id,
        "exp": (controlled_current_time + timedelta(hours=1)).timestamp(), # Not expired for this test
        "scope": "token_refresh"
    }
    
    mocker.patch('api.v1.routers.auth.jwt.get_unverified_claims', return_value=mock_payload)
    mocker.patch('api.v1.routers.auth.jwt.decode', return_value=mock_payload)

    # Correctly mock datetime within the 'auth' module
    mocked_auth_datetime = mocker.patch('api.v1.routers.auth.datetime')
    mocked_auth_datetime.now.return_value = controlled_current_time
    mocked_auth_datetime.fromtimestamp = datetime.fromtimestamp
    
    # Execution and Assertion
    with pytest.raises(exceptions.DatabaseError):
        await auth.refresh(
            refresh=schemas.RefreshTokenRequest(refresh="db.error.token"),
            request=mock_request,
            session=mock_session
        )
    mock_session.rollback.assert_called_once()
"""


def test_get_expired_sessions(client):
    response = client.get("/expired")
    assert response.status_code == 200
