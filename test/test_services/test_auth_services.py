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
