from models.db_models import State, TypeOfLabel
from repositories.task_repositories import TaskRepository
from models.exceptions import DatabaseError
from db.database import SQLAlchemyError
import pytest


def test_get_task_by_id_error(mocker):
    mock_session = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_task_by_id(1, 1)


def test_get_task_is_assigned_error(mocker):
    mock_session = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_task_is_asigned(1, 1)


def test_get_labels_for_task_error(mocker):
    mock_session = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_labels_for_task(1)


def test_get_labels_for_task_by_label_error(mocker):
    mock_session = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_label_for_task_by_label(1, "BUG")


def test_get_all_tasks_for_user_error(mocker):
    mock_session = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_all_task_for_user(1, 1, 1, ["BUG"])


def test_get_all_tasks_to_project_error(mocker):
    mock_session = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_all_task_to_project(1, 1, 1, 1, [TypeOfLabel.API], [State.CANCELADO])


def test_get_user_for_task_error(mocker):
    mock_session = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.get_user_for_task(1, 1, 1)


def test_validate_in_task_error(mocker):
    mock_session = mocker.Mock()
    mock_user = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.exec.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.validate_in_task([mock_user], 1)


def test_update_error(mocker):
    mock_session = mocker.Mock()
    mock_project = mocker.Mock()
    update_mock = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.update(mock_project, update_mock)


def test_delete_error(mocker):
    mock_session = mocker.Mock()
    mock_project = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.delete(mock_project)


def test_add_user_error(mocker):
    mock_session = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.add.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.add_user(1, 1)


def test_remove_user_error(mocker):
    mock_session = mocker.Mock()
    mock_project = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.remove_user(mock_project)


def test_add_label_error(mocker):
    mock_session = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.add.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.add_label(1, "BUG")


def test_delete_label_error(mocker):
    mock_session = mocker.Mock()
    label_mock = mocker.Mock()

    repo = TaskRepository(mock_session)

    mock_session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(DatabaseError):
        repo.delete_label(label_mock)
