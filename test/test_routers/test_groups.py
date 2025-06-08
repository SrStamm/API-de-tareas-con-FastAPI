import pytest
from conftest import auth_headers, auth_headers2, test_user2, async_client, clean_redis
from models import db_models, exceptions, schemas
from sqlalchemy.exc import SQLAlchemyError
from api.v1.routers import group
from fastapi import Request
from core.permission import require_role

@pytest.mark.asyncio
async def test_create_group(async_client, auth_headers, test_user2):
    response = await async_client.post('/group', headers=auth_headers, json={'name':'probando'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    response = await async_client.post('/group', headers=auth_headers, json={'name':'test'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    hola = test_user2

@pytest.mark.asyncio
async def test_get_groups(async_client, auth_headers, clean_redis):
    response = await async_client.get('/group', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['group_id', 'name', 'users'])
    
    response = await async_client.get('/group', headers=auth_headers)
    assert response.status_code == 200

"""@pytest.mark.asyncio
async def test_get_groups_error(mocker):
    db_session_mock = mocker.Mock()
    mock_request = mocker.Mock(spec=Request)

    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await group.get_groups(request=mock_request, session=db_session_mock)"""

@pytest.mark.asyncio
async def test_get_groups_in_user(async_client, auth_headers):
    response = await async_client.get('/group/me', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['group_id', 'name', 'description', 'users'])

    response = await async_client.get('/group/me', headers=auth_headers)
    assert response.status_code == 200

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'group_id, user_id, status, respuesta', [
            (1, 2, 200,  'El usuario ha sido agregado al grupo'),
            (1, 100000, 404, 'User with user_id 100000 not found'),
            (1, 2, 400, 'User with user_id 2 is in Group with group_id 1'),
            (2, 2, 200, 'El usuario ha sido agregado al grupo')
        ]
)
async def test_append_user_group(async_client, auth_headers, group_id, user_id, status, respuesta):
    response = await async_client.post(f'/group/{group_id}/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail':respuesta}

@pytest.mark.asyncio
async def test_get_user_in_group(async_client, auth_headers):
    response = await async_client.get('/group/1/users', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['user_id', 'username', 'role'])
    
    response = await async_client.get('/group/1/users', headers=auth_headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_update_group(async_client, auth_headers):
    response = await async_client.patch('/group/1', headers=auth_headers, json={'name':'probando el update', 'description':'asfkasklfn'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha actualizado la informacion del grupo'}

@pytest.mark.asyncio
async def test_failed_update_group(async_client, auth_headers2):
    response = await async_client.patch('/group/1', headers=auth_headers2, json={'description':'probando otra vez'})
    assert response.status_code == 401 
    assert response.json() == {'detail': 'User with user_id 2 is Not Authorized'}

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'user_id, role, status, respuesta', [
            (2, db_models.Group_Role.ADMIN, 200, 'Se ha cambiado los permisos del usuario en el grupo'),
            (2, db_models.Group_Role.EDITOR, 200, 'Se ha cambiado los permisos del usuario en el grupo'),
            (3, db_models.Group_Role.ADMIN, 400, 'User with user_id 3 is not in Group with group_id 1')
        ]
)
async def test_update_user_group(async_client, auth_headers, user_id, role, status, respuesta):
    response = await async_client.patch(f'/group/1/{user_id}', headers=auth_headers, json={'role':role})
    assert response.status_code == status
    assert response.json() == {'detail':respuesta}

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'group_id, user_id, status, respuesta', [
            (1, 2, 200, 'El usuario ha sido eliminado al grupo'),
            (1, 2, 404, 'User with user_id 2 not found')
        ]
)
async def test_delete_user_group(async_client, auth_headers, group_id, user_id, status, respuesta):
    response = await async_client.delete(f'/group/{group_id}/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': respuesta}

@pytest.mark.asyncio
@pytest.mark.parametrize(
        'group_id, status, respuesta', [
            (1, 200, 'Se ha eliminado el grupo'),
            (100000, 404, 'Group with group_id 100000 not found')
        ]
)
async def test_delete_group(async_client, auth_headers, group_id, status, respuesta):
    response = await async_client.delete(f'/group/{group_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': respuesta}

"""@pytest.mark.asyncio
async def test_create_group_error(mocker):
    db_session_mock = mocker.Mock()
    user_mock = mocker.Mock()
    mock_request = mocker.Mock(spec=Request)

    db_session_mock.add.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await group.create_group(
            request=mock_request,
            new_group=schemas.CreateGroup(name='holaaa'),
            user=user_mock)

    db_session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_update_group_error(mocker):
    # Simula un usuario y una session
    mock_user = mocker.Mock(spec=db_models.User)
    mock_user.user_id = 1

    db_session_mock = mocker.Mock()

    mock_request = mocker.Mock(spec=Request)

    #Simula el grupo obtenido
    mock_group = mocker.Mock()
    mock_group.id = 1

    # Configura los mocks para las funciones auxiliares
    mock_dependency = mocker.Mock(return_value={"user": mock_user, "role": "admin"})

    mocker.patch('services.group_service.get_group_or_404', return_value=mock_group)

    # Simula un error al hacer commit
    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    # Llama al endpoint
    with pytest.raises(exceptions.DatabaseError):
        await group.update_group(
                request=mock_request,
                group_id=1,
                updated_group=schemas.UpdateGroup(name='adioss'),
            )
    
    # Verifica qeu se hizo rollback
    db_session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_delete_group_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    db_session_mock = mocker.Mock()

    mock_request = mocker.Mock(spec=Request)

    mock_group = mocker.Mock()
    mock_group.id = 1

    mock_dependency = mocker.Mock(return_value={"user": mock_user, "role": "admin"})

    mocker.patch('services.group_service.get_group_or_404', return_value=mock_group)

    db_session_mock.delete.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await group.delete_group(
            request=mock_request,
            group_id=1
    )
    
    db_session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_get_groups_in_user_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    db_session_mock = mocker.Mock()

    mock_request = mocker.Mock(spec=Request)

    mock_group = mocker.Mock()
    mock_group.id = 1

    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await group.get_groups_in_user(
            request=mock_request,
            user=mock_user,
            session=db_session_mock
        )

@pytest.mark.asyncio
async def test_append_user_group_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)

    db_session_mock = mocker.Mock()

    mock_request = mocker.Mock(spec=Request)

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = []

    mock_auth_data = {'user': mock_user, 'role': 'admin'}

    mocker.patch('services.group_service.GroupService.get_group_or_404', return_value=mock_group)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await group.append_user_group(
            request=mock_request,
            group_id=1,
            user_id=2,
            auth_data=mock_auth_data
        )
    
    db_session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_delete_user_group_database_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_delete_user = mocker.Mock(spec=db_models.User)
    mock_delete_user.user_id = 2
    db_session_mock = mocker.Mock()

    mock_request = mocker.Mock(spec=Request)

    mock_group = mocker.Mock()
    mock_group.group_id = 1
    mock_group.users = [mock_delete_user, mock_user]

    mock_auth_data = {'user': mock_user, 'role': 'admin'}

    mocker.patch('services.group_service.GroupService.get_group_or_404', return_value=mock_group)
    mocker.patch('api.v1.routers.group.get_user_or_404', return_value=mock_delete_user)
    mocker.patch('api.v1.routers.group.role_of_user_in_group', return_value='editor')

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await group.delete_user_group(
            request=mock_request,
            group_id=1,
            user_id=2,
            auth_data=mock_auth_data
        )

    db_session_mock.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_delete_user_group_NotAuthorized_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)

    mock_delete_user = mocker.Mock(spec=db_models.User)
    mock_delete_user.user_id = 2

    db_session_mock = mocker.Mock()

    mock_request = mocker.Mock(spec=Request)

    mock_group = mocker.Mock()
    mock_group.group_id = 1
    mock_group.users = [mock_delete_user, mock_user]

    mock_auth_data = {'user': mock_user, 'role': 'editor'}

    mocker.patch('services.group_service.GroupService.get_group_or_404', return_value=mock_group)
    mocker.patch('api.v1.routers.group.get_user_or_404', return_value=mock_delete_user)
    mocker.patch('api.v1.routers.group.role_of_user_in_group', return_value='editor')


    with pytest.raises(exceptions.NotAuthorized):
        await group.delete_user_group(
            request=mock_request,
            group_id=1,
            user_id=2,
            auth_data=mock_auth_data
        )

@pytest.mark.asyncio
async def test_update_user_group_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_user.user_id = 1

    mock_delete_user = mocker.Mock(spec=db_models.group_user)
    mock_delete_user.id = 2
    mock_delete_user.role = 'editor'

    db_session_mock = mocker.Mock()

    mock_request = mocker.Mock(spec=Request)

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = [mock_delete_user, mock_user]

    mock_auth_data = {'user': mock_user, 'role': 'admin'}

    mocker.patch('services.group_service.GroupService.get_group_or_404', return_value=mock_group)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await group.update_user_group(
            request=mock_request,
            group_id=1,
            user_id=mock_delete_user.id,
            update_role=schemas.UpdateRoleUser(role=db_models.Group_Role.ADMIN),
            auth_data=mock_auth_data
        )

    db_session_mock.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_in_group_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_delete_user = mocker.Mock(spec=db_models.User)
    mock_delete_user.id = 2

    mock_request = mocker.Mock(spec=Request)

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = [mock_delete_user, mock_user]

    mocker.patch('api.v1.routers.group.get_group_or_404', return_value=mock_group)

    db_session_mock = mocker.Mock()
    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await group.get_user_in_group(
            request=mock_request,
            group_id=1,
            user=mock_user,
            session=db_session_mock
        )

def test_require_role_error(mocker):
    # Usuario ficticio
    mock_user = mocker.Mock(spec=db_models.User)
    mock_user.user_id = 1

    # Simulación de sesión de DB
    db_session_mock = mocker.Mock()
    db_session_mock.exec.return_value.first.return_value = None  # Simula que no está en el grupo

    # Ejecutás la función real que queremos testear
    dependency = require_role(roles=['admin'])  # obtenés la dependencia real

    # Verificás que lanza el error esperado
    with pytest.raises(exceptions.UserNotInGroupError) as exc_info:
        dependency(group_id=10000, user=mock_user, session=db_session_mock)

    assert exc_info.value.user_id == mock_user.user_id
    assert exc_info.value.group_id == 10000"""