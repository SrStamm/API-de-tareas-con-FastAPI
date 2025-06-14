import pytest
from conftest import (
    auth_headers,
    auth_headers2,
    test_create_group_init,
    async_client,
    clean_redis,
)
from models import db_models, schemas, exceptions
from api.v1.routers import project
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Request
from core.permission import require_permission


@pytest.mark.asyncio
async def test_get_projects(async_client, test_create_group_init, auth_headers):
    response = await async_client.get("/project/1", headers=auth_headers)
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    for project in projects:
        assert all(
            key in project
            for key in ["project_id", "group_id", "tittle", "description", "users"]
        )

    response = await async_client.get("/project/1", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_projects_iam(async_client, auth_headers):
    response = await async_client.get("/project/me", headers=auth_headers)
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    for project in projects:
        assert all(key in project for key in ["project_id", "group_id", "tittle"])

    response = await async_client.get("/project/me", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "group_id, status, detail",
    [
        (1, 200, "Se ha creado un nuevo proyecto de forma exitosa"),
        (1, 200, "Se ha creado un nuevo proyecto de forma exitosa"),
    ],
)
async def test_create_project(
    async_client, auth_headers, test_create_group_init, group_id, status, detail
):
    response = await async_client.post(
        f"/project/{group_id}",
        headers=auth_headers,
        json={"title": "creando un proyecto"},
    )
    assert response.status_code == status
    assert response.json() == {"detail": detail}


@pytest.mark.asyncio
async def test_update_project(async_client, auth_headers):
    response = await async_client.patch(
        "/project/1/1",
        headers=auth_headers,
        json={"title": "actualizando un proyecto", "description": "actualizando..."},
    )
    assert response.status_code == 200
    assert response.json() == {
        "detail": "Se ha actualizado la informacion del projecto"
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_id, status, detail",
    [
        (2, 200, "El usuario ha sido agregado al proyecto"),
        (2, 400, "User with user_id 2 is in project with project_id 1"),
        (3, 400, "User with user_id 3 is not in Group with group_id 1"),
        (100, 404, "User with user_id 100 not found"),
    ],
)
async def test_add_user_to_project(async_client, auth_headers, user_id, status, detail):
    response = await async_client.post(f"/project/1/1/{user_id}", headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {"detail": detail}


@pytest.mark.asyncio
async def test_get_user_in_project(async_client, auth_headers, clean_redis):
    response = await async_client.get("/project/1/1/users", headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ["user_id", "username", "permission"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "project_id, user_id, permission, status, detail",
    [
        (
            1,
            2,
            db_models.Project_Permission.READ,
            200,
            "Se ha cambiado los permisos del usuario en el proyecto",
        ),
        (
            1,
            100000,
            db_models.Project_Permission.ADMIN,
            400,
            "User with user_id 100000 is not in project with project_id 1",
        ),
    ],
)
async def test_update_user_permission_in_project(
    async_client, auth_headers, project_id, user_id, permission, status, detail
):
    response = await async_client.patch(
        f"/project/1/{project_id}/{user_id}",
        headers=auth_headers,
        json={"permission": permission},
    )
    assert response.status_code == status
    assert response.json() == {"detail": detail}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_id, status, detail",
    [
        (2, 200, "El usuario ha sido eliminado del proyecto"),
        (2, 400, "User with user_id 2 is not in project with project_id 1"),
        (3, 400, "User with user_id 3 is not in Group with group_id 1"),
    ],
)
async def test_remove_user_from_project(
    async_client, auth_headers, user_id, status, detail
):
    response = await async_client.delete(
        f"/project/1/1/{user_id}", headers=auth_headers
    )
    assert response.status_code == status
    assert response.json() == {"detail": detail}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "project_id, status, detail", [(2, 200, "Se ha eliminado el proyecto")]
)
async def test_delete_project(async_client, auth_headers, project_id, status, detail):
    response = await async_client.delete(
        f"/project/1/{project_id}", headers=auth_headers
    )
    assert response.status_code == status
    assert response.json() == {"detail": detail}
