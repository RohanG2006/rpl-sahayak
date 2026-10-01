"""Phase 3: worker registration, profile, versioned declaration, AI extraction as suggestion, confirmation."""
import uuid

from sqlalchemy import select

from app.models import AIObservation, AuditLog, WorkerExperience, WorkerSkill

RAJ = ("I have worked as an electrician for six years. I install wiring, switches, fans, MCBs and troubleshoot "
       "electrical faults. I learned most of this work while working with my uncle.")


def new_mobile() -> str:
    return "9" + str(uuid.uuid4().int)[:9]


def register(client, **extra):
    body = {"full_name": "Test Worker", "mobile": new_mobile(), "pin": "4321", "preferred_language": "hi", **extra}
    r = client.post("/api/v1/workers", json=body)
    assert r.status_code == 201, r.text
    j = r.json()
    return j["worker"], {"Authorization": f"Bearer {j['access_token']}"}


def test_self_registration_returns_token_and_status(client):
    w, h = register(client)
    assert w["status"] == "REGISTERED" and w["ncvet_stage"] == "Enrolment"
    assert client.get(f"/api/v1/workers/{w['id']}", headers=h).json()["full_name"] == "Test Worker"


def test_registration_requires_pin_without_token(client):
    r = client.post("/api/v1/workers", json={"full_name": "No Pin", "mobile": new_mobile()})
    assert r.status_code == 403


def test_invalid_mobile_rejected(client):
    r = client.post("/api/v1/workers", json={"full_name": "X Y", "mobile": "12345", "pin": "1111"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_profile_complete_transition(client):
    w, h = register(client)
    r = client.put(f"/api/v1/workers/{w['id']}", headers=h, json={
        "age": 29, "state": "Bihar", "district": "Patna", "occupation": "Electrician", "years_experience": 6,
        "education_level": "10th"})
    assert r.status_code == 200 and r.json()["status"] == "PROFILE_COMPLETE"


def test_worker_cannot_read_another_worker(client):
    w1, _ = register(client)
    _, h2 = register(client)
    assert client.get(f"/api/v1/workers/{w1['id']}", headers=h2).status_code == 403


def test_assessor_can_enrol_on_behalf_and_mobile_is_masked(client, assessor_headers):
    m = new_mobile()
    r = client.post("/api/v1/workers", headers=assessor_headers, json={"full_name": "Field Enrolled", "mobile": m})
    assert r.status_code == 201 and r.json()["access_token"] is None
    assert r.json()["worker"]["mobile"] == "XXXXXX" + m[-4:]


def test_extraction_is_suggestion_only_and_needs_declaration(client, db):
    w, h = register(client)
    r = client.post(f"/api/v1/workers/{w['id']}/extract-skills", headers=h)
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_workflow_state"

    assert client.post(f"/api/v1/workers/{w['id']}/experience", headers=h, json={"raw_text": RAJ}).status_code == 201
    r = client.post(f"/api/v1/workers/{w['id']}/extract-skills", headers=h)
    assert r.status_code == 200
    j = r.json()
    labels = {s["label"] for s in j["extraction"]["skills"]}
    assert {"House wiring installation", "Switch and socket installation", "Fan installation and repair",
            "MCB / circuit breaker installation", "Electrical fault diagnosis"} <= labels
    assert j["extraction"]["experience_years"] == 6 and j["extraction"]["occupation"] == "Electrician"
    assert "Informal apprenticeship" in {m["label"] for m in j["extraction"]["learning_mode"]}
    assert j["applied"] is False and "assessor verification required" in j["advisory"]
    assert all(s["source_text"] for s in j["extraction"]["skills"])
    # nothing written to worker skills until the worker confirms
    assert db.scalars(select(WorkerSkill).where(WorkerSkill.worker_id == w["id"])).all() == []
    assert db.get(AIObservation, j["observation_id"]).kind == "skill_extraction"


def test_declaration_is_versioned_never_overwritten(client, db):
    w, h = register(client)
    client.post(f"/api/v1/workers/{w['id']}/experience", headers=h, json={"raw_text": "First version of my work as electrician."})
    client.post(f"/api/v1/workers/{w['id']}/experience", headers=h, json={"raw_text": RAJ})
    rows = db.scalars(select(WorkerExperience).where(WorkerExperience.worker_id == w["id"]).order_by(WorkerExperience.version)).all()
    assert [r.version for r in rows] == [1, 2] and rows[0].raw_text.startswith("First version")


def test_confirm_skills_records_human_edits(client, db):
    w, h = register(client)
    client.post(f"/api/v1/workers/{w['id']}/experience", headers=h, json={"raw_text": RAJ})
    ext = client.post(f"/api/v1/workers/{w['id']}/extract-skills", headers=h).json()
    keep = [s for s in ext["extraction"]["skills"] if s["label"] != "Fan installation and repair"]
    body = {"skills": [{"kind": "skill", "label": s["label"], "source": "ai", "confidence": s["confidence"]} for s in keep]
            + [{"kind": "skill", "label": "Earthing installation", "source": "worker"}],
            "years_experience": 6, "ai_observation_id": ext["observation_id"]}
    r = client.put(f"/api/v1/workers/{w['id']}/skills", headers=h, json=body)
    assert r.status_code == 200 and r.json()["status"] == "SKILLS_CONFIRMED"
    assert {s["source"] for s in r.json()["skills"]} == {"ai", "worker"}
    log = db.scalar(select(AuditLog).where(AuditLog.entity_id == w["id"], AuditLog.action == "skills.confirmed"))
    assert "skill:Fan installation and repair" in log.after["removed_ai_items"]
    assert "skill:Earthing installation" in log.after["added_by_human"]


def test_redeclaration_after_confirmation_resets_state(client):
    w, h = register(client)
    client.post(f"/api/v1/workers/{w['id']}/experience", headers=h, json={"raw_text": RAJ})
    client.put(f"/api/v1/workers/{w['id']}/skills", headers=h, json={"skills": [{"kind": "skill", "label": "Wiring"}]})
    client.post(f"/api/v1/workers/{w['id']}/experience", headers=h, json={"raw_text": RAJ + " I also do earthing."})
    assert client.get(f"/api/v1/workers/{w['id']}", headers=h).json()["status"] == "EXPERIENCE_DECLARED"


def test_audit_does_not_store_pii(client, db):
    w, h = register(client, full_name="Secret Name")
    client.put(f"/api/v1/workers/{w['id']}", headers=h, json={"full_name": "Another Secret", "locality": "Hidden Lane"})
    log = db.scalar(select(AuditLog).where(AuditLog.entity_id == w["id"], AuditLog.action == "worker.updated"))
    assert "Another Secret" not in str(log.after) and "Hidden Lane" not in str(log.after)
