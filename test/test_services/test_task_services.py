from models.db_models import Task, User
from models.exceptions import DatabaseError, TaskIsAssignedError, TaskNotFound
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


def test_found_user_assigned_to_task_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.get_task_is_asigned.return_value = None

    with pytest.raises(TaskIsAssignedError):
        service.found_user_assigned_to_task(1, 1)


@pytest.mark.asyncio
async def test_get_users_for_task_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.get_user_for_task.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.get_users_for_task(1, 1, 1)


@pytest.mark.asyncio
async def test_get_all_task_for_user_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.get_all_task_for_user.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.get_all_task_for_user(1, 1, 1)


@pytest.mark.asyncio
async def test_get_all_task_for_project_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.get_all_task_to_project.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.get_all_task_for_project(1, 1, 1, 1, None, None)


@pytest.mark.asyncio
async def test_create_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    mock_new_task = mocker.Mock(spec=CreateTask)
    mock_new_task.user_ids = []

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.create.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.create(mock_new_task, 1)


async def test_delete_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    mock_new_task = mocker.Mock(spec=Task)

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.delete.side_effect = SQLAlchemyError("db error")
    mock_task_repo.found_task_or_404.return_value = mock_new_task

    with pytest.raises(DatabaseError):
        await service.delete(mock_new_task, 1)


async def test_update_error(mocker):
    mock_task_repo = mocker.Mock()
    mock_user_ser = mocker.Mock()
    mock_proj_ser = mocker.Mock()

    mock_new_task = mocker.Mock(spec=UpdateTask)
    mock_user = mocker.Mock(spec=User)

    service = TaskService(mock_task_repo, mock_user_ser, mock_proj_ser)
    mock_task_repo.update.side_effect = SQLAlchemyError("db error")
    mock_task_repo.found_task_or_404.return_value = mock_new_task

    with pytest.raises(DatabaseError):
        await service.update_task(1, 1, mock_new_task, mock_user, "admin")
