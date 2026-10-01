"""Phase 4: qualification mapping engine — computed, explainable, configurable, not hard-coded."""
import pytest

from app.core.config import get_match_weights
from tests.conftest import make_worker

DOMESTIC = ["House wiring installation", "Switch and socket installation", "Fan installation and repair",
            "MCB / circuit breaker installation", "Electrical fault diagnosis"]


def match(client, h, wid):
    r = client.post("/api/v1/qualifications/match", headers=h, json={"worker_id": wid})
    assert r.status_code == 200, r.text
    return r.json()


def test_requires_confirmed_skills(client):
    r = client.post("/api/v1/workers", json={"full_name": "Early Bird", "mobile": "9123400001", "pin": "1234"})
    wid, h = r.json()["worker"]["id"], {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.post("/api/v1/qualifications/match", headers=h, json={"worker_id": wid})
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_workflow_state"


def test_score_is_weighted_sum_of_reported_components(client):
    wid, h = make_worker(client, skills=DOMESTIC)
    res = match(client, h, wid)["results"]
    for r in res:
        w, c = r["weights"], r["components"]
        expected = sum(w[k] * c[k] for k in w) / sum(w.values())
        assert r["final_score"] == pytest.approx(expected, abs=1e-3)
        assert 0 <= r["final_pct"] <= 100
    assert [r["rank"] for r in res] == [1, 2]


def test_domestic_electrician_ranks_electrician_first_with_explanations(client):
    wid, h = make_worker(client, skills=DOMESTIC)
    top = match(client, h, wid)["results"][0]
    assert top["qualification_code"] == "DGT/1001"
    by_label = {m["label"]: m for m in top["matched_skills"]}
    assert by_label["House wiring installation"]["lo_number"] == 5
    assert by_label["Fan installation and repair"]["lo_number"] == 10
    statuses = {lo["lo_number"]: lo["status"] for lo in top["learning_outcomes"]}
    assert statuses[5] == "matched" and statuses[17] == "not_evidenced"  # no motor work declared
    assert all(c["result"] == "pass" for c in top["eligibility"])
    assert all("QF DGT/1001" in c["source"] for c in top["eligibility"])


def test_wireman_profile_ranks_wireman_first(client):
    wid, h = make_worker(client, occupation="Wireman", education="8th", sci=False,
                         skills=["House wiring installation", "Conduit and casing capping wiring", "Switch board fixing"])
    res = match(client, h, wid)["results"]
    assert res[0]["qualification_code"] == "DGT/1009"
    elec = next(r for r in res if r["qualification_code"] == "DGT/1001")
    edu = next(c for c in elec["eligibility"] if c["key"] == "education")
    assert edu["result"] == "fail"  # 10th + Sci/Maths required for Electrician (QF item 15)


def test_motor_skills_cover_motor_learning_outcomes(client):
    wid, h = make_worker(client, skills=["Motor wiring and maintenance", "Motor rewinding"])
    top = next(r for r in match(client, h, wid)["results"] if r["qualification_code"] == "DGT/1001")
    statuses = {lo["lo_number"]: lo["status"] for lo in top["learning_outcomes"]}
    assert statuses[17] in ("matched", "partial") or statuses[20] in ("matched", "partial")


def test_underage_and_low_experience_fail_category_iv(client):
    wid, h = make_worker(client, skills=DOMESTIC, age=19, years=1.5)
    top = next(r for r in match(client, h, wid)["results"] if r["qualification_code"] == "DGT/1001")
    checks = {c["key"]: c["result"] for c in top["eligibility"]}
    assert checks["age"] == "fail" and checks["experience"] == "fail"
    assert top["components"]["experience"] == pytest.approx(0.5)


def test_weights_are_configurable(client, monkeypatch):
    wid, h = make_worker(client, skills=DOMESTIC)
    base = match(client, h, wid)["results"][0]
    w = get_match_weights()
    monkeypatch.setattr(w, "skill", 0.0)
    monkeypatch.setattr(w, "eligibility", 0.5)
    alt = next(r for r in match(client, h, wid)["results"] if r["qualification_code"] == base["qualification_code"])
    assert alt["weights"]["skill"] == 0.0 and alt["final_score"] != base["final_score"]


def test_plan_creation_assigns_assessor_and_is_idempotent(client):
    wid, h = make_worker(client, skills=DOMESTIC)
    res = match(client, h, wid)["results"]
    wire = next(r for r in res if r["qualification_code"] == "DGT/1009")
    r = client.post("/api/v1/assessments", headers=h, json={"worker_id": wid, "qualification_id": wire["qualification_id"]})
    assert r.status_code == 409 and r.json()["error"]["code"] == "qualification_not_assessable"
    elec = next(r for r in res if r["qualification_code"] == "DGT/1001")
    r1 = client.post("/api/v1/assessments", headers=h, json={"worker_id": wid, "qualification_id": elec["qualification_id"]})
    assert r1.status_code == 201
    p = r1.json()
    assert p["status"] == "PLAN_CREATED" and p["assessor"]["code"].startswith("A") and len(p["tasks"]) == 8
    assert p["match_snapshot"]["qualification_code"] == "DGT/1001"
    assert client.get(f"/api/v1/workers/{wid}", headers=h).json()["status"] == "QUALIFICATION_CONFIRMED"
    r2 = client.post("/api/v1/assessments", headers=h, json={"worker_id": wid, "qualification_id": elec["qualification_id"]})
    assert r2.json()["id"] == p["id"]
    # worker view hides AI-suggested scores
    assert all(c["score"] is None for t in p["tasks"] for c in t["criteria"])
