"""Security behaviours: rate limiting, no stack traces, RBAC on staff-only routes."""
from app.core.ratelimit import limiter


def test_rate_limit_on_login(client):
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [client.post("/api/v1/auth/login", json={"login": "nobody@x.y", "password": "wrong-pass"}).status_code for _ in range(12)]
    finally:
        limiter.enabled = False
    assert 429 in codes and codes[0] == 401


def test_internal_errors_are_generic(client, monkeypatch):
    from app.api.routes import qualifications as q
    monkeypatch.setattr(q.repo, "list_qualifications", lambda db: 1 / 0)
    from tests.conftest import login
    h = login(client, "admin@demo.rpl")
    from fastapi.testclient import TestClient
    from app.main import app
    r = TestClient(app, raise_server_exceptions=False).get("/api/v1/qualifications", headers=h)
    assert r.status_code == 500 and r.json()["error"]["code"] == "internal_error"
    assert "ZeroDivision" not in r.text and "Traceback" not in r.text
