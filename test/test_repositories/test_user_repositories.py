from repositories.user_repositories import UserRepository
from models.exceptions import DatabaseError
from db.database import SQLAlchemyError
import pytest


def test_delete_user_error(mocker):
    session_mock = mocker.Mock()
    user_mock = mocker.Mock()

    repo = UserRepository(session_mock)

    session_mock.commit.side_effect = SQLAlchemyError("db error")
    with pytest.raises(DatabaseError):
        repo.delete(user_mock)


def test_update_user_error(mocker):
    session_mock = mocker.Mock()
    user_mock = mocker.Mock()
    update_mock = mocker.Mock()

    repo = UserRepository(session_mock)

    session_mock.commit.side_effect = SQLAlchemyError("db error")
    with pytest.raises(DatabaseError):
        repo.update(user_mock, update_mock)
