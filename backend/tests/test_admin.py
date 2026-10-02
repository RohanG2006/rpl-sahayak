"""Phase 11: admin RBAC, user management, rubric governance lock, audit log."""
import uuid

from tests.flows import score_all, started_plan


def test_admin_routes_require_admin(client, assessor_headers):
    for path in ("/api/v1/admin/overview", "/api/v1/admin/users", "/api/v1/admin/audit", "/api/v1/admin/tasks", "/api/v1/admin/sync"):
        assert client.get(path, headers=assessor_headers).status_code == 403, path


def test_overview_is_computed(client, admin_headers):
    o = client.get("/api/v1/admin/overview", headers=admin_headers).json()
    assert o["users_by_role"]["assessor"] >= 5 and {q["code"] for q in o["qualifications"]} == {"DGT/1001", "DGT/1009"}
    assert all(len(q["sha256"]) == 64 for q in o["qualifications"])


def test_user_lifecycle_and_self_protection(client, admin_headers):
    code = f"A{uuid.uuid4().int % 900 + 100}"
    login = f"{code.lower()}@demo.rpl"
    r = client.post("/api/v1/admin/users", headers=admin_headers, json={"login": login, "full_name": "New Assessor", "role": "assessor", "assessor_code": code})
    assert r.status_code == 201
    u = r.json()
    temp = u["temporary_password"]
    assert len(temp) >= 8
    assert client.post("/api/v1/auth/login", json={"login": login, "password": temp}).status_code == 200
    assert client.post("/api/v1/admin/users", headers=admin_headers, json={"login": login, "full_name": "Dup", "role": "assessor", "assessor_code": code}).status_code == 409
    assert client.put(f"/api/v1/admin/users/{u['id']}", headers=admin_headers, json={"is_active": False}).json()["is_active"] is False
    assert client.post("/api/v1/auth/login", json={"login": login, "password": temp}).status_code == 401
    me = client.get("/api/v1/auth/me", headers=admin_headers).json()
    assert client.put(f"/api/v1/admin/users/{me['id']}", headers=admin_headers, json={"is_active": False}).status_code == 409
    # password never appears in the audit log
    audit = client.get("/api/v1/admin/audit?action=admin.user", headers=admin_headers).json()
    assert temp not in str(audit)


def test_rubric_weight_locked_once_scored_but_wording_editable(client, admin_headers):
    p, wid, h, ah = started_plan(client)
    score_all(client, p, ah, default=3)
    r = client.put("/api/v1/admin/criteria/C04.2", headers=admin_headers, json={"weight": 9 / 4})
    assert r.status_code == 409 and r.json()["error"]["code"] == "rubric_locked"
    assert client.put("/api/v1/admin/tasks/T04", headers=admin_headers, json={"weight": 2.0}).json()["error"]["code"] == "rubric_locked"
    old = next(c for t in client.get("/api/v1/admin/tasks", headers=admin_headers).json() for c in t["criteria"] if c["criterion_code"] == "C04.2")
    anchors = {**old["anchors"], "4": old["anchors"]["4"] + " (clarified)"}
    r = client.put("/api/v1/admin/criteria/C04.2", headers=admin_headers, json={"anchors": anchors})
    assert r.status_code == 200 and r.json()["anchors"]["4"].endswith("(clarified)")
    assert client.put("/api/v1/admin/criteria/C04.2", headers=admin_headers, json={"anchors": {"0": "x"}}).status_code == 422
    client.put("/api/v1/admin/criteria/C04.2", headers=admin_headers, json={"anchors": old["anchors"]})  # restore
    log = client.get("/api/v1/admin/audit?action=admin.criterion_updated", headers=admin_headers).json()
    assert log["total"] >= 2 and log["rows"][0]["actor_role"] == "admin"


def test_audit_filters_and_pagination(client, admin_headers):
    started_plan(client)
    all_ = client.get("/api/v1/admin/audit?page_size=5", headers=admin_headers).json()
    assert len(all_["rows"]) == 5 and all_["total"] > 5 and "assessment.created" in all_["actions"]
    only = client.get("/api/v1/admin/audit?action=assessment.created", headers=admin_headers).json()
    assert only["rows"] and all(r["action"] == "assessment.created" for r in only["rows"])
    rows = client.get("/api/v1/admin/audit?actor_role=worker&page_size=200", headers=admin_headers).json()["rows"]
    assert all(r["actor_role"] == "worker" for r in rows)
