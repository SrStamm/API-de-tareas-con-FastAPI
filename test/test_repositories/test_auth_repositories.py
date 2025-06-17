from dependency.auth_dependencies import AuthRepository
from db.database import SQLAlchemyError
from models.exceptions import DatabaseError
import pytest


def test_new_session_error(mocker):
    mock_session = mocker.Mock()
    repo = AuthRepository(mock_session)

    mock_session.add.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "new_session"
    )
    with pytest.raises(DatabaseError):
        repo.new_session("6165465", "1", "2050-12-12")


def test_get_session_wiht_jti(mocker):
    mock_session = mocker.Mock()
    repo = AuthRepository(mock_session)

    mock_session.exec.return_value.first.return_value = "algo"

    repo.get_session_with_jti("6165465")
