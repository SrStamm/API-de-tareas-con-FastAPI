from conftest import client, test_user
import pytest

def test_root(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {'detail':'Bienvenido a esta API!'}

def test_failed_login_not_found(client):
    response = client.post("/login", data= {"username":'a', "password":'0000'})
    assert response.status_code == 404
    assert response.json() == {'detail':'User not found'}

def test_failed_login_incorrect_password(client, test_user):
    response = client.post("/login", data= {"username":test_user.username, "password":'5555'})
    assert response.status_code == 400
    assert response.json() == {'detail':'Password incorrect'}