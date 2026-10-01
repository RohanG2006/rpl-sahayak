"""Phase 5: pure scoring engine (hand-computed fixtures) + readiness + assessment API flow."""
import pytest

from app.services import readiness, scoring
from tests.conftest import login, make_worker

T = [scoring.TaskDef("T1", 1.0, "wiring", (5,)), scoring.TaskDef("T2", 2.0, "safety", (5, 8))]


def C(task, code, w, s, dim="quality", safety=False):
    return scoring.CriterionScore(task, code, w, s, dim, safety)


def test_task_pct_weighted():
    crits = [C("T1", "a", 1, 4), C("T1", "b", 3, 2)]  # (4 + 6) / (4 * 4) = 62.5
    assert scoring.task_scores(T[:1], crits)["T1"]["task_pct"] == 62.5


def test_lo_and_overall_weighting():
    crits = [C("T1", "a", 1, 4), C("T2", "b", 1, 2)]  # T1 100, T2 50
    out = scoring.compute(T, crits)
    assert out["learning_outcomes"][5] == pytest.approx((1 * 100 + 2 * 50) / 3, abs=0.01)
    assert out["learning_outcomes"][8] == 50.0
    assert out["overall_pct"] == pytest.approx(66.67, abs=0.01)
    assert out["complete"] is True


def test_unscored_criteria_excluded_and_incomplete():
    out = scoring.compute(T, [C("T1", "a", 1, 3), C("T1", "b", 1, None), C("T2", "c", 1, None)])
    assert out["tasks"]["T1"]["task_pct"] == 75.0 and not out["tasks"]["T1"]["complete"]
    assert out["tasks"]["T2"]["task_pct"] is None and out["overall_pct"] is None and not out["complete"]


def test_dimensions_and_safety_flags():
    crits = [C("T1", "a", 1, 1, "safety", True), C("T2", "b", 1, 4, "safety", True), C("T2", "c", 2, 3, "tools")]
    out = scoring.compute(T, crits)
    assert out["dimensions"]["safety"] == 62.5 and out["dimensions"]["tools"] == 75.0
    assert out["safety_flags"] == ["a"]


def test_readiness_threshold_strictly_above_70():
    snap = {"learning_outcomes": [{"lo_number": n, "status": "matched"} for n in range(1, 11)]}
    scope = list(range(1, 11))
    seven = {n: ("regularly" if n <= 7 else "never") for n in scope}
    assert readiness.evaluate(scope, seven, snap, [])["pathway"] == "UPSKILLING_SUGGESTED"  # 70 % is not > 70 %
    eight = {n: ("regularly" if n <= 8 else "never") for n in scope}
    r = readiness.evaluate(scope, eight, snap, [])
    assert r["pathway"] == "DIRECT_ASSESSMENT" and "§6.2(c)" in r["threshold_source"]


def test_readiness_flags_unsupported_claims_and_eligibility():
    snap = {"learning_outcomes": [{"lo_number": 1, "status": "not_evidenced"}]}
    r = readiness.evaluate([1], {1: "regularly"}, snap, [{"key": "age", "label": "Age ≥ 21", "result": "fail"}])
    assert r["probe_los"] == [1] and r["eligibility_flags"] == ["age"]


# ---- API flow ---------------------------------------------------------------------------------------
DOMESTIC = ["House wiring installation", "Switch and socket installation", "Fan installation and repair",
            "MCB / circuit breaker installation", "Electrical fault diagnosis", "Measurement with multimeter"]


def plan_for(client):
    wid, h = make_worker(client, skills=DOMESTIC)
    res = client.post("/api/v1/qualifications/match", headers=h, json={"worker_id": wid}).json()["results"]
    q = next(r for r in res if r["qualification_code"] == "DGT/1001")
    p = client.post("/api/v1/assessments", headers=h, json={"worker_id": wid, "qualification_id": q["qualification_id"]}).json()
    return p, h


def assessor_for(client, plan):
    return login(client, {"A01": "assessor1@demo.rpl", "A02": "assessor2@demo.rpl", "A03": "assessor3@demo.rpl",
                          "A04": "assessor4@demo.rpl", "A05": "assessor5@demo.rpl"}[plan["assessor"]["code"]])


def test_full_phase5_flow(client):
    p, h = plan_for(client)
    scope = sorted({lo for t in p["tasks"] for lo in t["lo_numbers"]})
    assert scope == [1, 2, 3, 5, 8, 12, 17, 27]
    # cannot start before self-assessment
    assert client.post(f"/api/v1/assessments/{p['id']}/start", headers=h).status_code == 409
    r = client.post(f"/api/v1/assessments/{p['id']}/self-assessment", headers=h,
                    json={"responses": {str(lo): "regularly" for lo in scope}})
    assert r.status_code == 200 and r.json()["readiness"]["pathway"] == "DIRECT_ASSESSMENT"
    assert client.post(f"/api/v1/assessments/{p['id']}/self-assessment", headers=h, json={"responses": {"30": "never"}}).status_code == 409
    assert client.post(f"/api/v1/assessments/{p['id']}/start", headers=h).json()["status"] == "TASKS_IN_PROGRESS"

    r = client.put(f"/api/v1/assessments/{p['id']}/tasks/T02/progress", headers=h,
                   json={"checklist_state": {"0": True, "1": True}, "status": "SUBMITTED"})
    assert next(t for t in r.json()["tasks"] if t["task_code"] == "T02")["attempt"]["status"] == "SUBMITTED"

    # worker cannot score
    body = {"scores": [{"criterion_code": "C02.1", "final_score": 4, "assessor_note": "Observed"}]}
    assert client.post(f"/api/v1/assessments/{p['id']}/tasks/T02/score", headers=h, json=body).status_code == 403
    # a different assessor cannot score
    other = login(client, "assessor5@demo.rpl" if p["assessor"]["code"] != "A05" else "assessor4@demo.rpl")
    assert client.post(f"/api/v1/assessments/{p['id']}/tasks/T02/score", headers=other, json=body).status_code == 403

    ah = assessor_for(client, p)
    # note required without evidence
    r = client.post(f"/api/v1/assessments/{p['id']}/tasks/T02/score", headers=ah, json={"scores": [{"criterion_code": "C02.1", "final_score": 3}]})
    assert r.status_code == 409 and r.json()["error"]["code"] == "note_required"
    # out-of-range score rejected
    assert client.post(f"/api/v1/assessments/{p['id']}/tasks/T02/score", headers=ah,
                       json={"scores": [{"criterion_code": "C02.1", "final_score": 5, "assessor_note": "x"}]}).status_code == 422

    # score every criterion with 3 → every task 75 %
    for t in p["tasks"]:
        scores = [{"criterion_code": c["criterion_code"], "final_score": 3, "assessor_note": "Observed directly"} for c in t["criteria"]]
        r = client.post(f"/api/v1/assessments/{p['id']}/tasks/{t['task_code']}/score", headers=ah, json={"scores": scores})
        assert r.status_code == 200, r.text
    assert r.json()["status"] == "SCORED"
    res = client.get(f"/api/v1/assessments/{p['id']}/results", headers=ah).json()
    assert res["overall_pct"] == 75.0 and res["complete"] and all(v == 75.0 for v in res["competencies"].values())
    # worker results hidden until decision
    assert client.get(f"/api/v1/assessments/{p['id']}/results", headers=h).status_code == 403
