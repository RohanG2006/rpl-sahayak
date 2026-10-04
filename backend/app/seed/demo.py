"""Seed the SYNTHETIC demo dataset by driving the real API in-process.

Inputs come from data/demo/*.csv (scripts/generate_demo_data.py). Every derived value — extraction, qualification
match, readiness, results, recommendation — is computed by the application exactly as for a real user.
Workers are created directly as data_origin='synthetic' so every row they produce inherits that label; audit
entries written during seeding are marked via='demo'.
"""
from __future__ import annotations

import csv
import json
import threading
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.config import DATA_DIR
from app.core.ratelimit import limiter
from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.models import AssessmentPlan, AuditLog, Evidence, User, WorkerProfile
from app.services import audit, files

DEMO = DATA_DIR / "demo"
WORKER_PIN = "1234"  # synthetic worker accounts only (documented in README)
RAJ_KEY = "W001"
RAJ_ASSESSOR = "A01"
CHECKPOINTS = {  # Raj Kumar demo checkpoints → target workflow state
    "fresh": "PROFILE_COMPLETE",
    "practical": "TASKS_IN_PROGRESS_EMPTY",
    "evidence_ready": "AI_EVIDENCE_REVIEWED",
    "awaiting_decision": "UNDER_ASSESSOR_REVIEW",
}
ORDER = ["REGISTERED", "PROFILE_COMPLETE", "EXPERIENCE_DECLARED", "SKILLS_EXTRACTED", "SKILLS_CONFIRMED", "QUALIFICATION_MATCHED",
         "PLAN_CREATED", "READINESS_EVALUATED", "TASKS_IN_PROGRESS_EMPTY", "TASKS_IN_PROGRESS", "AI_EVIDENCE_REVIEWED",
         "ASSESSOR_SCORING", "UNDER_ASSESSOR_REVIEW", "DECIDED"]
AGREE = {"ELIGIBLE": "APPROVE", "NOT_YET_READY": "REJECT", "REASSESSMENT_SUGGESTED": "REASSESS"}
COMMENTS = {
    "APPROVE": "Competent across the assessed practical tasks; evidence and observation consistent. Approved for certification (synthetic assessor).",
    "REJECT": "Not yet competent in the assessed scope; see skill gaps. Advised to practise and re-apply (synthetic assessor).",
    "REASSESS": "Repeat the listed tasks with clear evidence before a final decision (synthetic assessor).",
}
_lock = threading.Lock()


