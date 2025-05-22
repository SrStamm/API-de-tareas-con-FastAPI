import pytest
from models import schemas, db_models, exceptions
from api.v1.routers import group, project
from fastapi import Request
import core.utils as utils
import core.permission as permission

@pytest.mark.asyncio
async def test_get_group_or_404_error(mocker):
    request_mocker = mocker.Mock(spec=Request)
    
    session_mock = mocker.Mock()

    session_mock.exec.return_value.first.return_value = None

    with pytest.raises(exceptions.GroupNotFoundError):
        await group.update_group(
            request=request_mocker,
            group_id=1,
            updated_group=schemas.UpdateGroup(),
            session=session_mock
        )

@pytest.mark.asyncio
async def test_get_project_or_404_error(mocker):
    request_mocker = mocker.Mock(spec=Request)
    
    session_mock = mocker.Mock()

    session_mock.exec.return_value.first.return_value = None

    with pytest.raises(exceptions.ProjectNotFoundError):
        await project.update_project(
            request=request_mocker,
            group_id=1,
            project_id=1,
            updated_project=schemas.UpdateProject(),
            session=session_mock
        )

@pytest.mark.asyncio
async def test_role_of_user_in_group(mocker):
    request_mocker = mocker.Mock(spec=Request)
    
    session_mock = mocker.Mock()

    session_mock.exec.return_value.first.return_value = None

    mock_user = mocker.Mock(spec=db_models.User)
    mock_user.user_id = 1
    
    mock_group = mocker.Mock(spec=db_models.Group)
    mock_group.group_id = 1
    mock_group.users = [mock_user]

    mock_auth_data = {'user': mock_user, 'role': 'editor'}

    mocker.patch("api.v1.routers.group.get_group_or_404", return_value=mock_group)
    mocker.patch("api.v1.routers.group.get_user_or_404", return_value=mock_user)

    with pytest.raises(exceptions.UserNotInGroupError):
        await group.delete_user_group(
            request=request_mocker,
            group_id=1,
            user_id=1,
            auth_data=mock_auth_data,
            session=session_mock
        )

def test_found_project_for_task_or_404(mocker):
    session_mock = mocker.Mock()
    session_mock.exec.return_value.first.return_value = None

    with pytest.raises(exceptions.ProjectNotFoundError):
        utils.found_project_for_task_or_404(
            project_id=1,
            session=session_mock
        )

def test_permission_of_user_in_project(mocker):
    session_mock = mocker.Mock()
    session_mock.exec.return_value.first.return_value = None

    with pytest.raises(exceptions.UserNotInProjectError):
        permission.permission_of_user_in_project(
            user_id=1,
            project_id=1,
            session=session_mock
        )

def test_found_user_in_task_or_404(mocker):
    user_mock = mocker.Mock(spec=db_models.User)
    user_mock.user_id = 1

    task_mock = mocker.Mock(spec=db_models.Task)
    task_mock.task_id = 1
    task_mock.asigned = []
    
    session_mock = mocker.Mock()
    session_mock.exec.return_value.first.return_value = None
    
    with pytest.raises(exceptions.TaskErrorNotFound):
        utils.found_user_in_task_or_404(
            user_id=1,
            task_id=1,
            session=session_mock
        )

    session_mock.exec.return_value.first.return_value = task_mock
    session_mock.get.return_value = user_mock

    with pytest.raises(exceptions.TaskIsNotAssignedError):
        utils.found_user_in_task_or_404(
            user_id=1,
            task_id=1,
            session=session_mock
        )