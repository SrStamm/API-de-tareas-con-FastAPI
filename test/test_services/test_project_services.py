from models.db_models import Group, Project, User
from models.exceptions import DatabaseError, ProjectNotFoundError, UserNotInProjectError
from models.schemas import CreateProject, UpdateProject
from services.group_service import GroupService
from services.project_services import ProjectService
from db.database import SQLAlchemyError
import pytest


def test_found_project_or_404_error(mocker):
    mock_project_repo = mocker.Mock()
    mock_group_serv = mocker.Mock()
    mock_user_serv = mocker.Mock()

    service = ProjectService(mock_project_repo, mock_group_serv, mock_user_serv)

    mock_project_repo.get_project_by_id.return_value = None

    with pytest.raises(ProjectNotFoundError):
        service.found_project_or_404(1, 1)


def test_found_user_in_project_or_404_error(mocker):
    mock_project_repo = mocker.Mock()
    mock_group_serv = mocker.Mock()
    mock_user_serv = mocker.Mock()

    service = ProjectService(mock_project_repo, mock_group_serv, mock_user_serv)

    mock_project_repo.get_user_in_project.return_value = None

    with pytest.raises(UserNotInProjectError):
        service.found_user_in_project_or_404(1, 1)


@pytest.mark.asyncio
async def test_get_projects_iam_error(mocker):
    mock_project_repo = mocker.Mock()
    mock_group_serv = mocker.Mock()
    mock_user_serv = mocker.Mock()

    service = ProjectService(mock_project_repo, mock_group_serv, mock_user_serv)

    mock_project_repo.get_all_project_by_user.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.get_projects_iam(1, 1, 1)


@pytest.mark.asyncio
async def test_get_all_projects_error(mocker):
    mock_project_repo = mocker.Mock()
    mock_group_serv = mocker.Mock()
    mock_user_serv = mocker.Mock()

    mock_group = mocker.Mock(spec=Group)

    service = ProjectService(mock_project_repo, mock_group_serv, mock_user_serv)

    mocker.patch.object(GroupService, "get_group_or_404", return_value=mock_group)

    mock_project_repo.get_all_projects.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.get_all_projects(1, 1, 1)


@pytest.mark.asyncio
async def test_get_users_in_project_error(mocker):
    mock_project_repo = mocker.Mock()
    mock_group_serv = mocker.Mock()
    mock_user_serv = mocker.Mock()

    mock_group = mocker.Mock(spec=Group)

    service = ProjectService(mock_project_repo, mock_group_serv, mock_user_serv)

    mocker.patch.object(GroupService, "get_group_or_404", return_value=mock_group)

    mock_project_repo.get_users_in_project.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.get_user_in_project(1, 1, 1, 1)


@pytest.mark.asyncio
async def test_create_project_error(mocker):
    mock_project_repo = mocker.Mock()
    mock_group_serv = mocker.Mock()
    mock_user_serv = mocker.Mock()

    mock_group = mocker.Mock(spec=Group)
    mock_project = mocker.Mock(spec=CreateProject)

    service = ProjectService(mock_project_repo, mock_group_serv, mock_user_serv)

    mocker.patch.object(GroupService, "get_group_or_404", return_value=mock_group)

    mock_project_repo.create.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.create_project(1, 1, mock_project)


@pytest.mark.asyncio
async def test_update_project_error(mocker):
    mock_project_repo = mocker.Mock()
    mock_group_serv = mocker.Mock()
    mock_user_serv = mocker.Mock()

    mock_project = mocker.Mock(spec=Project)
    mock_update_project = mocker.Mock(spec=UpdateProject)
    service = ProjectService(mock_project_repo, mock_group_serv, mock_user_serv)

    mocker.patch.object(
        ProjectService, "found_project_or_404", return_value=mock_project
    )

    mock_project_repo.update.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.update_project(1, 1, mock_update_project)


@pytest.mark.asyncio
async def test_delete_project_error(mocker):
    mock_project_repo = mocker.Mock()
    mock_group_serv = mocker.Mock()
    mock_user_serv = mocker.Mock()

    mock_project = mocker.Mock(spec=Project)
    mock_update_project = mocker.Mock(spec=UpdateProject)
    service = ProjectService(mock_project_repo, mock_group_serv, mock_user_serv)

    mocker.patch.object(
        ProjectService, "found_project_or_404", return_value=mock_project
    )

    mock_project_repo.delete.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.delete_project(1, 1)


@pytest.mark.asyncio
async def test_add_user_error(mocker):
    mock_project_repo = mocker.Mock()
    mock_group_serv = mocker.Mock()
    mock_user_serv = mocker.Mock()

    mock_user = mocker.Mock(spec=User)
    mock_user.user_id = 1

    mock_project = mocker.Mock(spec=Project)
    mock_project.project_id = 1
    mock_project.users = []

    mock_group = mocker.Mock(spec=Group)
    mock_group.users = [mock_user]

    service = ProjectService(mock_project_repo, mock_group_serv, mock_user_serv)

    mocker.patch.object(
        ProjectService, "found_project_or_404", return_value=mock_project
    )

    mocker.patch.object(GroupService, "get_group_or_404", return_value=mock_group)
    mock_user_serv.get_user_or_404.return_value = mock_user
    mock_group_serv.get_group_or_404.return_value = mock_group
    mock_project_repo.add_user.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.add_user(1, 1, 1)


@pytest.mark.asyncio
async def test_remove_user_error(mocker):
    mock_project_repo = mocker.Mock()
    mock_group_serv = mocker.Mock()
    mock_user_serv = mocker.Mock()

    mock_user = mocker.Mock(spec=User)
    mock_user.user_id = 1

    mock_project = mocker.Mock(spec=Project)
    mock_project.project_id = 1
    mock_project.users = [mock_user]

    mock_group = mocker.Mock(spec=Group)
    mock_group.users = [mock_user]

    mock_project_user = mocker.Mock()

    service = ProjectService(mock_project_repo, mock_group_serv, mock_user_serv)

    mocker.patch.object(
        ProjectService, "found_project_or_404", return_value=mock_project
    )

    mocker.patch.object(GroupService, "get_group_or_404", return_value=mock_group)
    mock_user_serv.get_user_or_404.return_value = mock_user
    mock_group_serv.get_group_or_404.return_value = mock_group
    mock_project_repo.get_users_in_project.return_value = mock_project_user
    mock_project_repo.remove_user.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.remove_user(1, 1, 1)


@pytest.mark.asyncio
async def test_update_user_permission_in_project_error(mocker):
    mock_project_repo = mocker.Mock()
    mock_group_serv = mocker.Mock()
    mock_user_serv = mocker.Mock()

    mock_user = mocker.Mock(spec=User)
    mock_user.user_id = 1

    mock_project = mocker.Mock(spec=Project)
    mock_project.project_id = 1
    mock_project.users = [mock_user]

    mock_group = mocker.Mock(spec=Group)
    mock_group.users = [mock_user]

    mock_project_user = mocker.Mock()

    service = ProjectService(mock_project_repo, mock_group_serv, mock_user_serv)

    mocker.patch.object(
        ProjectService, "found_project_or_404", return_value=mock_project
    )

    mock_project_repo.get_users_in_project.return_value = mock_project_user

    mock_project_repo.update_permission.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        await service.update_user_permission_in_project(1, 1, 1, "write")
