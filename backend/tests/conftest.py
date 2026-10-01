"""Tests run against a dedicated PostgreSQL database (rpl_sahayak_test) — never the dev DB.
Override with TEST_DATABASE_URL. AI provider forced to 'mock' so no test touches the network."""
import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://rpl:rpl@localhost:5433/rpl_sahayak_test"
)
os.environ["AI_PROVIDER"] = "mock"
import tempfile  # noqa: E402
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="rpl-test-storage-")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.core.ratelimit import limiter  # noqa: E402

limiter.enabled = False  # exercised explicitly in test_security.py::test_rate_limit_on_login
from app.seed.base import DEMO_PASSWORD, seed_roles_and_staff  # noqa: E402
from app.seed.official import load_qualifications, load_task_banks  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_roles_and_staff(db)
        load_qualifications(db)
        load_task_banks(db)
        db.commit()
    yield
    import shutil
    shutil.rmtree(os.environ["STORAGE_DIR"], ignore_errors=True)  # remove this run's temporary uploads


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


def make_worker(client, *, skills, occupation="Electrician", years=6, age=29, education="10th", sci=True, tasks=(), mobile=None):
    """Create a worker via the public API and confirm a skill list. Returns (worker_id, headers)."""
    import uuid
    body = {"full_name": "Fixture Worker", "mobile": mobile or "9" + str(uuid.uuid4().int)[:9], "pin": "4321",
            "age": age, "state": "Bihar", "district": "Patna", "occupation": occupation, "years_experience": years,
            "education_level": education, "has_science_maths": sci}
    r = client.post("/api/v1/workers", json=body)
    assert r.status_code == 201, r.text
    wid, h = r.json()["worker"]["id"], {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.post(f"/api/v1/workers/{wid}/experience", headers=h, json={"raw_text": "Declaration for fixture: " + ", ".join(skills)}).status_code == 201
    items = [{"kind": "skill", "label": s} for s in skills] + [{"kind": "task", "label": t} for t in tasks]
    assert client.put(f"/api/v1/workers/{wid}/skills", headers=h, json={"skills": items}).status_code == 200
    return wid, h
