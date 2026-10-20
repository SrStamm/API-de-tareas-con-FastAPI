from main import app

DEMO_ORIGIN = "http://localhost:5173"


def _preflight(client, origin):
    return client.options(
        "/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_cors_preflight_allows_demo_frontend(client):
    response = _preflight(client, DEMO_ORIGIN)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == DEMO_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_rejects_unknown_origin(client):
    response = _preflight(client, "http://evil.example.com")

    assert "access-control-allow-origin" not in response.headers


def test_cors_does_not_use_wildcard_with_credentials(client):
    allowed_origins = next(
        m.kwargs["allow_origins"]
        for m in app.user_middleware
        if m.cls.__name__ == "CORSMiddleware"
    )

    assert "*" not in allowed_origins
