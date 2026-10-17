from jose.exceptions import ExpiredSignatureError

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
from services.auth_services import AuthService
from repositories.auth_repositories import AuthRepository


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


def test_logout(client, auth_headers):
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


def test_refresh(client, auth_headers, auth_tokens):
    response = client.post(
        "/refresh", 
        headers=auth_headers, 
        json={"refresh": auth_tokens["refresh_token"]}
    )
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in data
    assert data["access_token"] != auth_headers["Authorization"].split()[1]


# =============================================================================
# B3 — Casos borde de AuthService.refresh()
#
# ESTRATEGIA: tests UNITARIOS sobre AuthService, no sobre el router.
# ¿Por qué? Porque el happy path ya está cubierto por test_refresh() vía HTTP.
# Lo que queda por cubrir son las 8 ramas de error de refresh(), y la mayoría
# son IMPOSIBLES de provocar contra el router con datos reales (no podés hacer
# que la BD "olvide" una sesión sin romper otras cosas, ni forzar un payload
# sin 'scope' sin tener la clave secreta).
#
# PATRÓN que vas a repetir en CADA test de acá abajo:
#
#   1. ARRANGE
#      - Crear `mock_repo = mocker.Mock(spec=AuthRepository)`
#        (`spec=` es importante: si le pedís un método que no existe, explota
#        en vez de devolverte un Mock silencioso y mentirte)
#      - Crear `servicio = AuthService(auth_repo=mock_repo)`
#      - Mockear `services.auth_services.jwt` (NO `api.v1.routers.auth.jwt`,
#        este código vive en services/, no en el router)
#   2. ACT  -> llamar `servicio.refresh(RefreshTokenRequest(refresh="..."))`
#   3. ASSERT -> `pytest.raises(<excepción>)` + asserts sobre el mock
#        para verificar que NO llegó más lejos de donde debía
#
# REGLA DE ORO: en cada caso de error, verificá además que el mock del repo
# NO fue llamado para operaciones posteriores. Un `raise` que no corta el flujo
# es un bug que este assert detecta.
# =============================================================================


def test_refresh_session_not_found(mocker):
    # Rama auth_services.py:137 — el jti no existe en la BD.

    mock_repo = mocker.Mock(spec=AuthRepository)
    mock_repo.get_session_with_jti.return_value = None

    mock_payload = { "jti" : "falso"}
    mocker.patch('services.auth_services.jwt.get_unverified_claims', return_value=mock_payload)

    with pytest.raises(exceptions.InvalidToken):
        AuthService(auth_repo=mock_repo).refresh(schemas.RefreshTokenRequest(refresh="falso"))

    mock_repo.get_session_with_jti.assert_called_once_with(mock_payload["jti"])
    mock_repo.delete_session.assert_not_called()


def test_refresh_missing_scope(mocker):
    # Rama auth_services.py:143 — el payload no trae 'scope'.

    mock_repo = mocker.Mock(spec=AuthRepository)
    mock_repo.get_session_with_jti.return_value = mocker.Mock()

    mocker.patch('services.auth_services.jwt.get_unverified_claims', return_value={})
    mocker.patch('services.auth_services.jwt.decode', return_value={})

    with pytest.raises(exceptions.InvalidToken):
        AuthService(auth_repo=mock_repo).refresh(schemas.RefreshTokenRequest(refresh="falso"))

    mock_repo.get_user_by_id.assert_not_called()


def test_refresh_wrong_scope(mocker):
    # Rama auth_services.py:146 — 'scope' existe pero no es 'token_refresh'.

    mock_repo = mocker.Mock(spec=AuthRepository)
    mock_repo.get_session_with_jti.return_value = mocker.Mock()

    mocker.patch('services.auth_services.jwt.get_unverified_claims', return_value={})
    mocker.patch('services.auth_services.jwt.decode', return_value={"scope" : "api_access"})

    with pytest.raises(exceptions.InvalidToken):
        AuthService(auth_repo=mock_repo).refresh(schemas.RefreshTokenRequest(refresh="falso"))

    mock_repo.delete_session.assert_not_called()


def test_refresh_missing_sub(mocker):
    # Rama auth_services.py:150 — el payload no trae 'sub' (user_id).

    mock_repo = mocker.Mock(spec=AuthRepository)
    mock_repo.get_session_with_jti.return_value = mocker.Mock()

    mocker.patch('services.auth_services.jwt.get_unverified_claims', return_value={})
    mocker.patch('services.auth_services.jwt.decode', return_value={"scope" : "token_refresh"})

    with pytest.raises(exceptions.InvalidToken):
        AuthService(auth_repo=mock_repo).refresh(schemas.RefreshTokenRequest(refresh="falso"))

    mock_repo.get_user_by_id.assert_not_called()


