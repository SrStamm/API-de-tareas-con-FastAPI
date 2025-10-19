from db.database import SQLAlchemyError
from models.exceptions import (
    CommentNotFoundError,
    DatabaseError,
    UserNotAuthorizedInCommentError,
)
from models.schemas import CreateComment, UpdateComment
from services.comment_services import CommentService
import pytest


def test_get_all_comments_not_found_error(mocker):
    mock_comment_repo = mocker.Mock()
    mock_task_serv = mocker.Mock()

    mock_comment_repo.get_all_comments.return_value = None
    service = CommentService(mock_comment_repo, mock_task_serv)

    with pytest.raises(CommentNotFoundError):
        service.get_all_comments(task_id=1)


@pytest.mark.asyncio
async def test_create_error(mocker):
    mock_comment_repo = mocker.Mock()
    mock_task_serv = mocker.Mock()

    mock_comment = mocker.Mock(spec=CreateComment)
    mock_comment.content = "probando"

    service = CommentService(mock_comment_repo, mock_task_serv)

    mock_task_serv.found_user_assigned_to_task.return_value = 1
    mock_comment_repo.create.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "create"
    )

    with pytest.raises(DatabaseError):
        await service.create(mock_comment, 1, 1)


def test_update_db_error(mocker):
    mock_comment_repo = mocker.Mock()
    mock_task_serv = mocker.Mock()

    mock_comment_2 = mocker.Mock()
    mock_comment_2.comment_id = 1
    mock_comment_2.user_id = 1

    mock_comment = mocker.Mock(spec=UpdateComment)
    mock_comment.content = "probando"

    service = CommentService(mock_comment_repo, mock_task_serv)

    mock_comment_repo.get_comment_by_id.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "update"
    )

    with pytest.raises(DatabaseError):
        service.update(mock_comment, 1, 1, 1)


def test_update_not_found_error(mocker):
    mock_comment_repo = mocker.Mock()
    mock_task_serv = mocker.Mock()

    mock_comment_2 = mocker.Mock()
    mock_comment_2.comment_id = 1
    mock_comment_2.user_id = 2

    mock_comment = mocker.Mock(spec=UpdateComment)
    mock_comment.content = "probando"

    service = CommentService(mock_comment_repo, mock_task_serv)

    mock_comment_repo.get_comment_by_id.return_value = None

    with pytest.raises(CommentNotFoundError):
        service.update(mock_comment, 1, 1, 1)

    mock_comment_repo.get_comment_by_id.return_value = mock_comment_2

    with pytest.raises(UserNotAuthorizedInCommentError):
        service.update(mock_comment, 1, 1, 1)


def test_delete_error(mocker):
    mock_comment_repo = mocker.Mock()
    mock_task_serv = mocker.Mock()

    mock_comment = mocker.Mock()
    mock_comment.comment_id = 1
    mock_comment.user_id = 1

    service = CommentService(mock_comment_repo, mock_task_serv)

    mock_comment_repo.get_comment_by_id.return_value = mock_comment
    mock_comment_repo.get_comment_by_id.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "update"
    )

    with pytest.raises(DatabaseError):
        service.delete(1, 1, 1)


def test_delete_not_found_or_authorized_error(mocker):
    mock_comment_repo = mocker.Mock()
    mock_task_serv = mocker.Mock()

    mock_comment = mocker.Mock()
    mock_comment.comment_id = 1
    mock_comment.user_id = 2

    service = CommentService(mock_comment_repo, mock_task_serv)

    mock_comment_repo.get_comment_by_id.return_value = None

    with pytest.raises(CommentNotFoundError):
        service.delete(1, 1, 1)

    mock_comment_repo.get_comment_by_id.return_value = mock_comment

    with pytest.raises(UserNotAuthorizedInCommentError):
        service.delete(1, 1, 1)
