"""Phase 13: demo mode — seeding drives the real API, outputs are computed (not copied), everything is labelled."""
import csv

import pytest
from sqlalchemy import select

from app.core.config import DATA_DIR, get_settings
from app.models import AIObservation, AssessmentPlan, AuditLog, Evidence, Recommendation, User, WorkerProfile
from app.seed import demo


def _workers():
    with (DATA_DIR / "demo" / "workers.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(l for l in f if not l.startswith("#")))


def test_demo_csvs_are_labelled_and_sized():
    for name in ("workers.csv", "experiences.csv", "skills.csv", "assessments.csv", "task_scores.csv", "evidence.csv", "assessor_scores.csv"):
        first = (DATA_DIR / "demo" / name).read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith("# SYNTHETIC / DEMONSTRATION DATA"), name
    ws = _workers()
    assert 30 <= len(ws) <= 50 and {w["data_origin"] for w in ws} == {"synthetic"}
    assert len({w["archetype"] for w in ws}) == 10
    assert 15 <= len([w for w in ws if w["target_status"] in ("PLAN_CREATED", "READINESS_EVALUATED", "TASKS_IN_PROGRESS", "AI_EVIDENCE_REVIEWED",
                                                                  "ASSESSOR_SCORING", "UNDER_ASSESSOR_REVIEW", "DECIDED")]) <= 30
    # inputs only: no computed outputs stored in the CSVs
    assert not any(k in ws[0] for k in ("final_pct", "recommendation", "overall_pct"))


@pytest.fixture(scope="module")
def seeded():
    ws = _workers()
    pick = {"W001"} | {next(w["worker_key"] for w in ws if w["archetype"] == a and w["target_status"] in ("DECIDED", "UNDER_ASSESSOR_REVIEW"))
                       for a in ("safety_gaps", "missing_evidence")}
    r = demo.seed_demo(reset=True, only=pick)
    return pick, r


def test_seed_creates_synthetic_rows_through_the_api(seeded, db):
    pick, r = seeded
    assert r["created"] == len(pick)
    profs = list(db.scalars(select(WorkerProfile).where(WorkerProfile.data_origin == "synthetic")))
    assert len(profs) >= len(pick) and all(p.last_match for p in profs if p.status not in ("REGISTERED", "PROFILE_COMPLETE"))
    ids = {p.id for p in profs}
    ev = list(db.scalars(select(Evidence).where(Evidence.worker_id.in_(ids))))
    assert ev and {e.data_origin for e in ev} == {"synthetic"}
    obs = list(db.scalars(select(AIObservation).where(AIObservation.worker_id.in_(ids), AIObservation.kind == "evidence_analysis")))
    assert obs and {o.provider for o in obs} == {"demo-prepared"} and all("Prepared demo output" in (o.error or "") for o in obs)
    assert db.scalars(select(AuditLog).where(AuditLog.via == "demo")).first() is not None


def test_outcomes_are_computed_and_reflect_archetypes(seeded, db):
    by_arch = {}
    for p in db.scalars(select(WorkerProfile).where(WorkerProfile.data_origin == "synthetic")):
        plan = db.scalar(select(AssessmentPlan).where(AssessmentPlan.worker_id == p.id))
        rec = db.scalar(select(Recommendation).where(Recommendation.plan_id == plan.id)) if plan else None
        if rec:
            by_arch[p.archetype] = rec
    assert by_arch["safety_gaps"].outcome == "NOT_YET_READY"
    assert any(r["rule"] == "R2" and not r["passed"] for r in by_arch["safety_gaps"].rule_trace)
    assert by_arch["missing_evidence"].outcome == "REASSESSMENT_SUGGESTED" and by_arch["missing_evidence"].evidence_coverage < 0.5


def test_reset_raj_checkpoints_and_assessor(seeded, client):
    seen = {}
    for cp, status in (("fresh", "PROFILE_COMPLETE"), ("practical", "TASKS_IN_PROGRESS"), ("evidence_ready", "AI_EVIDENCE_REVIEWED"), ("awaiting_decision", "UNDER_ASSESSOR_REVIEW")):
        r = client.post("/api/v1/demo/raj", json={"checkpoint": cp})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["status"] == status and j["label"].startswith("SYNTHETIC")
        assert j["worker_session"]["user"]["full_name"] == "Raj Kumar" and j["assessor_session"]["user"]["assessor_code"] == "A01"
        seen[cp] = j["plan_id"]
    assert seen["fresh"] is None and seen["awaiting_decision"]
    h = {"Authorization": f"Bearer {j['assessor_session']['access_token']}"}
    rec = client.get(f"/api/v1/assessments/{seen['awaiting_decision']}/recommendation", headers=h).json()
    assert rec["outcome"] in ("ELIGIBLE", "NOT_YET_READY", "REASSESSMENT_SUGGESTED") and rec["rule_trace"]


def test_raj_prepared_observation_matches_spec_example(seeded, client):
    j = client.post("/api/v1/demo/raj", json={"checkpoint": "evidence_ready"}).json()
    h = {"Authorization": f"Bearer {j['assessor_session']['access_token']}"}
    ev = client.get(f"/api/v1/evidence?plan_id={j['plan_id']}", headers=h).json()
    c021 = next(e for e in ev if e["ai_observation"] and "Safety goggles not clearly visible" in e["ai_observation"]["output"]["potentially_missing"])
    o = c021["ai_observation"]
    assert o["simulated"] and o["confidence"] == 0.84 and "Electrical panel visible" in o["output"]["observed"]


def test_reset_touches_only_raj(seeded, db, client):
    others = {p.id for p in db.scalars(select(WorkerProfile).where(WorkerProfile.data_origin == "synthetic", WorkerProfile.full_name != "Raj Kumar"))}
    client.post("/api/v1/demo/raj", json={"checkpoint": "fresh"})
    db.expire_all()
    assert others <= {p.id for p in db.scalars(select(WorkerProfile).where(WorkerProfile.data_origin == "synthetic"))}
    assert db.scalar(select(User).where(User.login == "admin@demo.rpl")) is not None


def test_demo_evidence_pack_and_guard(seeded, client):
    st = client.get("/api/v1/demo/status").json()
    assert st["evidence_pack"] and st["synthetic_workers"] >= 1
    first = st["evidence_pack"][0]["upload_name"]
    r = client.get(f"/api/v1/demo/evidence/{first}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert client.get("/api/v1/demo/evidence/..%2F..%2Fworkers.csv").status_code == 404
    with pytest.raises(ValueError):
        demo.evidence_path("../workers.csv")


def test_demo_disabled_returns_404(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "demo_mode_enabled", False)
    assert client.post("/api/v1/demo/raj", json={"checkpoint": "fresh"}).status_code == 404
    assert client.get("/api/v1/demo/status").status_code == 404