def test_refresh_user_not_found(mocker):
    # Rama auth_services.py:154 — el 'sub' existe pero ese usuario no está en BD.

    mock_repo = mocker.Mock(spec=AuthRepository)
    mock_repo.get_session_with_jti.return_value = mocker.Mock()
    mock_repo.get_user_by_id.return_value = None

    mocker.patch('services.auth_services.jwt.get_unverified_claims', return_value={})
    mocker.patch('services.auth_services.jwt.decode', return_value={"scope" : "token_refresh", "sub": "u_1"})

    with pytest.raises(exceptions.UserNotFoundError) as exc_info:
        AuthService(auth_repo=mock_repo).refresh(schemas.RefreshTokenRequest(refresh="falso"))

    assert exc_info.value.user_id == "u_1"
    mock_repo.delete_session.assert_not_called()


def test_refresh_missing_exp(mocker):
    """Rama auth_services.py:162 — el payload no trae 'exp'.

    Debe lanzar: InvalidToken (401)

    ⚠️  CASO TRAMPOSO: jwt.decode NO valida 'exp' si el claim no existe.
    Lo devuelve como None y seguís de largo hasta la línea 162.
    (Distinto del token EXPIRADO, que sí lo revienta jwt.decode — ver test de abajo)

    ARRANGE:
      - jwt.decode -> payload con scope y sub, pero SIN "exp"

    ASSERT:
      - pytest.raises(exceptions.InvalidToken)
      - mock_repo.delete_session.assert_not_called()
    """

    mock_repo = mocker.Mock(spec=AuthRepository)
    mock_repo.get_session_with_jti.return_value = mocker.Mock()
    mock_repo.get_user_by_id.return_value = mocker.Mock()

    mocker.patch('services.auth_services.jwt.get_unverified_claims', return_value={})
    mocker.patch('services.auth_services.jwt.decode', return_value={"scope" : "token_refresh", "sub": "u_1"})

    with pytest.raises(exceptions.InvalidToken):
        AuthService(auth_repo=mock_repo).refresh(schemas.RefreshTokenRequest(refresh="falso"))

    mock_repo.delete_session.assert_not_called()


def test_refresh_expired_token(mocker):
    """Rama auth_services.py:206 (NO la 165) — token con 'exp' en el pasado.

    Debe lanzar: InvalidToken (401)

    ⚠️  TRAMPA CONFIRMADA — le dediqué una verificación a esto:
        >>> jwt.encode({'exp': <pasado>, ...}); jwt.decode(...)  ->  ExpiredSignatureError
        ExpiredSignatureError ES subclase de JWTError.

    Consecuencia: jwt.decode explota en la LÍNEA 135, el `except JWTError` de la
    línea 206 lo atrapa, y las líneas 162-166 (la verificación manual de exp)
    NUNCA se ejecutan. Esa verificación es código muerto/defensivo.

    Entonces: este test pasa, pero valida la línea 206, no la 165.
    Si querés probar la 165 tendrías que mockear jwt.decode para que devuelva
    un payload con exp viejo SIN lanzar excepción. Es válido hacerlo — decidí vos.

    ARRANGE (opción A, camino real):
      - mockear jwt.decode con side_effect=ExpiredSignatureError("Signature has expired")
      - o construir un token REAL con exp pasado usando la clave SECRET
    ARRANGE (opción B, para probar la línea 165 que está aislada):
      - jwt.decode devuelve payload con exp = timestamp del pasado

    ASSERT:
      - pytest.raises(exceptions.InvalidToken)
      - mock_repo.delete_session.assert_not_called()
    """

    mock_repo = mocker.Mock(spec=AuthRepository)
    mock_repo.get_session_with_jti.return_value = mocker.Mock()

    mocker.patch(
        'services.auth_services.jwt.get_unverified_claims',
        return_value={"jti": "jti_viejo"}
    )
    mocker.patch(
        'services.auth_services.jwt.decode',
        side_effect=ExpiredSignatureError("Signature has expired")
        )

    with pytest.raises(exceptions.InvalidToken):
        AuthService(auth_repo=mock_repo).refresh(schemas.RefreshTokenRequest(refresh="falso"))

    mock_repo.delete_session.assert_not_called()

def test_refresh_invalid_signature(mocker):
    """Rama auth_services.py:206 — firma inválida / token basura.

    Debe lanzar: InvalidToken (401)

    ARRANGE:
      - mockear jwt.get_unverified_claims con side_effect=JWTError("Invalid signature")
      - Esto es lo que pasa con un string random tipo "esto.no.es.un.jwt"

    ASSERT:
      - pytest.raises(exceptions.InvalidToken)
      - mock_repo.get_session_with_jti.assert_not_called()
        <- CLAVE: si la firma es inválida, NO debés consultar la BD.
           Si este assert falla, tenés un problema de seguridad (oracle de
           existencia de sesiones).
    """

    mock_repo = mocker.Mock(spec=AuthRepository)
    mock_repo.get_session_with_jti.return_value({})

    mocker.patch(
        'services.auth_services.jwt.get_unverified_claims',
        side_effect=JWTError("Invalid signature")
        )

    with pytest.raises(exceptions.InvalidToken):
        AuthService(auth_repo=mock_repo).refresh(schemas.RefreshTokenRequest(refresh="falso"))

    mock_repo.get_session_with_jti.assert_not_called()


