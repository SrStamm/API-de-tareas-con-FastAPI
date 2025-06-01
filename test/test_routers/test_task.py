import pytest
from conftest import auth_headers, auth_headers2, test_create_project_init_for_tasks, async_client, clean_redis
from models import schemas, db_models, exceptions
from api.v1.routers import task
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Request

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'project_id, datos, status, detail', [
            (1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[1]}, 200, 'A new task has been created and users have been successusfully assigned'),
            (1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[3]}, 400, 'User with user_id 3 is not in project with project_id 1'),
            (1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[1000]}, 404, 'User with user_id 1000 not found'),
        ]
)
async def test_create_task(async_client, auth_headers, test_create_project_init_for_tasks, project_id, datos, status, detail):
    response = await async_client.post(f'/task/{project_id}', headers=auth_headers, json= datos)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

@pytest.mark.asyncio
async def test_failed_create_task(async_client, auth_headers2):
    response = await async_client.post('/task/1', headers=auth_headers2, json= {'description':'probando el testing', 'date_exp':'2025-10-10', 'user_ids':[1]})
    assert response.status_code == 401
    assert response.json() == {'detail': 'User with user_id 2 is Not Authorized'}

@pytest.mark.asyncio
async def test_get_task(async_client, auth_headers, clean_redis):
    response = await async_client.get('/task', headers=auth_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    for task in tasks:
        assert all(key in task for key in ['task_id', 'description', 'date_exp', 'state', 'project_id'])
    
    response = await async_client.get('/task', headers=auth_headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_task_in_project(async_client, auth_headers, clean_redis):
    response = await async_client.get('/task/1', headers=auth_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    for task in tasks:
        assert all(key in task for key in ['task_id', 'description', 'date_exp', 'state', 'asigned'])

    response = await async_client.get('/task/1', headers=auth_headers)
    assert response.status_code == 200

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'project_id, task_id, datos, status, detail', [
            (1, 1, {'description':'probando el testing... otra vez', 'date_exp':'2025-12-12', 'state':db_models.State.EN_PROCESO, 'exclude_user_ids': [1], 'append_user_ids':[2]}, 200, 'A new task has been created and users have been successfully assigned'),
            (1000, 1, {'description':'probando el testing', 'date_exp':'2025-10-10'}, 404, 'Project with project_id 1000 not found'),
            (1, 1000, {'description':'probando el testing', 'date_exp':'2025-10-10'}, 404, 'Task with task_id 1000 is not in Project with project_id 1'),
            (1, 1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'exclude_user_ids':[100000]}, 400, 'Task with task_id 1 is NOT assigned to User with user_id 100000'),
            (1, 1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'append_user_ids':[3]}, 400, 'User with user_id 3 is not in project with project_id 1'),
            (1, 1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'append_user_ids':[2]}, 400, 'Task with task_id 1 is assigned to User with user_id 2'),
            (1, 1, {'description':'probando el testing', 'date_exp':'2025-10-10', 'append_user_ids':[100000]}, 404, 'User with user_id 100000 not found'),
        ]
)
async def test_update_task(async_client, auth_headers, project_id, task_id, datos, status, detail):
    response = await async_client.patch(f'/task/{project_id}/{task_id}', headers=auth_headers, json= datos)
    assert response.status_code == status
    assert response.json() == {'detail':detail}

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'task_id, status, detail', [
            (1, 200, 'Task successfully deleted'),
            (1, 404, 'Task with task_id 1 is not in Project with project_id 1')
        ]
)
async def test_delete_task(async_client, auth_headers, task_id, status, detail):
    response = await async_client.delete(f'/task/1/{task_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

@pytest.mark.asyncio
async def test_failed_delete_task(async_client, auth_headers2):
    response = await async_client.delete(f'/task/1/2', headers=auth_headers2)
    assert response.status_code == 401
    assert response.json() == {'detail': 'User with user_id 2 is Not Authorized'}

@pytest.mark.asyncio
async def test_get_users_for_task(async_client, auth_headers, clean_redis):
    response = await async_client.get('/task/1/users', headers=auth_headers)
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    for user in users:
        assert all(key in user for key in ['user_id', 'username'])

    response = await async_client.get('/task/1/users', headers=auth_headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_task_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_user.user_id = 1

    mock_request = mocker.Mock(spec=Request)

    session_mock = mocker.Mock()
    session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await task.get_task(
            request=mock_request,
            user=mock_user,
            session=session_mock)

@pytest.mark.asyncio
async def test_get_users_for_task_error(mocker):
    session_mock = mocker.Mock()
    mock_request = mocker.Mock(spec=Request)

    session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await task.get_users_for_task(
            request=mock_request,
            task_id=1,
            session=session_mock)

@pytest.mark.asyncio
async def test_get_task_in_project_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_user.user_id = 1

    mock_request = mocker.Mock(spec=Request)

    session_mock = mocker.Mock()
    session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await task.get_task_in_project(
            request=mock_request,
            project_id=1,
            user= mock_user,
            session=session_mock)

@pytest.mark.asyncio
async def test_create_task_error(mocker): 
    session_mock = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)

    mock_request = mocker.Mock(spec=Request)

    session_mock.add.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await task.create_task(
            request=mock_request,
            new_task=schemas.CreateTask(description='crear', date_exp='2025-10-10', user_ids=[1]),
            project_id=1,
            session=session_mock)
        
    session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_create_task_Value_error(mocker): 
    session_mock = mocker.Mock()

    mock_request = mocker.Mock(spec=Request)

    with pytest.raises(ValueError):
        await task.create_task(
            request=mock_request,
            new_task=schemas.CreateTask(description='crear', date_exp='2022-10-10'),
            project_id=1,
            session=session_mock)

@pytest.mark.asyncio
async def test_update_task_error(mocker):
    session_mock = mocker.Mock()

    mock_user = mocker.Mock(spec=db_models.User)
    mock_user.user_id = 123

    mock_request = mocker.Mock(spec=Request)

    # Configura el error de commit
    session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    # Patches necesarios
    mock_db_task = mocker.Mock(spec=db_models.Task)
    
    mocker.patch('api.v1.routers.task.found_task_or_404', return_value=mock_db_task)

    mock_auth_data = {'user': mock_user, 'permission': 'write'}

    with pytest.raises(exceptions.DatabaseError):
        await task.update_task(
                request=mock_request,
                task_id=1,
                project_id=1,
                update_task=schemas.UpdateTask(description='crear'),
                session=session_mock,
                auth_data=mock_auth_data
            )

    session_mock.commit.assert_called_once()

@pytest.mark.asyncio
async def test_update_task_error_NotAuthorized(mocker):
    session_mock = mocker.Mock()

    mock_user = mocker.Mock(spec=db_models.User)
    mock_user.user_id = 123

    mock_request = mocker.Mock(spec=Request)

    # Patches necesarios
    mock_db_task = mocker.Mock(spec=db_models.Task)
    
    mocker.patch('api.v1.routers.task.found_task_or_404', return_value=mock_db_task)

    mock_auth_data = {'user': mock_user, 'permission': 'write'}

    with pytest.raises(exceptions.NotAuthorized):
        await task.update_task(
            request=mock_request,
            task_id=1,
            project_id=1,
            update_task=schemas.UpdateTask(description='crear', exclude_user_ids=[3]),
            session=session_mock,
            auth_data=mock_auth_data
        )
    
    with pytest.raises(exceptions.NotAuthorized):
        await task.update_task(
            request=mock_request,
            task_id=1,
            project_id=1,
            update_task=schemas.UpdateTask(description='crear', append_user_ids=[3]),
            session=session_mock,
            auth_data=mock_auth_data
        )

def test_update_task_Value_error(mocker): 
    session_mock = mocker.Mock()

    mock_request = mocker.Mock(spec=Request)

    with pytest.raises(ValueError):
        task.update_task(
            request=mock_request,
            task_id=1,
            project_id=1,
            update_task=schemas.UpdateTask(description='crear', date_exp='2022-10-10'),
            session=session_mock)

@pytest.mark.asyncio
async def test_delete_task_error(mocker):
    session_mock = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)

    session_mock.delete.side_effect = SQLAlchemyError("Error en base de datos")

    mocker.patch('api.v1.routers.task.found_task_or_404')

    with pytest.raises(exceptions.DatabaseError):
        await task.delete_task(
            task_id=1,
            project_id=1,
            session=session_mock)
        
    session_mock.rollback.assert_called_once()