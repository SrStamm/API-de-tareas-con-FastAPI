import pytest
from conftest import auth_headers, auth_headers2, test_user2, async_client, clean_redis
from models import db_models


@pytest.mark.asyncio
async def test_create_group(async_client, auth_headers, test_user2):
    response = await async_client.post(
        "/group", headers=auth_headers, json={"name": "probando"}
    )
    assert response.status_code == 200
    assert response.json() == {"detail": "Se ha creado un nuevo grupo de forma exitosa"}

    response = await async_client.post(
        "/group", headers=auth_headers, json={"name": "test"}
    )
    assert response.status_code == 200
    assert response.json() == {"detail": "Se ha creado un nuevo grupo de forma exitosa"}

    hola = test_user2


@pytest.mark.asyncio
async def test_get_groups(async_client, auth_headers, clean_redis):
    response = await async_client.get("/group", headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ["group_id", "name", "users"])

    response = await async_client.get("/group", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_groups_in_user(async_client, auth_headers):
    response = await async_client.get("/group/me", headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ["group_id", "name", "description", "users"])

    response = await async_client.get("/group/me", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "group_id, user_id, status, respuesta",
    [
        (1, 2, 200, "El usuario ha sido agregado al grupo"),
        (1, 100000, 404, "User with user_id 100000 not found"),
        (1, 2, 400, "User with user_id 2 is in Group with group_id 1"),
        (2, 2, 200, "El usuario ha sido agregado al grupo"),
    ],
)
async def test_append_user_group(
    async_client, auth_headers, group_id, user_id, status, respuesta
):
    response = await async_client.post(
        f"/group/{group_id}/{user_id}", headers=auth_headers
    )
    assert response.status_code == status
    assert response.json() == {"detail": respuesta}


@pytest.mark.asyncio
async def test_get_user_in_group(async_client, auth_headers):
    response = await async_client.get("/group/1/users", headers=auth_headers)
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)
    for group in groups:
        assert all(key in group for key in ["user_id", "username", "role"])

    response = await async_client.get("/group/1/users", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_group(async_client, auth_headers):
    response = await async_client.patch(
        "/group/1",
        headers=auth_headers,
        json={"name": "probando el update", "description": "asfkasklfn"},
    )
    assert response.status_code == 200
    assert response.json() == {"detail": "Se ha actualizado la informacion del grupo"}


@pytest.mark.asyncio
async def test_failed_update_group(async_client, auth_headers2):
    response = await async_client.patch(
        "/group/1", headers=auth_headers2, json={"description": "probando otra vez"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "User with user_id 2 is Not Authorized"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_id, role, status, respuesta",
    [
        (
            2,
            db_models.Group_Role.ADMIN,
            200,
            "Se ha cambiado los permisos del usuario en el grupo",
        ),
        (
            2,
            db_models.Group_Role.EDITOR,
            200,
            "Se ha cambiado los permisos del usuario en el grupo",
        ),
        (
            3,
            db_models.Group_Role.ADMIN,
            400,
            "User with user_id 3 is not in Group with group_id 1",
        ),
    ],
)
async def test_update_user_group(
    async_client, auth_headers, user_id, role, status, respuesta
):
    response = await async_client.patch(
        f"/group/1/{user_id}", headers=auth_headers, json={"role": role}
    )
    assert response.status_code == status
    assert response.json() == {"detail": respuesta}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "group_id, user_id, status, respuesta",
    [
        (1, 2, 200, "El usuario ha sido eliminado del grupo"),
        (1, 2, 404, "User with user_id 2 not found"),
    ],
)
async def test_delete_user_group(
    async_client, auth_headers, group_id, user_id, status, respuesta
):
    response = await async_client.delete(
        f"/group/{group_id}/{user_id}", headers=auth_headers
    )
    assert response.status_code == status
    assert response.json() == {"detail": respuesta}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "group_id, status, respuesta",
    [
        (1, 200, "Se ha eliminado el grupo"),
        (100000, 404, "Group with group_id 100000 not found"),
    ],
)
async def test_delete_group(async_client, auth_headers, group_id, status, respuesta):
    response = await async_client.delete(f"/group/{group_id}", headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {"detail": respuesta}
