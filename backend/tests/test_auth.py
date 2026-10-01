from tests.conftest import login


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["ai_provider"] == "mock"


def test_login_success_returns_role(client):
    r = client.post("/api/v1/auth/login", json={"login": "assessor1@demo.rpl", "password": "demo1234"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["role"] == "assessor" and body["user"]["assessor_code"] == "A01"
    assert "password_hash" not in r.text


def test_login_wrong_password_is_generic_401(client):
    r = client.post("/api/v1/auth/login", json={"login": "assessor1@demo.rpl", "password": "wrong-pass"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_me_requires_token(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401 and "Traceback" not in r.text


def test_me_with_token(client):
    h = login(client, "admin@demo.rpl")
    assert client.get("/api/v1/auth/me", headers=h).json()["role"] == "admin"


def test_expired_token_reports_session_expired(client):
    import jwt
    from datetime import datetime, timedelta, timezone
    from app.core.config import get_settings
    s = get_settings()
    tok = jwt.encode({"sub": "x", "role": "worker", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, s.jwt_secret, algorithm=s.jwt_algorithm)
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "session_expired"


def test_password_is_hashed(db):
    from sqlalchemy import select
    from app.models import User
    u = db.scalar(select(User).where(User.login == "admin@demo.rpl"))
    assert u.password_hash.startswith("$2") and "demo1234" not in u.password_hash
