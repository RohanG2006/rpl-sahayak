"""Tests run against a dedicated PostgreSQL database (rpl_sahayak_test) — never the dev DB.
Override with TEST_DATABASE_URL. AI provider forced to 'mock' so no test touches the network."""
import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://rpl:rpl@localhost:5433/rpl_sahayak_test"
)
os.environ["AI_PROVIDER"] = "mock"
os.environ["RATE_LIMIT_LOGIN"] = "1000/minute"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.base import DEMO_PASSWORD, seed_roles_and_staff  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_roles_and_staff(db)
        db.commit()
    yield


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


@pytest.fixture
def client():
    return TestClient(app)


def login(client: TestClient, login: str, password: str = DEMO_PASSWORD) -> dict:
    r = client.post("/api/v1/auth/login", json={"login": login, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def assessor_headers(client):
    return login(client, "assessor1@demo.rpl")


@pytest.fixture
def admin_headers(client):
    return login(client, "admin@demo.rpl")
