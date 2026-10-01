"""Phase 6: evidence upload validation, traceability, AI evidence assistance (rules + stub LLM), document claims."""
import io
import json
import uuid

from PIL import Image
from sqlalchemy import select

from app.ai.service import AIService, get_ai_service
from app.main import app
from app.models import AuditLog, AssessorScore
from tests.conftest import login, make_worker

DOMESTIC = ["House wiring installation", "Switch and socket installation", "MCB / circuit breaker installation"]
EMAIL = {"A01": "assessor1@demo.rpl", "A02": "assessor2@demo.rpl", "A03": "assessor3@demo.rpl", "A04": "assessor4@demo.rpl", "A05": "assessor5@demo.rpl"}


def png(color=(200, 200, 200), size=(800, 600)) -> bytes:
    img = Image.new("RGB", size, color)
    for x in range(0, size[0], 20):  # stripes → edges so the sharpness heuristic has signal
        for y in range(size[1]):
            img.putpixel((x, y), (20, 20, 20))
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()


def started_plan(client):
    wid, h = make_worker(client, skills=DOMESTIC)
    res = client.post("/api/v1/qualifications/match", headers=h, json={"worker_id": wid}).json()["results"]
    q = next(r for r in res if r["qualification_code"] == "DGT/1001")
    p = client.post("/api/v1/assessments", headers=h, json={"worker_id": wid, "qualification_id": q["qualification_id"]}).json()
    scope = sorted({lo for t in p["tasks"] for lo in t["lo_numbers"]})
    client.post(f"/api/v1/assessments/{p['id']}/self-assessment", headers=h, json={"responses": {str(lo): "regularly" for lo in scope}})
    p = client.post(f"/api/v1/assessments/{p['id']}/start", headers=h).json()
    return p, wid, h, login(client, EMAIL[p["assessor"]["code"]])


def upload(client, h, wid, plan_id, data, *, name="photo.png", ctype="image/png", criterion="C04.2", op=None, purpose="assessment", doc_type=None):
    form = {"worker_id": wid, "purpose": purpose, "caption": "Open switch showing terminations"}
    if purpose == "assessment":
        form.update({"plan_id": plan_id, "criterion_code": criterion})
    if doc_type:
        form["doc_type"] = doc_type
    if op:
        form["client_op_id"] = op
    return client.post("/api/v1/evidence", headers=h, data=form, files={"file": (name, data, ctype)})


def test_upload_links_to_criterion_and_advances_state(client):
    p, wid, h, ah = started_plan(client)
    r = upload(client, h, wid, p["id"], png())
    assert r.status_code == 201, r.text
    ev = r.json()
    assert ev["kind"] == "image" and ev["mime"] == "image/png" and len(ev["sha256"]) == 64
    plan = client.get(f"/api/v1/assessments/{p['id']}", headers=ah).json()
    assert plan["status"] == "EVIDENCE_SUBMITTED"
    crit = next(c for t in plan["tasks"] for c in t["criteria"] if c["criterion_code"] == "C04.2")
    assert crit["evidence_ids"] == [ev["id"]]
    f = client.get(f"/api/v1/evidence/{ev['id']}/file", headers=ah)
    assert f.status_code == 200 and f.headers["content-type"] == "image/png"


def test_spoofed_content_type_is_rejected(client):
    p, wid, h, _ = started_plan(client)
    r = upload(client, h, wid, p["id"], b"MZ\x90\x00 this is an exe pretending", name="x.jpg", ctype="image/jpeg")
    assert r.status_code == 415 and r.json()["error"]["code"] == "invalid_evidence"


def test_size_limit(client, monkeypatch):
    from app.core.config import get_settings
    p, wid, h, _ = started_plan(client)
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    r = upload(client, h, wid, p["id"], png())
    assert r.status_code == 413 and r.json()["error"]["code"] == "upload_too_large"


def test_unknown_criterion_and_idempotent_retry(client):
    p, wid, h, _ = started_plan(client)
    assert upload(client, h, wid, p["id"], png(), criterion="C99.9").status_code == 404
    op = str(uuid.uuid4())
    a = upload(client, h, wid, p["id"], png(), op=op).json()
    b = upload(client, h, wid, p["id"], png(), op=op).json()
    assert a["id"] == b["id"] and b["duplicate"] is True


def test_rules_analysis_never_suggests_a_score(client):
    p, wid, h, ah = started_plan(client)
    ev = upload(client, h, wid, p["id"], png()).json()
    r = client.post(f"/api/v1/evidence/{ev['id']}/analyze", headers=ah)
    assert r.status_code == 200
    o = r.json()["ai_observation"]
    assert o["provider"] == "rules" and o["output"]["suggested_score"] is None
    assert o["output"]["analysis_basis"] == "metadata_only"
    assert "assessor verification required" in o["advisory"]
    assert any("Resolution 800×600" in x for x in o["output"]["observed"])
    # worker view never includes suggested score fields
    w = client.get(f"/api/v1/evidence?plan_id={p['id']}", headers=h).json()[0]["ai_observation"]["output"]
    assert "suggested_score" not in w


