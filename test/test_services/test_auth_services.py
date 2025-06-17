from datetime import datetime, timezone, timedelta

from httpx._transports import mock
from db.database import SQLAlchemyError
from sqlalchemy.exc import DatabaseError
from models.exceptions import (
    InvalidToken,
    DatabaseError,
    SessionNotFound,
    UserNotFoundError,
)
from services.auth_services import AuthService
import pytest


def test_get_expired_sessions_success(mocker):
    mock_auth_repo = mocker.Mock()
    expired_sessions = [
        {"jti": "asfasfa", "sub": "2", "is_active": True, "use_count": 1}
    ]

    mock_auth_repo.get_expired_sessions.return_value = expired_sessions

    service = AuthService(mock_auth_repo)

    result = service.get_expired_sessions()

    mock_auth_repo.get_expired_sessions.assert_called_once()
    assert result == expired_sessions


def test_auth_user_error(mocker):
    mock_repo = mocker.Mock()
    mock_token = mocker.Mock()

    serv = AuthService(mock_repo)

    mocker.patch("services.auth_services.jwt.decode", side_effect=InvalidToken)

    with pytest.raises(InvalidToken):
        serv.auth_user(mock_token)


def test_auth_user_scope_error(mocker):
    mock_repo = mocker.Mock()
    mock_token = mocker.Mock()

    serv = AuthService(mock_repo)

    mock_payload = {}

    mocker.patch("services.auth_services.jwt.decode", return_value=mock_payload)

    with pytest.raises(InvalidToken):
        serv.auth_user(mock_token)


def test_auth_user_sub_error(mocker):
    mock_repo = mocker.Mock()
    mock_token = mocker.Mock()

    serv = AuthService(mock_repo)

    expiration_time = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_payload = {"exp": expiration_time.timestamp(), "scope": "api_access"}

    mocker.patch("services.auth_services.jwt.decode", return_value=mock_payload)

    with pytest.raises(InvalidToken):
        serv.auth_user(mock_token)


def test_auth_user_not_found_error(mocker):
    mock_repo = mocker.Mock()
    mock_token = mocker.Mock()

    serv = AuthService(mock_repo)

    mock_payload = {"sub": "1", "scope": "api_access"}

    mocker.patch("services.auth_services.jwt.decode", return_value=mock_payload)

    mock_repo.get_user_by_id.return_value = None
    with pytest.raises(UserNotFoundError):
        serv.auth_user(mock_token)


def test_auth_user_exp_error(mocker):
    mock_repo = mocker.Mock()
    mock_token = mocker.Mock()

    serv = AuthService(mock_repo)

    mock_payload = {"sub": "1", "scope": "api_access"}

    mocker.patch("services.auth_services.jwt.decode", return_value=mock_payload)

    mock_repo.get_user_by_id.return_value = None
    with pytest.raises(UserNotFoundError):
        serv.auth_user(mock_token)


def test_auth_user_token_expired_error(mocker):
    mock_repo = mocker.Mock()
    mock_token = mocker.Mock()

    serv = AuthService(mock_repo)

    expiration_time = datetime.now(timezone.utc) - timedelta(hours=1)
    mock_payload = {
        "sub": "1",
        "scope": "api_access",
        "exp": expiration_time.timestamp(),
    }

    mocker.patch("services.auth_services.jwt.decode", return_value=mock_payload)

    mock_repo.get_user_by_id.return_value = None
    with pytest.raises(UserNotFoundError):
        serv.auth_user(mock_token)



def test_logout_sessions_found(mocker):
    mock_repo = mocker.Mock()

    serv = AuthService(mock_repo)

    mock_repo.get_active_sessions.return_value = None

    with pytest.raises(SessionNotFound):
        serv.logout(1)

    mock_repo.get_active_sessions.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "logout"
    )

    with pytest.raises(DatabaseError):
        serv.logout(1)
