"""Our first test.

A test is just a function whose name starts with `test_`. Run them all from
the `backend` folder with:

    pytest -q

`TestClient` pretends to be a browser calling our app, without needing the
server to actually be running. That makes tests fast and means they work in
CI, where there is no server at all.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_says_ok():
    response = client.get("/health")

    assert response.status_code == 200  # 200 means "fine"
    assert response.json() == {"status": "ok"}


def test_unknown_url_is_a_404():
    """Anything we haven't defined should say "not found", not crash."""
    response = client.get("/this-does-not-exist")

    assert response.status_code == 404
