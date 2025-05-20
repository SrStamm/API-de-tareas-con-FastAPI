import pytest
from conftest import auth_headers, auth_headers2, test_create_group_init, async_client, clean_redis
from models import db_models, schemas, exceptions
from api.v1.routers import project
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Request
from core.permission import require_permission

@pytest.mark.asyncio
async def test_get_projects(async_client, test_create_group_init, auth_headers):
    response = await async_client.get('/project/1', headers=auth_headers)
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    for project in projects:
        assert all(key in project for key in ['project_id', 'group_id', 'tittle', 'description', 'users'])

    response = await async_client.get('/project/1', headers=auth_headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_projects_iam(async_client, auth_headers):
    response = await async_client.get('/project/me', headers=auth_headers)
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    for project in projects:
        assert all(key in project for key in ['project_id', 'group_id', 'tittle'])

    response = await async_client.get('/project/me', headers=auth_headers)
    assert response.status_code == 200

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'group_id, status, detail', [
            (1, 200, 'Se ha creado un nuevo proyecto de forma exitosa'),
            (1, 200, 'Se ha creado un nuevo proyecto de forma exitosa'),
        ]
)
async def test_create_project(async_client, auth_headers, test_create_group_init, group_id, status, detail):
    response = await async_client.post(f'/project/{group_id}', headers=auth_headers, json={'title':'creando un proyecto'})
    assert response.status_code == status
    assert response.json() == {'detail': detail}

