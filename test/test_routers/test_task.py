import pytest
from conftest import (
    auth_headers,
    auth_headers2,
    test_create_project_init_for_tasks,
    async_client,
    clean_redis,
)
from models import schemas, db_models, exceptions
from api.v1.routers import task
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Request


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "project_id, datos, status, detail",
    [
        (
            1,
            {
                "description": "probando el testing",
                "date_exp": "2025-10-10",
                "user_ids": [1],
                "label": ["bug"],
            },
            200,
            "A new task has been created and users have been successusfully assigned",
        ),
        (
            1,
            {
                "description": "probando el testing",
                "date_exp": "2025-10-10",
                "user_ids": [3],
            },
            400,
            "User with user_id 3 is not in project with project_id 1",
        ),
        (
            1,
            {
                "description": "probando el testing",
                "date_exp": "2025-10-10",
                "user_ids": [1000],
            },
            404,
            "User with user_id 1000 not found",
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
    assert response.json() == {"detail": detail}


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
                "description",
                "date_exp",
                "state",
                "asigned",
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
                "date_exp": "2025-12-12",
                "state": db_models.State.EN_PROCESO,
                "exclude_user_ids": [1],
                "append_user_ids": [2],
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
            "A task has been successfully updated",
        ),
        (
            1000,
            1,
            {"description": "probando el testing", "date_exp": "2025-10-10"},
            404,
            "Project with project_id 1000 not found",
        ),
        (
            1,
            1000,
            {"description": "probando el testing", "date_exp": "2025-10-10"},
            404,
            "Task with task_id 1000 is not in Project with project_id 1",
        ),
        (
            1,
            1,
            {
                "description": "probando el testing",
                "date_exp": "2025-10-10",
                "exclude_user_ids": [100000],
            },
            400,
            "Task with task_id 1 is NOT assigned to User with user_id 100000",
        ),
        (
            1,
            1,
            {
                "description": "probando el testing",
                "date_exp": "2025-10-10",
                "append_user_ids": [3],
            },
            400,
            "User with user_id 3 is not in project with project_id 1",
        ),
        (
            1,
            1,
            {
                "description": "probando el testing",
                "date_exp": "2025-10-10",
                "append_user_ids": [2],
            },
            400,
            "Task with task_id 1 is assigned to User with user_id 2",
        ),
        (
            1,
            1,
            {
                "description": "probando el testing",
                "date_exp": "2025-10-10",
                "append_user_ids": [100000],
            },
            404,
            "User with user_id 100000 not found",
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
    assert response.json() == {"detail": detail}


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


@pytest.mark.asyncio
async def test_get_users_for_task(async_client, auth_headers, clean_redis):
    response = await async_client.get("/task/1/users", headers=auth_headers)
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    for user in users:
        assert all(key in user for key in ["user_id", "username"])

    response = await async_client.get("/task/1/users", headers=auth_headers)
    assert response.status_code == 200

