from models.db_models import Project_Permission
from repositories.project_repositories import ProjectRepository
from models.exceptions import DatabaseError
from db.database import SQLAlchemyError
import pytest


def test_get_project_by_id_error(mocker):
    mock_session = mocker.Mock()

    repo = ProjectRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_project_by_id(1, 1)


def test_get_user_in_project_error(mocker):
    mock_session = mocker.Mock()

    repo = ProjectRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_user_in_project(1, 1)


def test_get_all_projects_by_user_error(mocker):
    mock_session = mocker.Mock()

    repo = ProjectRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_all_project_by_user(1, 1, 1)


def test_get_all_projects_error(mocker):
    mock_session = mocker.Mock()

    repo = ProjectRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_all_projects(1, 1, 1)


def test_get_users_in_project_error(mocker):
    mock_session = mocker.Mock()

    repo = ProjectRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_users_in_project(1, 1, 1)


def test_update_error(mocker):
    mock_session = mocker.Mock()
    mock_project = mocker.Mock()
    update_mock = mocker.Mock()

    repo = ProjectRepository(mock_session)

    mock_session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.update(mock_project, update_mock)


def test_delete_error(mocker):
    mock_session = mocker.Mock()
    mock_project = mocker.Mock()

    repo = ProjectRepository(mock_session)

    mock_session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.delete(mock_project)


def test_add_user_error(mocker):
    mock_session = mocker.Mock()

    repo = ProjectRepository(mock_session)

    mock_session.add.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.add_user(1, 1)


def test_remove_user_error(mocker):
    mock_session = mocker.Mock()
    mock_project = mocker.Mock()

    repo = ProjectRepository(mock_session)

    mock_session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.remove_user(mock_project)


def test_update_permissio_error(mocker):
    mock_session = mocker.Mock()
    mock_project = mocker.Mock()

    repo = ProjectRepository(mock_session)

    mock_session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.update_permission(mock_project, Project_Permission.ADMIN)