@pytest.mark.asyncio
async def test_update_project(async_client, auth_headers):
    response = await async_client.patch('/project/1/1', headers=auth_headers, json={'title':'actualizando un proyecto', 'description':'actualizando...'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha actualizado la informacion del projecto'}

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'user_id, status, detail', [
            (2, 200, 'El usuario ha sido agregado al proyecto'),
            (2, 400, 'User with user_id 2 is in project with project_id 1'),
            (3, 400, 'User with user_id 3 is not in Group with group_id 1'),
            (100, 404, 'User with user_id 100 not found')
        ]
)
async def test_add_user_to_project(async_client, auth_headers, user_id, status, detail):
    response = await async_client.post(f'/project/1/1/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

@pytest.mark.asyncio
async def test_get_user_in_project(async_client, auth_headers, clean_redis):
    response = await async_client.get('/project/1/1/users', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['user_id', 'username', 'permission'])

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'project_id, user_id, permission, status, detail', [
            (1, 2, db_models.Project_Permission.READ, 200, 'Se ha cambiado los permisos del usuario en el proyecto'),
            (1, 100000, db_models.Project_Permission.ADMIN, 400, 'User with user_id 100000 is not in project with project_id 1')
            ]
)
async def test_update_user_permission_in_project(async_client, auth_headers, project_id, user_id, permission, status, detail):
    response = await async_client.patch(f'/project/1/{project_id}/{user_id}', headers=auth_headers, json={'permission': permission})
    assert response.status_code == status
    assert response.json() == {'detail': detail}

@pytest.mark.asyncio
async def test_update_project_error(async_client, auth_headers2):
    response = await async_client.patch('/project/1/1', headers=auth_headers2, json={'description':'probando otra vez', 'name':'probando el update'})
    assert response.status_code == 401
    assert response.json() == {'detail': 'User with user_id 2 is Not Authorized'}

@pytest.mark.asyncio
async def test_update_project_error_database(mocker):
    mock_user = mocker.Mock(spec=db_models.User)

    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    mock_request = mocker.Mock(spec=Request)

    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1

    mock_auth_data = {'user': mock_user, 'permission': 'write'}

    mocker.patch('api.v1.routers.project.found_project_or_404', return_value=mock_project)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await project.update_project(
                request=mock_request,
                group_id=1,
                project_id = 1,
                updated_project=schemas.UpdateProject(title='Hola'),
                auth_data=mock_auth_data,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_failed_delete_project(async_client, auth_headers2):
    response = await async_client.delete(f'/project/1/1', headers=auth_headers2)
    assert response.status_code == 401
    assert response.json() == {'detail': 'User with user_id 2 is Not Authorized'}

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'user_id, status, detail', [
            (2, 200, 'El usuario ha sido eliminado del proyecto'),
            (2, 400, 'User with user_id 2 is not in project with project_id 1'),
            (3, 400, 'User with user_id 3 is not in Group with group_id 1')
        ]
)
async def test_remove_user_from_project(async_client, auth_headers, user_id, status, detail):
    response = await async_client.delete(f'/project/1/1/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'project_id, status, detail', [
            (2, 200, 'Se ha eliminado el proyecto')
        ]
)
async def test_delete_project(async_client, auth_headers, project_id, status, detail):
    response = await async_client.delete(f'/project/1/{project_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_require_permission(mocker):
    # Usuario ficticio
    mock_user = mocker.Mock(spec=db_models.User)
    mock_user.user_id = 1

    # Simulación de sesión de DB
    db_session_mock = mocker.Mock()
    db_session_mock.exec.return_value.first.return_value = None  # Simula que no está en el grupo

    # Ejecutás la función real que queremos testear
    dependency = require_permission(permissions=['admin'])  # obtenés la dependencia real

    # Verificás que lanza el error esperado
    with pytest.raises(exceptions.UserNotInProjectError) as exc_info:
        dependency(project_id=10000, user=mock_user, session=db_session_mock)

    assert exc_info.value.user_id == mock_user.user_id
    assert exc_info.value.project_id == 10000

@pytest.mark.asyncio
async def test_get_projects_error(mocker):
    db_session_mock = mocker.Mock()

    mock_request = mocker.Mock(spec=Request)

    mock_group = mocker.Mock()
    mock_group.id = 1

    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await project.get_projects(
                request=mock_request,
                group_id=1,
                session=db_session_mock
            )

@pytest.mark.asyncio
async def test_get_projects_iam_error(mocker):
    db_session_mock = mocker.Mock()

    user_mock = mocker.Mock()
    user_mock.user_id = 1

    mock_request = mocker.Mock(spec=Request)

    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await project.get_projects_iam(
            request=mock_request,
            user=user_mock,
            session=db_session_mock
            )

@pytest.mark.asyncio
async def test_create_project_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    mock_request = mocker.Mock(spec=Request)
    mock_auth_data = {'user': mock_user, 'permission': 'admin'}

    db_session_mock.add.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await project.create_project(
                request=mock_request,
                new_project=schemas.CreateProject(title='hello world'),
                group_id=1,
                session=db_session_mock,
                auth_data=mock_auth_data
            )
    
    db_session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_delete_project_error(mocker):
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    mock_request = mocker.Mock(spec=Request)

    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1

    mocker.patch('api.v1.routers.project.found_project_or_404', return_value=mock_project)

    db_session_mock.delete.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await project.delete_project(
                request=mock_request,
                group_id=1,
                project_id = mock_project.id,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_add_user_to_project_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_append_user = mocker.Mock(spec=db_models.User)
    mock_append_user.id = 2
    db_session_mock = mocker.Mock()

    mock_request = mocker.Mock(spec=Request)

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = [mock_append_user, mock_user]

    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1
    mock_project.users = []

    mocker.patch('api.v1.routers.project.found_project_or_404', return_value=mock_project)
    mocker.patch('api.v1.routers.project.get_group_or_404', return_value=mock_group)
    mocker.patch('api.v1.routers.project.get_user_or_404', return_value=mock_append_user)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await project.add_user_to_project(
                request=mock_request,
                group_id=1,
                user_id=2,
                project_id = 1,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_remove_user_from_project_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_append_user = mocker.Mock(spec=db_models.User)
    mock_append_user.id = 2
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = [mock_append_user, mock_user]

    mock_request = mocker.Mock(spec=Request)

    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1
    mock_project.users = [mock_append_user, mock_user]

    mocker.patch('api.v1.routers.project.found_project_or_404', return_value=mock_project)
    mocker.patch('api.v1.routers.project.get_group_or_404', return_value=mock_group)
    mocker.patch('api.v1.routers.project.get_user_or_404', return_value=mock_append_user)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await project.remove_user_from_project(
                request=mock_request,
                group_id=1,
                project_id = 1,
                user_id=2,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_update_user_permission_in_project_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_append_user = mocker.Mock(spec=db_models.User)
    mock_append_user.id = 2
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = [mock_append_user, mock_user]

    mock_request = mocker.Mock(spec=Request)

    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1
    mock_project.users = [mock_append_user, mock_user]

    mocker.patch('api.v1.routers.project.found_project_or_404', return_value=mock_project)
    mocker.patch('api.v1.routers.project.get_group_or_404', return_value=mock_group)
    mocker.patch('api.v1.routers.project.get_user_or_404', return_value=mock_append_user)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await project.update_user_permission_in_project(
                request=mock_request,
                group_id=1,
                user_id=2,
                project_id = 1,
                update_role=schemas.UpdatePermissionUser(permission=db_models.Project_Permission.ADMIN),
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_in_project_error(mocker):
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    mock_request = mocker.Mock(spec=Request)
    
    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1
    
    mocker.patch('api.v1.routers.project.found_project_or_404', return_value=mock_project)

    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await project.get_user_in_project(
                request=mock_request,
                group_id=1,
                project_id = 1,
                session=db_session_mock
            )

@pytest.mark.asyncio
async def test_get_user_in_project_not_results_error(mocker):
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    mock_request = mocker.Mock(spec=Request)
    
    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1
    
    db_session_mock.exec.return_value.all.return_value = None

    mocker.patch('api.v1.routers.project.found_project_or_404', return_value=mock_project)

    with pytest.raises(exceptions.UsersNotFoundInProjectError):
        await project.get_user_in_project(
                request=mock_request,
                group_id=1,
                project_id = 1,
                session=db_session_mock
            )