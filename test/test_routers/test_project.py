import pytest
from conftest import auth_headers, client, auth_headers2, test_create_group_init
from models import db_models, schemas, exceptions
from routers import project
from sqlalchemy.exc import SQLAlchemyError

def test_get_projects(client, test_create_group_init):
    response = client.get('/project/1')
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    for project in projects:
        assert all(key in project for key in ['project_id', 'group_id', 'tittle', 'description', 'users'])

def test_get_projects_iam(client, auth_headers):
    response = client.get('/project/1', headers=auth_headers)
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    for project in projects:
        assert all(key in project for key in ['project_id', 'group_id', 'tittle'])

@pytest.mark.parametrize(
        'group_id, status, detail', [
            (1, 200, 'Se ha creado un nuevo proyecto de forma exitosa'),
            (1, 200, 'Se ha creado un nuevo proyecto de forma exitosa'),
        ]
)
def test_create_project(client, auth_headers, test_create_group_init, group_id, status, detail):
    response = client.post(f'/project/{group_id}', headers=auth_headers, json={'title':'creando un proyecto'})
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_update_project(client, auth_headers):
    response = client.patch('/project/1/1', headers=auth_headers, json={'title':'actualizando un proyecto', 'description':'actualizando...'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Se ha actualizado la informacion del projecto'}

@pytest.mark.parametrize(
        'user_id, status, detail', [
            (2, 200, 'El usuario ha sido agregado al proyecto'),
            (2, 400, 'User with user_id 2 is in project with project_id 1'),
            (3, 400, 'User with user_id 3 is not in Group with group_id 1'),
            (100, 404, 'User with user_id 100 not found')
        ]
)
def test_add_user_to_project(client, auth_headers, user_id, status, detail):
    response = client.post(f'/project/1/1/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_get_user_in_project(client, auth_headers):
    response = client.get('/project/1/1/users', headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ['user_id', 'username', 'permission'])

@pytest.mark.parametrize(
        'project_id, user_id, permission, status, detail', [
            (1, 1, db_models.Project_Permission.ADMIN, 200, 'Se ha cambiado los permisos del usuario en el proyecto'),
            (1, 100000, db_models.Project_Permission.ADMIN, 400, 'User with user_id 100000 is not in project with project_id 1')
            ]
)
def test_update_user_permission_in_project(client, auth_headers, project_id, user_id, permission, status, detail):
    response = client.patch(f'/project/1/{project_id}/{user_id}', headers=auth_headers, json={'permission': permission})
    assert response.status_code == status
    assert response.json() == {'detail': detail}

@pytest.mark.parametrize(
        'user_id, status, detail', [
            (2, 200, 'El usuario ha sido eliminado del proyecto'),
            (2, 400, 'User with user_id 2 is not in project with project_id 1'),
            (3, 400, 'User with user_id 3 is not in Group with group_id 1')
        ]
)
def test_remove_user_from_project(client, auth_headers, user_id, status, detail):
    response = client.delete(f'/project/1/1/{user_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_failed_delete_project(client, auth_headers2):
    response = client.delete(f'/project/1/1', headers=auth_headers2)
    assert response.status_code == 401
    assert response.json() == {'detail': 'User with user_id 2 is Not Authorized'}

@pytest.mark.parametrize(
        'project_id, status, detail', [
            (2, 200, 'Se ha eliminado el proyecto')
        ]
)
def test_delete_project(client, auth_headers, project_id, status, detail):
    response = client.delete(f'/project/1/{project_id}', headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {'detail': detail}

def test_found_project_or_404_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_user.user_id = 1
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    db_session_mock.exec.return_value.first.return_value = None

    mocker.patch('routers.project.is_admin_in_project')

    with pytest.raises(exceptions.ProjectNotFoundError) as exc_info:
        project.update_project(
                group_id=1,
                project_id=1,
                updated_project=schemas.UpdateProject(title='error'),
                user=mock_user,
                session=db_session_mock
                )
    
    assert exc_info.value.project_id == 1

def test_get_projects_error(mocker):
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        project.get_projects(
                group_id=1,
                session=db_session_mock
            )

def test_get_projects_iam_error(mocker):
    db_session_mock = mocker.Mock()

    user_mock = mocker.Mock()
    user_mock.user_id = 1

    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        project.get_projects_iam(
                            user=user_mock,
                            session=db_session_mock
                )

def test_create_project_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    db_session_mock.add.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        project.create_project(
                new_project=schemas.CreateProject(title='hello world'),
                group_id=1,
                user=mock_user,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

def test_update_project_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1

    mocker.patch('routers.project.is_admin_in_project')
    mocker.patch('routers.project.found_project_or_404', return_value=mock_project)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        project.update_project(
                group_id=1,
                project_id = mock_project.id,
                updated_project=schemas.UpdateProject(title='GoodBye world'),
                user=mock_user,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

def test_delete_project_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1

    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1

    mocker.patch('routers.project.is_admin_in_project')
    mocker.patch('routers.project.found_project_or_404', return_value=mock_project)

    db_session_mock.delete.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        project.delete_project(
                group_id=1,
                project_id = mock_project.id,
                user=mock_user,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

def test_add_user_to_project_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_append_user = mocker.Mock(spec=db_models.User)
    mock_append_user.id = 2
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = [mock_append_user, mock_user]

    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1
    mock_project.users = []

    mocker.patch('routers.project.is_admin_in_project')
    mocker.patch('routers.project.found_project_or_404', return_value=mock_project)
    mocker.patch('routers.project.get_group_or_404', return_value=mock_group)
    mocker.patch('routers.project.get_group_or_404', return_value=mock_group)
    mocker.patch('routers.project.get_user_or_404', return_value=mock_append_user)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        project.add_user_to_project(
                group_id=1,
                user_id=2,
                project_id = 1,
                user=mock_user,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

def test_remove_user_from_project_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_append_user = mocker.Mock(spec=db_models.User)
    mock_append_user.id = 2
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = [mock_append_user, mock_user]

    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1
    mock_project.users = [mock_append_user, mock_user]

    mocker.patch('routers.project.is_admin_in_project')
    mocker.patch('routers.project.found_project_or_404', return_value=mock_project)
    mocker.patch('routers.project.get_group_or_404', return_value=mock_group)
    mocker.patch('routers.project.get_group_or_404', return_value=mock_group)
    mocker.patch('routers.project.get_user_or_404', return_value=mock_append_user)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        project.remove_user_from_project(
                group_id=1,
                project_id = 1,
                user_id=2,
                user=mock_user,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

def test_update_user_permission_in_project_error(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_append_user = mocker.Mock(spec=db_models.User)
    mock_append_user.id = 2
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1
    mock_group.users = [mock_append_user, mock_user]

    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1
    mock_project.users = [mock_append_user, mock_user]

    mocker.patch('routers.project.is_admin_in_project')
    mocker.patch('routers.project.found_project_or_404', return_value=mock_project)
    mocker.patch('routers.project.get_group_or_404', return_value=mock_group)
    mocker.patch('routers.project.get_group_or_404', return_value=mock_group)
    mocker.patch('routers.project.get_user_or_404', return_value=mock_append_user)

    db_session_mock.commit.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        project.update_user_permission_in_project(
                group_id=1,
                user_id=2,
                project_id = 1,
                update_role=schemas.UpdatePermissionUser(permission=db_models.Project_Permission.ADMIN),
                user=mock_user,
                session=db_session_mock
            )
    
    db_session_mock.rollback.assert_called_once()

def test_get_user_in_project_error(mocker):
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1
    
    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1
    
    mocker.patch('routers.project.found_project_or_404', return_value=mock_project)

    db_session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        project.get_user_in_project(
                group_id=1,
                project_id = 1,
                session=db_session_mock
            )

def test_get_user_in_project_not_results_error(mocker):
    db_session_mock = mocker.Mock()

    mock_group = mocker.Mock()
    mock_group.id = 1
    
    mock_project = mocker.Mock(spec=db_models.Project(title='hello world'))
    mock_project.id = 1
    
    db_session_mock.exec.return_value.all.return_value = None

    mocker.patch('routers.project.found_project_or_404', return_value=mock_project)

    with pytest.raises(exceptions.UsersNotFoundInProjectError):
        project.get_user_in_project(
                group_id=1,
                project_id = 1,
                session=db_session_mock
            )
