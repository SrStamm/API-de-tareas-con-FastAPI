from models.db_models import Group, Group_Role, User
from models.exceptions import (
    DatabaseError,
    GroupNotFoundError,
    NotAuthorized,
    UserNotFoundError,
    UserNotInGroupError,
)
from models.schemas import CreateGroup, UpdateGroup
from services.group_service import GroupService
from db.database import SQLAlchemyError
import pytest


def test_get_group_or_404(mocker):
    mock_group_repo = mocker.Mock()
    mock_user_repo = mocker.Mock()

    service = GroupService(mock_group_repo, mock_user_repo)

    mock_group_repo.get_group_by_id.return_value = None

    with pytest.raises(GroupNotFoundError):
        service.get_group_or_404(1000000)


@pytest.mark.asyncio
async def test_get_groups_error(mocker):
    mock_group_repo = mocker.Mock()
    mock_user_repo = mocker.Mock()

    service = GroupService(mock_group_repo, mock_user_repo)
    mock_group_repo.get_all_groups.side_effect = DatabaseError(
        SQLAlchemyError("DB error"), "get_groups"
    )

    with pytest.raises(DatabaseError):
        await service.get_groups_with_cache(10, 10)


@pytest.mark.asyncio
async def test_get_groups_where_user_in_error(mocker):
    mock_group_repo = mocker.Mock()
    mock_user_repo = mocker.Mock()

    mock_group_repo.get_groups_for_user.side_effect = DatabaseError(
        SQLAlchemyError("DB error"), "get_groups_where_user_in"
    )
    service = GroupService(mock_group_repo, mock_user_repo)

    with pytest.raises(DatabaseError):
        await service.get_groups_where_user_in(1, 10, 10)


@pytest.mark.asyncio
async def test_get_users_in_group_error(mocker):
    mock_group_repo = mocker.Mock()
    mock_user_repo = mocker.Mock()

    mock_group = mocker.Mock()

    mock_group_repo.get_users_for_group.side_effect = DatabaseError(
        SQLAlchemyError("DB error"), "get_users_in_group"
    )
    service = GroupService(mock_group_repo, mock_user_repo)

    mocker.patch.object(GroupService, "get_group_or_404", return_value=mock_group)

    with pytest.raises(DatabaseError):
        await service.get_users_in_group(1)


@pytest.mark.asyncio
async def test_create_group_error(mocker):
    mock_group_repo = mocker.Mock()
    mock_user_repo = mocker.Mock()
    group_mock = mocker.Mock(spec=CreateGroup)

    mock_group_repo.create.side_effect = DatabaseError(
        SQLAlchemyError("DB error"), "create"
    )
    service = GroupService(mock_group_repo, mock_user_repo)

    with pytest.raises(DatabaseError):
        await service.create_group(group_mock, 1)


@pytest.mark.asyncio
async def test_update_group_error(mocker):
    mock_group_repo = mocker.Mock()
    mock_user_repo = mocker.Mock()
    group_mock = mocker.Mock(spec=UpdateGroup)
    role_mock = Group_Role.ADMIN

    mocker.patch.object(GroupService, "get_group_or_404", return_value=role_mock)

    mock_group_repo.update.side_effect = DatabaseError(
        SQLAlchemyError("DB error"), "update"
    )

    service = GroupService(mock_group_repo, mock_user_repo)

    with pytest.raises(DatabaseError):
        await service.update_group(1, group_mock, role_mock, 1)

    with pytest.raises(NotAuthorized):
        await service.update_group(1, group_mock, "member", 1)


@pytest.mark.asyncio
async def test_delete_group_error(mocker):
    mock_group_repo = mocker.Mock()
    mock_user_repo = mocker.Mock()
    role_mock = Group_Role.ADMIN

    service = GroupService(mock_group_repo, mock_user_repo)

    mocker.patch.object(GroupService, "get_group_or_404", return_value=role_mock)

    mock_group_repo.delete.side_effect = DatabaseError(
        SQLAlchemyError("DB error"), "delete"
    )

    with pytest.raises(DatabaseError):
        await service.delete_group(group_id=1)


