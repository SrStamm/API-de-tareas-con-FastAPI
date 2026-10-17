from fastapi.testclient import TestClient

from main import app


def _client_with_failing_route():
    """Register a temporary route that raises, keeping the real app stack."""

    def boom():
        raise RuntimeError("boom real del endpoint")

    app.add_api_route("/__boom_test", boom, methods=["GET"])
    return TestClient(app, raise_server_exceptions=False)


def _remove_failing_route():
    app.router.routes = [
        route
        for route in app.router.routes
        if getattr(route, "path", None) != "/__boom_test"
    ]


def test_unhandled_exception_returns_500_json():
    """An unhandled exception must answer 500 with a JSON body, never an empty one."""
    client = _client_with_failing_route()
    try:
        response = client.get("/__boom_test")

        assert response.status_code == 500
        assert response.json() == {"detail": "Internal Server Error"}
    finally:
        _remove_failing_route()


def test_unhandled_exception_logs_real_traceback(caplog):
    """The original traceback must reach the logs, not a masked or missing error."""
    client = _client_with_failing_route()
    try:
        with caplog.at_level("ERROR"):
            client.get("/__boom_test")

        assert "boom real del endpoint" in caplog.text
        assert "Traceback" in caplog.text
    finally:
        _remove_failing_route()
