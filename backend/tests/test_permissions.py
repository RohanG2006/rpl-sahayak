"""Systematic access-control matrix (spec §34): anonymous / worker / other worker / assessor / other assessor / admin."""
import pytest

from tests.conftest import login, make_worker
from tests.flows import EMAIL, started_plan


@pytest.fixture(scope="module")
def world(request):
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    p, wid, h, ah = started_plan(c)
    other_wid, other_h = make_worker(c, skills=["House wiring installation"])
    other_assessor = login(c, EMAIL["A05"] if p["assessor"]["code"] != "A05" else EMAIL["A04"])
    admin = login(c, "admin@demo.rpl")
    return {"c": c, "pid": p["id"], "wid": wid, "worker": h, "other_wid": other_wid, "other_worker": other_h,
            "assessor": ah, "other_assessor": other_assessor, "admin": admin}


PROTECTED = [
    ("GET", "/api/v1/auth/me"), ("GET", "/api/v1/qualifications"), ("GET", "/api/v1/assessments"),
    ("GET", "/api/v1/assessor/candidates"), ("GET", "/api/v1/analytics/dashboard"), ("GET", "/api/v1/analytics/consistency"),
    ("GET", "/api/v1/admin/overview"), ("GET", "/api/v1/admin/audit"), ("GET", "/api/v1/sync/status"),
    ("POST", "/api/v1/assessor/decision"), ("POST", "/api/v1/sync"), ("POST", "/api/v1/qualifications/match"),
]


@pytest.mark.parametrize("method,path", PROTECTED)
def test_anonymous_gets_401(world, method, path):
    r = world["c"].request(method, path, json={})
    assert r.status_code == 401, f"{method} {path} → {r.status_code}"


STAFF_ONLY = ["/api/v1/assessor/candidates", "/api/v1/analytics/dashboard", "/api/v1/analytics/consistency"]
ADMIN_ONLY = ["/api/v1/admin/overview", "/api/v1/admin/users", "/api/v1/admin/audit", "/api/v1/admin/tasks", "/api/v1/admin/sync"]


@pytest.mark.parametrize("path", STAFF_ONLY + ADMIN_ONLY)
def test_worker_blocked_from_staff_and_admin(world, path):
    assert world["c"].get(path, headers=world["worker"]).status_code == 403


@pytest.mark.parametrize("path", ADMIN_ONLY)
def test_assessor_blocked_from_admin(world, path):
    assert world["c"].get(path, headers=world["assessor"]).status_code == 403


@pytest.mark.parametrize("path", STAFF_ONLY + ADMIN_ONLY)
def test_admin_can_read_everything(world, path):
    assert world["c"].get(path, headers=world["admin"]).status_code == 200


def test_worker_isolation(world):
    c, pid, wid, other = world["c"], world["pid"], world["wid"], world["other_worker"]
    assert c.get(f"/api/v1/workers/{wid}", headers=other).status_code == 403
    assert c.put(f"/api/v1/workers/{wid}", headers=other, json={"locality": "x"}).status_code == 403
    assert c.post(f"/api/v1/workers/{wid}/experience", headers=other, json={"raw_text": "Trying to write to someone else"}).status_code == 403
    assert c.get(f"/api/v1/assessments/{pid}", headers=other).status_code == 403
    assert c.get(f"/api/v1/evidence?plan_id={pid}", headers=other).status_code == 403
    assert c.post(f"/api/v1/qualifications/match", headers=other, json={"worker_id": wid}).status_code == 403
    assert all(p["id"] != pid for p in c.get("/api/v1/assessments", headers=other).json())


def test_assessor_isolation(world):
    c, pid, oa = world["c"], world["pid"], world["other_assessor"]
    assert c.get(f"/api/v1/assessments/{pid}", headers=oa).status_code == 403
    assert c.get(f"/api/v1/competencies/{pid}", headers=oa).status_code == 403
    assert c.post(f"/api/v1/assessments/{pid}/recommendation", headers=oa).status_code == 403
    assert all(r["plan_id"] != pid for r in c.get("/api/v1/assessor/candidates?page_size=100", headers=oa).json()["rows"])


def test_only_assessors_score_and_decide(world):
    c, pid = world["c"], world["pid"]
    body = {"scores": [{"criterion_code": "C02.1", "final_score": 3, "assessor_note": "x"}]}
    for who in ("worker", "admin"):
        assert c.post(f"/api/v1/assessments/{pid}/tasks/T02/score", headers=world[who], json=body).status_code == 403, who
        assert c.post("/api/v1/assessor/decision", headers=world[who],
                      json={"plan_id": pid, "decision": "APPROVE", "comments": "Not allowed to decide"}).status_code == 403, who


def test_worker_cannot_reach_staff_only_fields(world):
    """Workers never receive AI-suggested scores or assessor notes before a decision."""
    p = world["c"].get(f"/api/v1/assessments/{world['pid']}", headers=world["worker"]).json()
    for t in p["tasks"]:
        for crit in t["criteria"]:
            if crit["score"]:
                assert crit["score"]["ai_suggested_score"] is None and crit["score"]["assessor_note"] is None
