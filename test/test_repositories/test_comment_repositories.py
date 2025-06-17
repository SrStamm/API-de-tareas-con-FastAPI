from repositories.comment_repositories import CommentRepository
from db.database import SQLAlchemyError
from models.exceptions import DatabaseError
import pytest


def test_create_error(mocker):
    mock_session = mocker.Mock()

    comment_mock = mocker.Mock()

    repo = CommentRepository(mock_session)

    mock_session.add.side_effect = SQLAlchemyError("db error")
    with pytest.raises(DatabaseError):
        repo.create(comment_mock, 1, 1)


def test_update_error(mocker):
    mock_session = mocker.Mock()

    comment_mock = mocker.Mock()
    update_mock = mocker.Mock()

    repo = CommentRepository(mock_session)

    mock_session.commit.side_effect = SQLAlchemyError("db error")
    with pytest.raises(DatabaseError):
        repo.update(update_mock, comment_mock)


def test_delete_error(mocker):
    mock_session = mocker.Mock()

    comment_mock = mocker.Mock()

    repo = CommentRepository(mock_session)

    mock_session.commit.side_effect = SQLAlchemyError("db error")
    with pytest.raises(DatabaseError):
        repo.delete(comment_mock)
