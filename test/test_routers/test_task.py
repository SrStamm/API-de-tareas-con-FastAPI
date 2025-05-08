import pytest
from conftest import auth_headers, client, auth_headers2, test_create_project_init
from models import schemas, db_models, exceptions
from routers import task
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Request

@pytest.mark.parametrize(
        'project_id, datos, status, detail', [
            (1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[1]}, 200, 'Se ha creado una nueva tarea y asignado los usuarios con exito'),
            (1000000, {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[1, 2]}, 404, 'Project with project_id 1000000 not found'),
            (1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[3]}, 400, 'User with user_id 3 is not in project with project_id 1'),
            (1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[1000]}, 404, 'User with user_id 1000 not found'),
        ]
)
def test_create_task(client, auth_headers, test_create_project_init, project_id, datos, status, detail):
    response = client.post(f'/task/{project_id}', headers=auth_headers, json= datos)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_failed_create_task(client, auth_headers2):
    response = client.post('/task/1', headers=auth_headers2, json= {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[1]})
    assert response.status_code == 401
    assert response.json() == {'detail': 'User with user_id 2 is Not Authorized'}

def test_get_task(client, auth_headers):
    response = client.get('/task', headers=auth_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    for task in tasks:
        assert all(key in task for key in ['task_id', 'description', 'date_exp', 'state', 'project_id'])

def test_get_task_in_project(client, auth_headers):
    response = client.get('/task/1', headers=auth_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    for task in tasks:
        assert all(key in task for key in ['task_id', 'description', 'date_exp', 'state', 'asigned'])

@pytest.mark.parametrize(
        'project_id, task_id, datos, status, detail', [
            (1, 1, {'description':'probando el testing... otra vez', 'date_exp':'2025-12-12', 'state':db_models.State.EN_PROCESO, 'exclude_user_ids': [1]}, 200, 'Se ha actualizado la tarea'),
            (1000, 1, {'description':'probando el testing', 'date_exp':'2025-10-10'}, 404, 'Project with project_id 1000 not found'),
            (1, 1000, {'description':'probando el testing', 'date_exp':'2025-10-10'}, 404, 'Task with task_id 1000 is not in Project with project_id 1'),
            (1, 1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'exclude_user_ids':[100000]}, 400, 'Task with task_id 1 is NOT assigned to User with user_id 100000'),
            (1, 1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'append_user_ids':[3]}, 400, 'User with user_id 3 is not in project with project_id 1'),
            (1, 1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'append_user_ids':[100000]}, 404, 'User with user_id 100000 not found'),
        ]
)
def test_update_task(client, auth_headers, project_id, task_id, datos, status, detail):
    response = client.patch(f'/task/{project_id}/{task_id}', headers=auth_headers, json= datos)
    assert response.status_code == status
    assert response.json() == {'detail':detail}

@pytest.mark.parametrize(
        'task_id, status, detail', [
            (1, 200, 'Se ha eliminado la tarea'),
            (1, 404, 'Task with task_id 1 is not in Project with project_id 1')
        ]
)
def test_delete_task(client, auth_headers, task_id, status, detail):
    response = client.delete(f'/task/1/{task_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_failed_delete_task(client, auth_headers2):
    response = client.delete(f'/task/1/2', headers=auth_headers2)
    assert response.status_code == 401
    assert response.json() == {'detail': 'User with user_id 2 is Not Authorized'}

def test_get_users_for_task(client, auth_headers):
    response = client.get('/task/1/users', headers=auth_headers)
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    for user in users:
        assert all(key in user for key in ['user_id', 'username'])

def test_get_task_error(mocker):
    session_mock = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)
    mock_request = mocker.Mock(spec=Request)

    session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        task.get_task(
            request=mock_request,
            user=mock_user,
            session=session_mock)

def test_get_users_for_task_error(mocker):
    session_mock = mocker.Mock()
    mock_request = mocker.Mock(spec=Request)

    session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        task.get_users_for_task(
            request=mock_request,
            task_id=1,
            session=session_mock)

def test_get_task_in_project_error(mocker):
    session_mock = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)
    mock_request = mocker.Mock(spec=Request)

    session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        task.get_task_in_project(
            request=mock_request,
            project_id=1,
            user=mock_user,
            session=session_mock)

def test_create_task_error(mocker):
    session_mock = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)

    mock_request = mocker.Mock(spec=Request)

    session_mock.add.side_effect = SQLAlchemyError("Error en base de datos")

    mocker.patch('routers.task.found_project_for_task_or_404')
    mocker.patch('routers.task.is_admin_in_project')

    with pytest.raises(exceptions.DatabaseError):
        task.create_task(
            request=mock_request,
            new_task=schemas.CreateTask(description='crear', date_exp='2025-10-10', user_ids=[1]),
            project_id=1,
            user=mock_user,
            session=session_mock)
        
    session_mock.rollback.assert_called_once()

def test_update_task_error(mocker):
    session_mock = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)

    mock_request = mocker.Mock(spec=Request)

    session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    mocker.patch('routers.task.found_project_for_task_or_404')
    mocker.patch('routers.task.found_task_or_404')
    mocker.patch('routers.task.is_admin_in_project')

    with pytest.raises(exceptions.DatabaseError):
        task.update_task(
            request=mock_request,
            task_id=1,
            project_id=1,
            update_task=schemas.UpdateTask(description='crear'),
            user=mock_user,
            session=session_mock)
        
    session_mock.rollback.assert_called_once()

def test_delete_task_error(mocker):
    session_mock = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)

    session_mock.delete.side_effect = SQLAlchemyError("Error en base de datos")

    mocker.patch('routers.task.found_task_or_404')
    mocker.patch('routers.task.is_admin_in_project')

    with pytest.raises(exceptions.DatabaseError):
        task.delete_task(
            task_id=1,
            project_id=1,
            user=mock_user,
            session=session_mock)
        
    session_mock.rollback.assert_called_once()