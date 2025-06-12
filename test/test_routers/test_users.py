import pytest
from conftest import auth_headers, client, async_client, clean_redis


def test_get_user_me(client, auth_headers):
    response = client.get("/user/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"user_id": 1, "username": "mirko"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "username, password, email, status, respuesta",
    [
        (
            "mirko",
            "0000",
            "mirko@dev.com",
            406,
            "Ya existe un usuario con este Username",
        ),
        (
            "mirko_dev",
            "0000",
            "mirko@dev.com",
            406,
            "Ya existe un usuario con este Email",
        ),
        (
            "mirko_dev",
            "0000",
            "mirko@gmail.com",
            200,
            "Se ha creado un nuevo usuario con exito",
        ),
        (
            "moure_dev",
            "0000",
            "moure@gmail.com",
            200,
            "Se ha creado un nuevo usuario con exito",
        ),
    ],
)
async def test_create_user(async_client, username, password, email, status, respuesta):
    response = await async_client.post(
        "/user", json={"username": username, "email": email, "password": password}
    )
    assert response.status_code == status
    assert response.json() == {"detail": respuesta}


@pytest.mark.asyncio
async def test_get_users(async_client, clean_redis):
    response = await async_client.get("user")
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    for user in users:
        assert all(key in user for key in ["user_id", "username"])

    response = await async_client.get("user")
    assert response.status_code == 200


@pytest.fixture
def auth_headers2(client):
    response = client.post("/login", data={"username": "moure_dev", "password": "0000"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_update_user(async_client, auth_headers2):
    response = await async_client.patch(
        "/user/me",
        headers=auth_headers2,
        json={
            "username": "SrStamm",
            "email": "srstamm@gmail.com",
            "password": "cambiado",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"detail": "Se ha actualizado el usuario con exito"}


@pytest.mark.asyncio
async def test_delete_user(async_client, auth_headers, mocker):
    redis_client_mock = mocker.AsyncMock()
    redis_client_mock.delete.return_value = None

    response = await async_client.delete("/user/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"detail": "Se ha eliminado el usuario"}
