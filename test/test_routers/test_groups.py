import pytest
from conftest import auth_headers, client, auth_headers2, test_user2
from models import db_models, exceptions, schemas
from sqlalchemy.exc import SQLAlchemyError
from routers import group

def test_create_group(client, auth_headers, test_user2):
    response = client.post('/group', headers=auth_headers, json={'name':'probando'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    response = client.post('/group', headers=auth_headers, json={'name':'test'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    hola = test_user2

def test_get_groups(client, auth_headers):
    response = client.get('/group', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['group_id', 'name', 'users'])

def test_get_groups_in_user(client, auth_headers):
    response = client.get('/group/me', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['group_id', 'name', 'description', 'users'])

@pytest.mark.parametrize(
        'group_id, user_id, status, respuesta', [
            (1, 2, 200,  'El usuario ha sido agregado al grupo'),
            (1, 100000, 404, 'User with user_id 100000 not found'),
            (1, 2, 400, 'User with user_id 2 is in Group with group_id 1'),
            (2, 2, 200, 'El usuario ha sido agregado al grupo')
        ]
)
def test_append_user_group(client, auth_headers, group_id, user_id, status, respuesta):
    response = client.post(f'/group/{group_id}/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail':respuesta}

def test_get_user_in_group(client, auth_headers):
    response = client.get('/group/1/users', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['user_id', 'username', 'role'])

def test_update_group(client, auth_headers):
    response = client.patch('/group/1', headers=auth_headers, json={'description':'probando otra vez', 'name':'probando el update'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha actualizado la informacion del grupo'}

def test_failed_update_group(client, auth_headers2):
    response = client.patch('/group/1', headers=auth_headers2, json={'description':'probando otra vez'})
    assert response.status_code == 401 
    assert response.json() == {'detail': 'User with user_id 2 is Not Authorized'}

@pytest.mark.parametrize(
        'user_id, role, status, respuesta', [
            (2, db_models.Group_Role.ADMIN, 200, 'Se ha cambiado los permisos del usuario en el grupo'),
            (2, db_models.Group_Role.MEMBER, 200, 'Se ha cambiado los permisos del usuario en el grupo'),
            (3, db_models.Group_Role.ADMIN, 400, 'User with user_id 3 is not in Group with group_id 1')
        ]
)
def test_update_user_group(client, auth_headers, user_id, role, status, respuesta):
    response = client.patch(f'/group/1/{user_id}', headers=auth_headers, json={'role':role})
    assert response.status_code == status
    assert response.json() == {'detail':respuesta}

@pytest.mark.parametrize(
        'group_id, user_id, status, respuesta', [
            (1, 2, 200, 'El usuario ha sido eliminado al grupo'),
            (1, 2, 404, 'User with user_id 2 not found')
        ]
)
def test_delete_user_group(client, auth_headers, group_id, user_id, status, respuesta):
    response = client.delete(f'/group/{group_id}/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': respuesta}

@pytest.mark.parametrize(
        'group_id, status, respuesta', [
            (1, 200, 'Se ha eliminado el grupo'),
            (100000, 404, 'Group with group_id 100000 not found')
        ]
)
def test_delete_group(client, auth_headers, group_id, status, respuesta):
    response = client.delete(f'/group/{group_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': respuesta}

def test_get_groups_error(mocker):
    db_session_mock = mocker.Mock()

    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        group.get_groups(session=db_session_mock)

def test_create_group_error(mocker):
    db_session_mock = mocker.Mock()

    db_session_mock.add.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        group.create_group(session=db_session_mock, new_group=schemas.CreateGroup(name='holaaa'))

    db_session_mock.rollback.assert_called_once()

def test_update_group_error(mocker):
    # Simula un usuario y una session
    mock_user = mocker.Mock(spec=db_models.User)
    db_session_mock = mocker.Mock()

    #Simula el grupo obtenido
    mock_group = mocker.Mock()
    mock_group.id = 1

    # Configura los mocks para las funciones auxiliares
    mocker.patch('routers.group.is_admin_in_group') # No lanza la excepcion
    mocker.patch('routers.group.get_group_or_404', return_value=mock_group)

    # Simula un error al hacer commit
    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    # Llama al endpoint
    with pytest.raises(exceptions.DatabaseError):
        group.update_group(
                group_id=1,
                updated_group=schemas.UpdateGroup(name='adioss'),
                user=mock_user,
                session=db_session_mock
            )
    
    # Verifica qeu se hizo rollback
    db_session_mock.rollback.assert_called_once()

def test_delete_group_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    mocker.patch('routers.group.is_admin_in_group') # No lanza la excepcion
    mocker.patch('routers.group.get_group_or_404', return_value=mock_group)

    db_session_mock.delete.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        group.delete_group(
                group_id=1,
                user=mock_user,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

def test_get_groups_in_user_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        group.get_groups_in_user(
                user=mock_user,
                session=db_session_mock
            )

def test_append_user_group_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_append_user = mocker.Mock(spec=db_models.User)
    mock_append_user.id = 2
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = []

    mocker.patch('routers.group.is_admin_in_group')
    mocker.patch('routers.group.get_group_or_404', return_value=mock_group)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        group.append_user_group(
                group_id=1,
                user_id=mock_append_user.id,
                user=mock_user,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

def test_delete_user_group_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_delete_user = mocker.Mock(spec=db_models.User)
    mock_delete_user.id = 2
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = [mock_delete_user, mock_user]

    mocker.patch('routers.group.is_admin_in_group')
    mocker.patch('routers.group.get_group_or_404', return_value=mock_group)
    mocker.patch('routers.group.get_user_or_404', return_value=mock_delete_user)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        group.delete_user_group(
                group_id=1,
                user_id=mock_delete_user.id,
                user=mock_user,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

def test_update_user_group_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_delete_user = mocker.Mock(spec=db_models.User)
    mock_delete_user.id = 2
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = [mock_delete_user, mock_user]

    mocker.patch('routers.group.is_admin_in_group')
    mocker.patch('routers.group.get_group_or_404', return_value=mock_group)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        group.update_user_group(
                group_id=1,
                user_id=mock_delete_user.id,
                update_role=schemas.UpdateRoleUser(role=db_models.Group_Role.ADMIN),
                user=mock_user,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

def test_get_user_in_group_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_delete_user = mocker.Mock(spec=db_models.User)
    mock_delete_user.id = 2
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = [mock_delete_user, mock_user]

    mocker.patch('routers.group.get_group_or_404', return_value=mock_group)

    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        group.get_user_in_group(
                group_id=1,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

def test_is_admin_in_group_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_user.user_id = 1
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    db_session_mock.exec.return_value.first.return_value = None

    with pytest.raises(exceptions.UserNotInGroupError) as exc_info:
        group.update_group(
                group_id=1,
                updated_group=schemas.UpdateGroup(name='error'),
                user=mock_user,
                session=db_session_mock
                )
        
    assert exc_info.value.user_id == mock_user.user_id
    assert exc_info.value.group_id == 1