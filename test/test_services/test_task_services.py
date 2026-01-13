from models.db_models import Project_Permission, Task, User
from models.exceptions import (
    DatabaseError,
    TaskIsNotAssignedError,
    TaskNotFound,
    NotAuthorized,
)
from models.schemas import CreateTask, UpdateTask
from services.task_services import TaskService
from db.database import SQLAlchemyError
import pytest


def test_found_task_or_404_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.get_task_by_id.return_value = None

    with pytest.raises(TaskNotFound):
        service.found_task_or_404(1, 1)


@pytest.mark.asyncio
async def test_get_all_task_for_user_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.get_all_task_for_user.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "get_all_task_for_user"
    )

    with pytest.raises(DatabaseError):
        await service.get_all_task_for_user(1, 1, 1)


@pytest.mark.asyncio
async def test_get_all_task_for_project_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.get_all_task_to_project.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "get_all_task_for_project"
    )

    with pytest.raises(DatabaseError):
        await service.get_all_task_for_project(1, 1, 1, None, None)


@pytest.mark.asyncio
async def test_create_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    mock_new_task = mocker.Mock(spec=CreateTask)
    mock_new_task.assigned_user_id = None

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.create.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "create"
    )

    with pytest.raises(DatabaseError):
        await service.create(mock_new_task, 1)


async def test_delete_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    mock_new_task = mocker.Mock(spec=Task)

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.delete.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "delete"
    )
    mock_task_repo.found_task_or_404.return_value = mock_new_task

    with pytest.raises(DatabaseError):
        await service.delete(mock_new_task, 1)


async def test_update_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    mock_new_task = mocker.Mock(spec=UpdateTask)

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.update.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "update"
    )
    mock_task_repo.found_task_or_404.return_value = mock_new_task

    with pytest.raises(DatabaseError):
        await service.update_task(1, 1, mock_new_task, Project_Permission.ADMIN)