def test_dark_image_flagged(client):
    p, wid, h, ah = started_plan(client)
    ev = upload(client, h, wid, p["id"], png(color=(5, 5, 5))).json()
    o = client.post(f"/api/v1/evidence/{ev['id']}/analyze", headers=ah).json()["ai_observation"]["output"]
    assert any("dark" in m for m in o["potentially_missing"])


class StubVision:
    name, model = "stub", "stub-vision"

    def complete_json(self, system, user, json_schema, images=None):
        assert images and images[0].mime == "image/png"
        return json.dumps({"observed": ["Switch terminals visible", "Phase conductor in switch"],
                           "potentially_missing": ["Earth terminal of socket not clearly visible"],
                           "safety_concerns": [], "competency_indicators": ["Neat terminations"],
                           "suggested_score": 3, "suggested_score_reason": "Matches anchor 3", "confidence": 0.84,
                           "analysis_basis": "image"})


def test_llm_suggestion_is_stored_separately_and_override_is_audited(client, db, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "ai_send_evidence", True)
    app.dependency_overrides[get_ai_service] = lambda: AIService(StubVision())
    try:
        p, wid, h, ah = started_plan(client)
        ev = upload(client, h, wid, p["id"], png()).json()
        o = client.post(f"/api/v1/evidence/{ev['id']}/analyze", headers=ah).json()["ai_observation"]
        assert o["provider"] == "stub" and o["output"]["suggested_score"] == 3 and o["confidence"] == 0.84
    finally:
        app.dependency_overrides.clear()
    plan = client.get(f"/api/v1/assessments/{p['id']}", headers=ah).json()
    assert plan["status"] == "AI_EVIDENCE_REVIEWED"
    crit = next(c for t in plan["tasks"] for c in t["criteria"] if c["criterion_code"] == "C04.2")
    assert crit["score"]["ai_suggested_score"] == 3 and crit["score"]["final_score"] is None  # AI never finalises
    # assessor overrides
    r = client.post(f"/api/v1/assessments/{p['id']}/tasks/T04/score", headers=ah,
                    json={"scores": [{"criterion_code": "C04.2", "final_score": 2, "assessor_note": "Earth not connected"}]})
    crit = next(c for t in r.json()["tasks"] for c in t["criteria"] if c["criterion_code"] == "C04.2")
    assert crit["score"]["final_score"] == 2 and crit["score"]["overrode_ai"] is True
    row = db.scalar(select(AssessorScore).where(AssessorScore.plan_id == p["id"], AssessorScore.final_score == 2))
    assert row.evidence_ids == [ev["id"]]  # Score → Criterion → Evidence traceability
    assert db.scalar(select(AuditLog).where(AuditLog.entity_id == p["id"], AuditLog.action == "score.overridden_ai"))
    # worker never sees the suggestion
    wcrit = next(c for t in client.get(f"/api/v1/assessments/{p['id']}", headers=h).json()["tasks"] for c in t["criteria"] if c["criterion_code"] == "C04.2")
    assert wcrit["score"]["ai_suggested_score"] is None


def test_other_assessor_cannot_access_evidence(client):
    p, wid, h, ah = started_plan(client)
    ev = upload(client, h, wid, p["id"], png()).json()
    other = login(client, EMAIL["A05"] if p["assessor"]["code"] != "A05" else EMAIL["A04"])
    assert client.get(f"/api/v1/evidence/{ev['id']}/file", headers=other).status_code == 403


def test_document_claims_from_pdf(client):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 750, "Experience letter. Mr Test worked as electrician with Shakti Electricals for 5 years.")
    c.drawString(72, 730, "He does house wiring, MCB installation and fault finding.")
    c.save()
    wid, h = make_worker(client, skills=DOMESTIC)
    ev = upload(client, h, wid, None, buf.getvalue(), name="letter.pdf", ctype="application/pdf", purpose="document", doc_type="experience_letter").json()
    assert ev["kind"] == "document"
    r = client.post(f"/api/v1/evidence/{ev['id']}/analyze", headers=h).json()
    labels = [x["label"] for x in r["extracted_claims"]]
    assert "Experience stated: 5 years" in labels and any("electrician" in x.lower() for x in labels)
    r = client.put(f"/api/v1/evidence/{ev['id']}/claims", headers=h, json={"claims": r["extracted_claims"][:2]})
    assert r.json()["claims_confirmed"] is True
