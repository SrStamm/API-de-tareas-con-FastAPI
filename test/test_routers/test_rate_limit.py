import pytest
from main import app
from core.limiter import limiter


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Keep counters isolated so parallel/ordered tests never bleed into each other."""
    limiter.reset()
    yield
    limiter.reset()


def test_rate_limit_returns_429_when_exceeded(client):
    payload = {"refresh": "invalid-token-for-rate-limit-test"}

    responses = [
        client.post("/refresh", json=payload) for _ in range(11)
    ]

    statuses = [response.status_code for response in responses]

    assert statuses.count(429) >= 1, (
        f"Expected at least one 429 after exceeding 10/minute, got {statuses}"
    )
    assert 500 not in statuses, (
        f"Rate limit must not surface as a 500, got {statuses}"
    )


def test_rate_limit_response_reports_retry_after(client):
    payload = {"refresh": "invalid-token-for-rate-limit-test"}
    response = None

    for _ in range(12):
        response = client.post("/refresh", json=payload)
        if response.status_code == 429:
            break

    assert response is not None
    assert response.status_code == 429
    assert response.json().get("error", "").startswith("Rate limit exceeded")
