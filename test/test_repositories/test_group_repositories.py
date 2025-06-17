from models.db_models import Group_Role
from repositories.group_repositories import GroupRepository
from models.exceptions import DatabaseError
from db.database import SQLAlchemyError
import pytest


def test_get_group_by_id_error(mocker):
    mock_session = mocker.Mock()

    repo = GroupRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_group_by_id(1)


def test_get_all_groups_error(mocker):
    mock_session = mocker.Mock()

    repo = GroupRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_all_groups(1, 1)


def test_user_for_group_error(mocker):
    mock_session = mocker.Mock()

    repo = GroupRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_users_for_group(1)


def test_get_groups_for_user_error(mocker):
    mock_session = mocker.Mock()

    repo = GroupRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_groups_for_user(1, 1, 1)


def test_get_role_for_user_in_group_error(mocker):
    mock_session = mocker.Mock()

    repo = GroupRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_role_for_user_in_group(1, 1)


"""
def test_create_error(mocker):
    mock_session = mocker.Mock()
    mock_group = mocker.Mock()
    mock_group.name = "test"
    mock_group.description = "test"

    repo = GroupRepository(mock_session)

    mock_session.add.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.create(mock_group, 1)
"""


def test_update_error(mocker):
    mock_session = mocker.Mock()
    mock_group = mocker.Mock()
    mock_update = mocker.Mock()

    repo = GroupRepository(mock_session)

    mock_session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.update(mock_group, mock_update)


def test_delete_error(mocker):
    mock_session = mocker.Mock()
    mock_group = mocker.Mock()

    repo = GroupRepository(mock_session)

    mock_session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.delete(mock_group)


def test_append_user_error(mocker):
    mock_session = mocker.Mock()
    user_mock = mocker.Mock()
    mock_group = mocker.Mock()

    repo = GroupRepository(mock_session)

    mocker.patch.object(GroupRepository, "get_group_by_id", return_value=mock_group)
    mock_session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.append_user(1, user_mock)


def test_remove_user_error(mocker):
    mock_session = mocker.Mock()
    user_mock = mocker.Mock()
    mock_group = mocker.Mock()

    repo = GroupRepository(mock_session)

    mocker.patch.object(GroupRepository, "get_group_by_id", return_value=mock_group)
    mock_session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.delete_user(1, user_mock)


def test_update_role_error(mocker):
    mock_session = mocker.Mock()
    user_mock = mocker.Mock()
    mock_group = mocker.Mock()

    repo = GroupRepository(mock_session)

    mocker.patch.object(GroupRepository, "get_group_by_id", return_value=mock_group)
    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.update_role(1, Group_Role.ADMIN)
