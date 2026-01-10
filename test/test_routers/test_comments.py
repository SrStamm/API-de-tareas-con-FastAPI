import pytest
from conftest import (
    auth_headers,
    test_create_project_init_for_tasks,
    test_create_task_init,
    async_client,
    client,
)


@pytest.mark.asyncio
async def test_create_comment(
    async_client,
    auth_headers,
    test_create_project_init_for_tasks,
    test_create_task_init,
):
    response = await async_client.post(
        "/task/1/comments",
        headers=auth_headers,
        json={"content": "@mirko esto es un comentario"},
    )

    print("Response body:", response.json())

    assert response.status_code == 200
    first_comment = response.json()

    assert all(
        key in first_comment
        for key in ["comment_id", "content", "created_at", "is_deleted", "task_id"]
    )

    response = await async_client.post(
        "/task/1/comments",
        headers=auth_headers,
        json={"content": "esto es otro comentario"},
    )

    print("Response body:", response.json())
    assert response.status_code == 200
    second_comment = response.json()
    assert all(
        key in second_comment
        for key in ["comment_id", "content", "created_at", "is_deleted", "task_id"]
    )


@pytest.mark.asyncio
def test_get_comment(client, auth_headers):
    response = client.get("/task/1/comments", headers=auth_headers)
    assert response.status_code == 200
    comments = response.json()
    assert isinstance(comments, list)
    for comment in comments:
        assert all(
            key in comment
            for key in [
                "comment_id",
                "task_id",
                "user_id",
                "content",
                "created_at",
                "update_at",
                "is_deleted",
            ]
        )


@pytest.mark.asyncio
def test_update_comment(client, auth_headers):
    response = client.patch(
        "/task/1/comments/1",
        headers=auth_headers,
        json={"content": "esto es un comentario actualizado"},
    )
    assert response.status_code == 200

    comment = response.json()
    assert all(
        key in comment
        for key in [
            "comment_id",
            "content",
            "created_at",
            "task_id",
            "user_id",
            "update_at",
            "is_deleted",
        ]
    )


@pytest.mark.asyncio
def test_delete_comment(client, auth_headers):
    response = client.delete("/task/1/comments/2", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"detail": "Comment successfully deleted"}


@pytest.mark.asyncio
def test_get_all_comments(client, auth_headers):
    response = client.get("/task/1/comments/all", headers=auth_headers)
    assert response.status_code == 200
    comments = response.json()
    assert len(comments) == 2