@pytest.mark.asyncio
async def test_append_user_group_error(mocker):
    mock_group_repo = mocker.Mock()
    mock_user_repo = mocker.Mock()

    mock_user = mocker.Mock()
    mock_user.user_id = 1
    mock_group = mocker.Mock(spec=Group)
    mock_group.users = [mock_user]

    mocker.patch.object(GroupService, "get_group_or_404", return_value=mock_group)

    mock_group_repo.append_user.side_effect = DatabaseError(
        SQLAlchemyError("DB error"), "append_user"
    )

    service = GroupService(mock_group_repo, mock_user_repo)

    with pytest.raises(DatabaseError):
        await service.append_user(1, 1)


@pytest.mark.asyncio
async def test_delete_user_error(mocker):
    mock_group_repo = mocker.Mock()
    mock_user_repo = mocker.Mock()

    mock_user = mocker.Mock(spec=User)
    mock_user.user_id = 1

    mock_group = mocker.Mock(spec=Group)
    mock_group.users = [mock_user]

    role_mock = Group_Role.ADMIN

    mocker.patch.object(GroupService, "get_group_or_404", return_value=mock_group)

    service = GroupService(mock_group_repo, mock_user_repo)

    with pytest.raises(UserNotFoundError):
        await service.delete_user(1, 1, 2, role_mock)

    mock_user_repo.get_user_by_id.return_value = mock_user

    mock_group_repo.delete_user.side_effect = DatabaseError(
        SQLAlchemyError("DB error"), "delete_user"
    )

    with pytest.raises(NotAuthorized):
        await service.delete_user(1, 1, 2, role_mock)

    mocker.patch.object(
        GroupService, "role_of_user_in_group", return_value=Group_Role.MEMBER
    )

    with pytest.raises(DatabaseError):
        await service.delete_user(1, 1, 2, role_mock)


@pytest.mark.asyncio
async def test_update_user_error(mocker):
    mock_group_repo = mocker.Mock()
    mock_user_repo = mocker.Mock()

    mock_user = mocker.Mock(spec=User)
    mock_user.user_id = 1
    mock_user.role = "admin"

    mock_group = mocker.Mock(spec=Group)

    mocker.patch.object(GroupService, "get_group_or_404", return_value=mock_group)

    mock_group.users = [mock_user]
    mocker.patch.object(GroupService, "role_of_user_in_group", return_value=mock_user)

    # Agrega el usuario al grupo
    mock_user_repo.get_user_by_id.return_value = mock_user
    mocker.patch.object(GroupService, "get_group_or_404", return_value=mock_group)

    mock_group_repo.update_role.side_effect = DatabaseError(
        SQLAlchemyError("DB error"), "role_of_user_in_group"
    )

    mocker.patch.object(
        GroupService, "role_of_user_in_group", return_value=Group_Role.MEMBER
    )

    service = GroupService(mock_group_repo, mock_user_repo)

    # Error de base de datos
    with pytest.raises(DatabaseError):
        await service.update_user_role(1, 1, Group_Role.EDITOR)


@pytest.mark.asyncio
async def test_update_user_user_not_found_error(mocker):
    mock_group_repo = mocker.Mock()
    mock_user_repo = mocker.Mock()

    mock_group = mocker.Mock(spec=Group)

    mocker.patch.object(GroupService, "get_group_or_404", return_value=mock_group)
    mocker.patch.object(GroupService, "role_of_user_in_group", return_value=None)

    service = GroupService(mock_group_repo, mock_user_repo)

    # Usuario no existe en el grupo
    with pytest.raises(UserNotInGroupError):
        await service.update_user_role(1, 1, Group_Role.EDITOR)