def _rows(name: str) -> list[dict]:
    with (DEMO / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


def load_inputs() -> dict:
    by = lambda rows: _group(rows)  # noqa: E731
    return {"workers": _rows("workers.csv"), "experiences": by(_rows("experiences.csv")), "skills": by(_rows("skills.csv")),
            "assessments": {r["worker_key"]: r for r in _rows("assessments.csv")}, "tasks": by(_rows("task_scores.csv")),
            "evidence": by(_rows("evidence.csv")), "scores": by(_rows("assessor_scores.csv"))}


def _group(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        out[r["worker_key"]].append(r)
    return out


def _reached(target: str, stage: str) -> bool:
    return ORDER.index(target) >= ORDER.index(stage)


def _profile_body(w: dict) -> dict:
    body = {k: w[k] or None for k in ("full_name", "gender", "state", "district", "locality", "preferred_language", "occupation",
                                       "current_employer", "informal_training", "education_level")}
    body["age"] = int(w["age"])
    body["years_experience"] = float(w["years_experience"]) if w["years_experience"] else None
    body["has_science_maths"] = None if w["has_science_maths"] == "" else w["has_science_maths"] == "true"
    return body


def _ensure_worker(db: Session, w: dict) -> WorkerProfile:
    u = db.scalar(select(User).where(User.login == w["mobile"]))
    if not u:
        u = User(login=w["mobile"], password_hash=hash_password(WORKER_PIN), role_code="worker", full_name=w["full_name"],
                 preferred_language=w["preferred_language"], data_origin="synthetic")
        db.add(u)
        db.flush()
    p = WorkerProfile(user_id=u.id, full_name=w["full_name"], mobile=w["mobile"], preferred_language=w["preferred_language"],
                      archetype=w["archetype"], data_origin="synthetic")
    db.add(p)
    db.flush()
    audit.record(db, "worker.created", "worker_profile", p.id, actor=u, via="demo", summary="Synthetic demo candidate created")
    db.commit()
    return p


def _drive(c: TestClient, db: Session, w: dict, inp: dict, target: str, assessor_codes: dict[str, User], force_assessor: str | None = None) -> str | None:
    """Advance one synthetic worker to `target` through the public API. Returns the plan id (if any)."""
    key = w["worker_key"]
    prof = _ensure_worker(db, w)
    wid = prof.id
    H = {"Authorization": f"Bearer {create_access_token(prof.user_id, 'worker')[0]}"}

    def ok(r, what):
        if r.status_code >= 400:
            raise RuntimeError(f"{key} {what}: {r.status_code} {r.text[:300]}")
        return r.json()

    if not _reached(target, "PROFILE_COMPLETE"):
        return None
    ok(c.put(f"/api/v1/workers/{wid}", headers=H, json=_profile_body(w)), "profile")
    if not _reached(target, "EXPERIENCE_DECLARED"):
        return None
    e = inp["experiences"][key][0]
    ok(c.post(f"/api/v1/workers/{wid}/experience", headers=H, json={"raw_text": e["raw_text"], "language": e["language"]}), "experience")
    if not _reached(target, "SKILLS_EXTRACTED"):
        return None
    ext = ok(c.post(f"/api/v1/workers/{wid}/extract-skills", headers=H), "extract")
    if not _reached(target, "SKILLS_CONFIRMED"):
        return None
    items = [{"kind": s["kind"], "label": s["label"], "source": s["source"]} for s in inp["skills"].get(key, [])]
    ok(c.put(f"/api/v1/workers/{wid}/skills", headers=H, json={"skills": items, "ai_observation_id": ext["observation_id"]}), "confirm")
    if not _reached(target, "QUALIFICATION_MATCHED"):
        return None
    res = ok(c.post("/api/v1/qualifications/match", headers=H, json={"worker_id": wid}), "match")["results"]
    if not _reached(target, "PLAN_CREATED"):
        return None
    q = next(r for r in res if r["qualification_code"] == "DGT/1001")
    plan = ok(c.post("/api/v1/assessments", headers=H, json={"worker_id": wid, "qualification_id": q["qualification_id"]}), "plan")
    pid = plan["id"]
    if force_assessor:
        a = assessor_codes[force_assessor]
        db.execute(update(AssessmentPlan).where(AssessmentPlan.id == pid).values(assessor_id=a.id))
        audit.record(db, "assessment.assigned", "assessment_plan", pid, via="demo", summary=f"Demo persona assigned to {force_assessor}")
        db.commit()
    assessor = db.get(User, db.get(AssessmentPlan, pid).assessor_id)
    A = {"Authorization": f"Bearer {create_access_token(assessor.id, 'assessor')[0]}"}
    if not _reached(target, "READINESS_EVALUATED"):
        return pid
    sa = json.loads(inp["assessments"][key]["self_assessment"])
    ok(c.post(f"/api/v1/assessments/{pid}/self-assessment", headers=H, json={"responses": sa}), "self-assessment")
    if not _reached(target, "TASKS_IN_PROGRESS_EMPTY"):
        return pid
    ok(c.post(f"/api/v1/assessments/{pid}/start", headers=H), "start")
    if not _reached(target, "TASKS_IN_PROGRESS"):
        return pid
    tasks = {t["task_code"]: t for t in plan["tasks"]}
    for t in inp["tasks"].get(key, []):
        steps = {str(i): True for i in range(len(tasks[t["task_code"]]["steps"]))}
        ok(c.put(f"/api/v1/assessments/{pid}/tasks/{t['task_code']}/progress", headers=H,
                 json={"checklist_state": steps, "status": "SUBMITTED"}), f"task {t['task_code']}")
    if not _reached(target, "AI_EVIDENCE_REVIEWED"):
        return pid
    for ev in inp["evidence"].get(key, []):
        data = (DEMO / "evidence" / ev["base_image"]).read_bytes()
        up = ok(c.post("/api/v1/evidence", headers=H, files={"file": (ev["upload_name"], data, "image/png")},
                       data={"worker_id": wid, "plan_id": pid, "task_code": ev["task_code"], "criterion_code": ev["criterion_code"],
                             "purpose": "assessment", "caption": ev["caption"], "captured_offline": ev["captured_offline"]}), "evidence")
        ok(c.post(f"/api/v1/evidence/{up['id']}/analyze", headers=A), "analyze")
    if not _reached(target, "ASSESSOR_SCORING"):
        return pid
    by_task: dict[str, list[dict]] = defaultdict(list)
    crit_task = {c["criterion_code"]: t["task_code"] for t in plan["tasks"] for c in t["criteria"]}
    for s in inp["scores"].get(key, []):
        by_task[crit_task[s["criterion_code"]]].append({"criterion_code": s["criterion_code"], "final_score": int(s["final_score"]),
                                                       "assessor_note": s["assessor_note"]})
    for task_code, scores in by_task.items():
        ok(c.post(f"/api/v1/assessments/{pid}/tasks/{task_code}/score", headers=A, json={"scores": scores}), f"score {task_code}")
    if not _reached(target, "UNDER_ASSESSOR_REVIEW"):
        return pid
    rec = ok(c.post(f"/api/v1/assessments/{pid}/recommendation", headers=A), "recommendation")
    if not _reached(target, "DECIDED"):
        return pid
    policy = inp["assessments"][key]["decision_policy"]
    decision = AGREE[rec["outcome"]] if policy == "follow" else policy
    reassess = []
    if decision == "REASSESS":
        res_ = ok(c.get(f"/api/v1/competencies/{pid}", headers=A), "results")["tasks"]
        reassess = [k for k, v in sorted(res_.items(), key=lambda kv: kv[1]["task_pct"] or 0)[:2]]
    ok(c.post("/api/v1/assessor/decision", headers=A, json={"plan_id": pid, "decision": decision, "comments": COMMENTS[decision],
                                                            "reassess_task_codes": reassess}), "decision")
    return pid


def _purge_worker(db: Session, prof: WorkerProfile) -> None:
    for e in db.scalars(select(Evidence).where(Evidence.worker_id == prof.id)):
        if e.storage_path:
            try:
                files.path_of(e.storage_path).unlink(missing_ok=True)
            except Exception:
                pass
    db.execute(delete(WorkerProfile).where(WorkerProfile.id == prof.id))  # DB cascades plans, evidence, scores, AI notes…


def seed_demo(reset: bool = False, only: set[str] | None = None, raj_target: str = "UNDER_ASSESSOR_REVIEW") -> dict:
    """Create all synthetic workers (idempotent; `reset` rebuilds them)."""
    import logging
    from app.main import app
    logging.getLogger("httpx").setLevel(logging.WARNING)
    inp = load_inputs()
    started = datetime.now(timezone.utc)
    made, skipped = 0, 0
    with _lock, SessionLocal() as db:
        assessors = {u.assessor_code: u for u in db.scalars(select(User).where(User.role_code == "assessor", User.is_active.is_(True)))}
        was = limiter.enabled
        limiter.enabled = False  # seeding issues hundreds of requests from one client
        try:
            c = TestClient(app)
            for w in inp["workers"]:
                if only and w["worker_key"] not in only:
                    continue
                existing = db.scalar(select(WorkerProfile).join(User, User.id == WorkerProfile.user_id).where(User.login == w["mobile"]))
                if existing and not reset:
                    skipped += 1
                    continue
                if existing:
                    _purge_worker(db, existing)
                    db.commit()
                is_raj = w["worker_key"] == RAJ_KEY
                _drive(c, db, w, inp, raj_target if is_raj else w["target_status"], assessors, RAJ_ASSESSOR if is_raj else None)
                made += 1
        finally:
            limiter.enabled = was
        db.execute(update(AuditLog).where(AuditLog.at >= started).values(via="demo"))
        db.commit()
    return {"created": made, "skipped": skipped}


def reset_raj(checkpoint: str) -> dict:
    """Rebuild the synthetic Raj Kumar persona at a demo checkpoint. Touches only that synthetic account."""
    if checkpoint not in CHECKPOINTS:
        raise ValueError(f"checkpoint must be one of {sorted(CHECKPOINTS)}")
    seed_demo(reset=True, only={RAJ_KEY}, raj_target=CHECKPOINTS[checkpoint])
    with SessionLocal() as db:
        raj = next(w for w in load_inputs()["workers"] if w["worker_key"] == RAJ_KEY)
        u = db.scalar(select(User).where(User.login == raj["mobile"]))
        prof = db.scalar(select(WorkerProfile).where(WorkerProfile.user_id == u.id))
        plan = db.scalar(select(AssessmentPlan).where(AssessmentPlan.worker_id == prof.id))
        a = db.scalar(select(User).where(User.assessor_code == RAJ_ASSESSOR))
        return {"checkpoint": checkpoint, "worker_id": prof.id, "plan_id": plan.id if plan else None, "status": plan.status if plan else prof.status,
                "worker_user_id": u.id, "assessor_user_id": a.id}


def demo_evidence_pack() -> list[dict]:
    """Raj's placeholder images (for uploading live during the demo)."""
    return [r for r in load_inputs()["evidence"].get(RAJ_KEY, [])]


def evidence_path(base_image: str) -> Path:
    p = (DEMO / "evidence" / base_image).resolve()
    if p.parent != (DEMO / "evidence").resolve():
        raise ValueError("invalid image")
    return p