def test_refresh_database_error(mocker):
    """Rama auth_services.py:208 — el repo lanza DatabaseError.

    Debe lanzar: DatabaseError (500), propagado SIN tragar.

    ARRANGE:
      - mock_repo.get_session_with_jti con side_effect=DatabaseError("boom", "get_session_with_jti")
        (DatabaseError necesita 2 args: error y func)
      - OJO: DatabaseError es HTTPException, así que tiene status_code 500

    ASSERT:
      - pytest.raises(exceptions.DatabaseError)
      - Verificá que NO se convirtió en InvalidToken — si el except DatabaseError
        no estuviera, caería en un handler genérico y el status podría cambiar.
    """

    mock_repo = mocker.Mock(spec=AuthRepository)
    mocker.patch('services.auth_services.jwt.get_unverified_claims', return_value={})
    mock_repo.get_session_with_jti.side_effect=exceptions.DatabaseError("boom", "get_session_with_jti")

    with pytest.raises(exceptions.DatabaseError):
        AuthService(auth_repo=mock_repo).refresh(schemas.RefreshTokenRequest(refresh="falso"))


def test_refresh_success_rotates_session(mocker):
    """Rama feliz DETALLADA — verifica que rota la sesión correctamente.

    Esto complementa test_refresh() (que es integration y sólo mira el 200).

    Debe devolver: Token(access_token=..., token_type="bearer", refresh_token=...)

    ARRANGE:
      - mock_repo.get_session_with_jti -> una session mock con .jti
      - mock_repo.get_user_by_id -> un user mock con .user_id
      - mock_repo.new_session -> un objeto con .jti, .sub, .expires_at (datetime)
        ⚠️ DEBE tener expires_at real, porque refresh() lee new_session.expires_at
        para armar el exp del nuevo refresh token (línea 184)
      - jwt.decode -> payload completo y válido
      - jwt.encode -> side_effect=["nuevo_access", "nuevo_refresh"]

    ASSERT (las que importan):
      - result.access_token == "nuevo_access"
      - result.token_type == "bearer"
      - result.refresh_token == "nuevo_refresh"
      - mock_repo.delete_session.assert_called_once_with(<la session vieja>)
        <- la sesión VIEJA se borra. Es el corazón del refresh.
      - mock_repo.new_session.assert_called_once()
      - jwt.encode se llamó 2 veces
      - El payload del PRIMER encode tiene scope="api_access"
      - El payload del SEGUNDO encode tiene scope="token_refresh"
    """
    mock_repo = mocker.Mock(spec=AuthRepository)

    mock_session = mocker.Mock()
    mock_session.jti = "jti_viejo"
    mock_repo.get_session_with_jti.return_value = mock_session


    user_mock = mocker.Mock()
    user_mock.user_id = "u_1"
    mock_repo.get_user_by_id.return_value = user_mock

    mock_new_session = mocker.Mock()
    mock_new_session.jti = "jti_nuevo"
    mock_new_session.sub = "u_1"
    mock_new_session.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    mock_repo.new_session.return_value = mock_new_session

    mocker.patch(
        'services.auth_services.jwt.get_unverified_claims',
        return_value={"jti": "jti_viejo"}
    )
    mocker.patch(
        'services.auth_services.jwt.decode',
        return_value={
            "scope": "token_refresh",
            "sub": "u_1",
            "exp": (datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()
        }
    )

    mock_jwt_encode = mocker.patch(
        'services.auth_services.jwt.encode',
        side_effect=["nuevo_access", "nuevo_refresh"]
    )

    result = AuthService(auth_repo=mock_repo).refresh(schemas.RefreshTokenRequest(refresh="falso"))


    assert result.access_token == "nuevo_access"
    assert result.token_type == "bearer"
    assert result.refresh_token == "nuevo_refresh"

    mock_repo.delete_session.assert_called_once_with(mock_session)
    mock_repo.new_session.assert_called_once()

    # Verificar llamadas a jwt.encode y sus payloads
    assert mock_jwt_encode.call_count == 2

    # Primer encode: access_token (scope="api_access")
    first_call_args = mock_jwt_encode.call_args_list[0][0][0]
    assert first_call_args["scope"] == "api_access"

    # Segundo encode: refresh_token (scope="token_refresh")
    second_call_args = mock_jwt_encode.call_args_list[1][0][0]
    assert second_call_args["scope"] == "token_refresh"


def test_refresh_with_garbage_token_returns_401(client):
    response = client.post("/refresh", json={"refresh": "esto.no.es.un.jwt"})
    assert response.status_code == 401


def test_get_expired_sessions(client):
    response = client.get("/expired")
    assert response.status_code == 200
