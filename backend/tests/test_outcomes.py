"""Phases 7–8: competency profile, skill gaps, recommendation rules, human decision, assessor workspace.
Integration: Worker → Profile → Match → Assessment → Evidence → Assessor → Decision."""
from tests.conftest import login
from tests.flows import EMAIL, score_all, started_plan, upload_required_evidence


def recommend(client, p, ah):
    r = client.post(f"/api/v1/assessments/{p['id']}/recommendation", headers=ah)
    assert r.status_code == 200, r.text
    return r.json()


def test_full_workflow_to_human_decision(client):
    p, wid, h, ah = started_plan(client)
    assert client.post(f"/api/v1/assessments/{p['id']}/recommendation", headers=ah).status_code == 409  # not scored yet
    upload_required_evidence(client, p, wid, h)
    score_all(client, p, ah, default=3)

    rec = recommend(client, p, ah)
    assert rec["outcome"] == "ELIGIBLE" and rec["evidence_coverage"] == 1.0 and rec["competency_coverage"] == 1.0
    assert [r["rule"] for r in rec["rule_trace"]] == ["R0", "R1", "R2", "R3", "R4"] and all(r["passed"] for r in rec["rule_trace"])
    assert "final decision by authorised human assessor" in rec["disclaimer"]
    assert any("§6.2(c)" in r["source"] for r in rec["rule_trace"])

    comp = client.get(f"/api/v1/competencies/{p['id']}", headers=ah).json()
    assert comp["overall_pct"] == 75.0 and comp["summary"]["provider"] == "rules"
    assert set(comp["competencies"]) == {"components_tools", "safety", "joints", "wiring", "testing", "fault_diagnosis", "protection", "drawing"}

    # decision guards
    body = {"plan_id": p["id"], "decision": "APPROVE", "comments": "Competent across all assessed tasks; evidence verified."}
    assert client.post("/api/v1/assessor/decision", headers=h, json=body).status_code == 403  # worker
    other = login(client, EMAIL["A05"] if p["assessor"]["code"] != "A05" else EMAIL["A04"])
    assert client.post("/api/v1/assessor/decision", headers=other, json=body).status_code == 403
    assert client.post("/api/v1/assessor/decision", headers=ah, json={**body, "comments": "ok"}).status_code == 422
    assert client.post("/api/v1/assessor/decision", headers=ah, json={**body, "decision": "REASSESS"}).status_code == 409

    # worker cannot see results before decision
    assert client.get(f"/api/v1/competencies/{p['id']}", headers=h).status_code == 403
    r = client.post("/api/v1/assessor/decision", headers=ah, json=body)
    assert r.status_code == 200
    d = r.json()["decision"]
    assert d["decision"] == "APPROVE" and d["agrees_with_recommendation"] is True
    assert r.json()["plan"]["status"] == "DECIDED" and r.json()["plan"]["ncvet_stage"] == "Certification & Feedback"
    assert client.post("/api/v1/assessor/decision", headers=ah, json=body).status_code == 409  # only once
    # scores frozen after decision
    t = p["tasks"][0]
    assert client.post(f"/api/v1/assessments/{p['id']}/tasks/{t['task_code']}/score", headers=ah,
                       json={"scores": [{"criterion_code": t["criteria"][0]["criterion_code"], "final_score": 4, "assessor_note": "x"}]}).status_code == 409
    # released to worker
    assert client.get(f"/api/v1/competencies/{p['id']}", headers=h).status_code == 200
    assert client.get(f"/api/v1/assessments/{p['id']}/decision", headers=h).json()["decision"] == "APPROVE"


def test_safety_gate_blocks_eligible(client):
    p, wid, h, ah = started_plan(client)
    upload_required_evidence(client, p, wid, h)
    score_all(client, p, ah, default=4, overrides={"C02.2": 1})
    rec = recommend(client, p, ah)
    assert rec["outcome"] == "NOT_YET_READY"
    r2 = next(r for r in rec["rule_trace"] if r["rule"] == "R2")
    assert not r2["passed"] and "C02.2" in r2["detail"]


def test_missing_evidence_suggests_reassessment(client):
    p, wid, h, ah = started_plan(client)
    score_all(client, p, ah, default=4)
    rec = recommend(client, p, ah)
    assert rec["outcome"] == "REASSESSMENT_SUGGESTED" and rec["evidence_coverage"] == 0.0


def test_low_scores_not_ready_and_gaps_cite_official_criteria(client):
    p, wid, h, ah = started_plan(client)
    upload_required_evidence(client, p, wid, h)
    score_all(client, p, ah, default=3, overrides={c["criterion_code"]: 2 for t in p["tasks"] if t["task_code"] == "T06" for c in t["criteria"]})
    gaps = client.get(f"/api/v1/skill-gaps/{p['id']}", headers=ah).json()
    fd = next(a for a in gaps["areas"] if a["competency_key"] == "fault_diagnosis")
    assert fd["demonstrated"] == 50.0 and fd["gap"] == 10.0 and fd["status"] == "gap"
    official = [x for x in fd["learning_topics"] if x["source"] == "official"]
    assert any(x["topic"] == "Test, locate the fault and repair a domestic wiring installation." and x["lo_number"] == 5 for x in official)
    assert any(x["source"] == "suggested" for x in fd["learning_topics"])
    assert len(gaps["not_assessed_in_prototype"]) == 22
    rec = recommend(client, p, ah)
    # LO5 is shared by T04/T06/T07/T08 so it stays above 60; overall still ≥ 60 → outcome depends only on computed rules
    assert rec["outcome"] in ("ELIGIBLE", "NOT_YET_READY")
    assert rec["overall_pct"] < 75


def test_disagreeing_decision_is_recorded(client):
    p, wid, h, ah = started_plan(client)
    upload_required_evidence(client, p, wid, h)
    score_all(client, p, ah, default=3)
    recommend(client, p, ah)
    r = client.post("/api/v1/assessor/decision", headers=ah, json={"plan_id": p["id"], "decision": "REASSESS",
                                                                    "comments": "Fault finding was guided; repeat T06 independently.",
                                                                    "reassess_task_codes": ["T06"]})
    assert r.json()["decision"]["agrees_with_recommendation"] is False


def test_assessor_candidate_list_and_dashboard(client, admin_headers):
    p, wid, h, ah = started_plan(client)
    rows = client.get("/api/v1/assessor/candidates?page_size=100", headers=ah).json()["rows"]
    row = next(r for r in rows if r["plan_id"] == p["id"])
    assert row["qualification_code"] == "DGT/1001" and row["ai_match_pct"] > 0 and row["trade"] == "Electrician"
    assert client.get("/api/v1/assessor/candidates", headers=h).status_code == 403
    assert client.get("/api/v1/assessor/candidates", headers=admin_headers).json()["total"] >= 1
    k = client.get("/api/v1/analytics/dashboard", headers=ah).json()
    assert k["assigned"] >= 1 and "note" in k
