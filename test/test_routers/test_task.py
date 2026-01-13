import pytest
from conftest import (
    auth_headers,
    auth_headers2,
    test_create_project_init_for_tasks,
    async_client,
    clean_redis,
)
from models import db_models
from api.v1.routers import task


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "project_id, datos, status, detail",
    [
        (
            1,
            {
                "title": "probando",
                "description": "probando el testing",
                "date_exp": "2030-10-10",
                "assigned_user_id": 1,
                "label": ["bug"],
            },
            200,
            {
                "date_exp": "2030-10-10T00:00:00",
                "description": "probando el testing",
                "project_id": 1,
                "state": "sin empezar",
                "task_id": 1,
                "title": "probando",
                "assigned_user_id": 1,
            },
        ),
        (
            1,
            {
                "title": "probando",
                "description": "probando el testing",
                "date_exp": "2030-10-10",
                "assigned_user_id": 3,
            },
            400,
            {
                "detail": "User with user_id 3 is not in project with project_id 1",
            },
        ),
        (
            1,
            {
                "title": "probando",
                "description": "probando el testing",
                "date_exp": "2030-10-10",
                "assigned_user_id": 1000,
            },
            404,
            {
                "detail": "User with user_id 1000 not found",
            },
        ),
    ],
)
async def test_create_task(
    async_client,
    auth_headers,
    test_create_project_init_for_tasks,
    project_id,
    datos,
    status,
    detail,
):
    response = await async_client.post(
        f"/task/{project_id}", headers=auth_headers, json=datos
    )
    assert response.status_code == status
    assert response.json() == detail


@pytest.mark.asyncio
async def test_get_task(async_client, auth_headers, clean_redis):
    params = [
        ("labels", db_models.TypeOfLabel.BUG.value),
        ("state", db_models.State.SIN_EMPEZAR.value),
    ]
    response = await async_client.get("/task", headers=auth_headers, params=params)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    for task in tasks:
        assert all(
            key in task
            for key in [
                "task_id",
                "title",
                "description",
                "date_exp",
                "state",
                "project_id",
                "task_label_links",
            ]
        )

    response = await async_client.get("/task", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_task_in_project(async_client, auth_headers, clean_redis):
    params = [
        ("labels", db_models.TypeOfLabel.BUG.value),
        ("state", db_models.State.SIN_EMPEZAR.value),
    ]
    response = await async_client.get("/task/1", headers=auth_headers, params=params)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    for task in tasks:
        assert all(
            key in task
            for key in [
                "task_id",
                "title",
                "description",
                "date_exp",
                "state",
                "assigned_user",
                "task_label_links",
            ]
        )

    response = await async_client.get("/task/1", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "project_id, task_id, datos, status, detail",
    [
        (
            1,
            1,
            {
                "description": "probando el testing... otra vez",
                "date_exp": "2030-10-10",
                "state": db_models.State.EN_PROCESO,
                "assigned_user_id": 1,
                "append_label": [
                    db_models.TypeOfLabel.BACKEND.value,
                    db_models.TypeOfLabel.BUG.value,
                ],
                "remove_label": [
                    db_models.TypeOfLabel.FRONTEND.value,
                    db_models.TypeOfLabel.BUG.value,
                ],
            },
            200,
            {
                "date_exp": "2030-10-10T00:00:00",
                "description": "probando el testing... otra vez",
                "project_id": 1,
                "assigned_user_id": 1,
                "state": "en proceso",
                "task_id": 1,
                "title": "probando",
            },
        ),
        (
            1000,
            1,
            {"description": "probando el testing", "date_exp": "2030-10-10"},
            400,
            {
                "detail": "User with user_id 1 is not in project with project_id 1000",
            },
        ),
        (
            1,
            1000,
            {
                "description": "probando el testing",
                "date_exp": "2030-10-10",
                "assigned_user_id": None,
            },
            404,
            {
                "detail": "Task with task_id 1000 is not in Project with project_id 1",
            },
        ),
        (
            1,
            1,
            {
                "description": "probando el testing",
                "date_exp": "2030-10-10",
                "assigned_user_id": 3,
            },
            400,
            {
                "detail": "User with user_id 3 is not in project with project_id 1",
            },
        ),
    ],
)
async def test_update_task(
    async_client, auth_headers, project_id, task_id, datos, status, detail
):
    response = await async_client.patch(
        f"/task/{project_id}/{task_id}", headers=auth_headers, json=datos
    )
    assert response.status_code == status
    assert response.json() == detail


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "task_id, status, detail",
    [
        (1, 200, "Task successfully deleted"),
        (1, 404, "Task with task_id 1 is not in Project with project_id 1"),
    ],
)
async def test_delete_task(async_client, auth_headers, task_id, status, detail):
    response = await async_client.delete(f"/task/1/{task_id}", headers=auth_headers)
    assert response.status_code == status
    assert response.json() == {"detail": detail}
