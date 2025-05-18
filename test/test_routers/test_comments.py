import pytest
from conftest import auth_headers, auth_headers2, test_create_project_init_for_tasks
from models import schemas, db_models, exceptions
from routers import comment
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Request

def test_create_comment(client, auth_headers, test_create_project_init_for_tasks):
    response = client.post(f'/task/1', headers=auth_headers, json={'description':'aaaaa', 'date_exp':'2030-12-30', 'user_ids':[1]})
    assert response.status_code == 200

    response = client.post(f'/task/1/comments', headers=auth_headers, json={'content':'esto es un comentario'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Nuevo comentario creado'}

    response = client.post(f'/task/1/comments', headers=auth_headers, json={'content':'esto es otro comentario'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Nuevo comentario creado'}

def test_get_comment(client, auth_headers):
    response = client.get(f'/task/1/comments', headers=auth_headers)
    assert response.status_code == 200
    comments = response.json()
    assert isinstance(comments, list)
    for comment in comments:
        assert all(key in comment for key in ['comment_id', 'task_id', 'user_id', 'content', 'created_at', 'update_at', 'is_deleted'])

def test_update_comment(client, auth_headers):
    response = client.patch(f'/task/1/comments/1', headers=auth_headers, json={'content':'esto es un comentario actualizado'})
    assert response.status_code == 200
    assert response.json() == {'detail': 'Comentario actualizado'}

def test_delete_comment(client, auth_headers):
    response = client.delete(f'/task/1/comments/2', headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {'detail': 'Comentario eliminado'}

def test_get_all_comments(client, auth_headers):
    response = client.get(f'/task/1/comments/all', headers=auth_headers)
    assert response.status_code == 200
    comments = response.json()
    assert len(comments) == 2