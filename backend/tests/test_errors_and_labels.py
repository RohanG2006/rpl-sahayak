"""Spec §47 error states, R23 data-origin labelling, and workflow state-machine rules."""
import csv
import json

import pytest
from sqlalchemy import select

from app.core.config import DATA_DIR
from app.core.errors import InvalidState
from app.models import ConsistencyRating, Qualification, QualificationCompetency, User, WorkerProfile
from app.services import workflow
from tests.conftest import make_worker
from tests.flows import started_plan


# ---- §47 error states (each must be a typed JSON error, never a stack trace) -----------------------
def _is_typed(r, status, code=None):
    j = r.json()
    assert r.status_code == status, r.text
    assert set(j) == {"error"} and {"code", "message", "details"} <= set(j["error"])
    assert "Traceback" not in r.text
    if code:
        assert j["error"]["code"] == code


def test_upload_failures_are_typed(client):
    p, wid, h, _ = started_plan(client)
    up = lambda data, name="x.png", ctype="image/png", **f: client.post(
        "/api/v1/evidence", headers=h, data={"worker_id": wid, "plan_id": p["id"], "purpose": "assessment", **f},
        files={"file": (name, data, ctype)})
    _is_typed(up(b""), 415, "invalid_evidence")                                  # empty file
    _is_typed(up(b"just text pretending"), 415, "invalid_evidence")              # wrong type
    _is_typed(up(b"\x89PNG\r\n\x1a\n" + b"0" * 20, criterion_code="C99.9"), 404)  # unknown criterion
    r = client.post("/api/v1/evidence", headers=h, data={"worker_id": wid, "purpose": "document", "doc_type": "passport"},
                    files={"file": ("d.pdf", b"%PDF-1.4 test", "application/pdf")})
    _is_typed(r, 409, "validation_error")                                         # unsupported document type


def test_evidence_before_practical_starts_is_rejected(client):
    wid, h = make_worker(client, skills=["House wiring installation"])
    res = client.post("/api/v1/qualifications/match", headers=h, json={"worker_id": wid}).json()["results"]
    q = next(r for r in res if r["qualification_code"] == "DGT/1001")
    p = client.post("/api/v1/assessments", headers=h, json={"worker_id": wid, "qualification_id": q["qualification_id"]}).json()
    r = client.post("/api/v1/evidence", headers=h, data={"worker_id": wid, "plan_id": p["id"], "purpose": "assessment"},
                    files={"file": ("x.png", b"\x89PNG\r\n\x1a\n0000", "image/png")})
    _is_typed(r, 409, "invalid_workflow_state")


def test_qualification_unavailable_and_unauthorized(client, assessor_headers):
    _is_typed(client.get("/api/v1/qualifications/NOT-A-CODE", headers=assessor_headers), 404, "qualification_unavailable")
    _is_typed(client.get("/api/v1/qualifications", headers={"Authorization": "Bearer not-a-jwt"}), 401, "unauthorized")


def test_validation_errors_list_fields(client):
    r = client.post("/api/v1/workers", json={"full_name": "A", "mobile": "123", "pin": "1"})
    _is_typed(r, 422, "validation_error")
    locs = [".".join(f["loc"]) for f in r.json()["error"]["details"]["fields"]]
    assert any("full_name" in l for l in locs) and any("mobile" in l for l in locs)


def test_ai_unavailable_without_fallback_is_503(client, monkeypatch):
    from app.ai.service import AIService
    from app.ai.schemas import NarrativeOut
    from app.core.errors import AIUnavailable

    class Down:
        name, model = "down", None

        def complete_json(self, *a, **k):
            from app.ai.providers.base import ProviderError
            raise ProviderError("timeout")

    with pytest.raises(AIUnavailable) as e:
        AIService(Down())._run("x", "recommendation", {}, NarrativeOut, None)
    assert e.value.status == 503 and "assessor can review manually" in e.value.message


# ---- R23: every row carries a truthful data_origin ------------------------------------------------
def test_official_data_is_labelled_official(db):
    assert {q.data_origin for q in db.scalars(select(Qualification))} == {"official"}
    assert {c.data_origin for c in db.scalars(select(QualificationCompetency))} == {"official"}


def test_seeded_staff_are_synthetic_and_user_data_is_user(db, client):
    seeded = db.scalars(select(User).where(User.login.like("%@demo.rpl"))).all()
    assert seeded and all(u.data_origin == "synthetic" for u in seeded if u.login.startswith(("assessor", "admin")))
    wid, _ = make_worker(client, skills=["House wiring installation"])
    assert db.get(WorkerProfile, wid).data_origin == "user"


def test_simulation_dataset_labelled_everywhere(db):
    from app.seed.consistency import load_consistency
    load_consistency(db)
    db.commit()
    assert {r.data_origin for r in db.scalars(select(ConsistencyRating).limit(500))} == {"simulation"}
    path = DATA_DIR / "demo" / "consistency_test_set.csv"
    first = path.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("# SIMULATION / TEST DATA")
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(l for l in f if not l.startswith("#")))
    assert {r["data_origin"] for r in rows} == {"simulation"}
    meta = json.loads((DATA_DIR / "demo" / "consistency_parameters.json").read_text(encoding="utf-8"))
    assert "NOT real assessor data" in meta["label"]


# ---- Workflow state machine ------------------------------------------------------------------------
class _W:
    def __init__(self, status):
        self.status, self.id = status, "w"


class _DB:
    def __init__(self):
        self.added = []

    def add(self, x):
        self.added.append(x)


def test_states_only_move_forward_unless_reset():
    w = _W("SKILLS_CONFIRMED")
    workflow.advance_worker(_DB(), w, "EXPERIENCE_DECLARED", None)
    assert w.status == "SKILLS_CONFIRMED"  # no silent regression
    workflow.advance_worker(_DB(), w, "EXPERIENCE_DECLARED", None, reset=True)
    assert w.status == "EXPERIENCE_DECLARED"


def test_transitions_are_audited_and_guards_raise():
    d = _DB()
    w = _W("REGISTERED")
    workflow.advance_worker(d, w, "PROFILE_COMPLETE", None)
    assert d.added and d.added[0].action == "workflow.worker_state" and d.added[0].after == {"status": "PROFILE_COMPLETE"}
    with pytest.raises(InvalidState):
        workflow.require_worker_at_least(w, "SKILLS_CONFIRMED", "match")
    with pytest.raises(InvalidState):
        workflow.advance_worker(d, w, "NOT_A_STATE", None)


def test_every_state_maps_to_an_ncvet_stage():
    assert set(workflow.NCVET_STAGE) == set(workflow.WORKER_STATES) | set(workflow.PLAN_STATES)
