import io

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.service import ADVISORY, AIService, get_ai_service
from app.api.deps import ensure_worker_access, get_current_user
from app.core.config import get_settings
from app.core.errors import Forbidden, InvalidState, NotFound
from app.core.ratelimit import limiter
from app.db.session import get_db
from app.models import AIObservation, AssessmentAttempt, AssessmentPlan, AssessorScore, Evidence, User, WorkerProfile
from app.services import audit, files, workflow
from app.services.demo_prepared import prepared_observation
from app.services.results import plan_tasks

router = APIRouter(tags=["evidence"])

DOC_TYPES = ("resume", "experience_letter", "certificate", "id_placeholder", "other")


def evidence_out(e: Evidence, viewer: User, obs: AIObservation | None = None) -> dict:
    staff = viewer.role_code in ("assessor", "admin")
    out = {
        "id": e.id, "plan_id": e.plan_id, "worker_id": e.worker_id, "criterion_id": e.criterion_id, "purpose": e.purpose,
        "doc_type": e.doc_type, "kind": e.kind, "mime": e.mime, "size_bytes": e.size_bytes, "sha256": e.sha256,
        "caption": e.caption, "captured_offline": e.captured_offline, "upload_status": e.upload_status,
        "data_origin": e.data_origin, "created_at": e.created_at.isoformat(), "file_url": f"/evidence/{e.id}/file",
        "extracted_claims": e.extracted_claims, "claims_confirmed": e.claims_confirmed,
    }
    if obs:
        data = dict(obs.output)
        if not staff:
            data.pop("suggested_score", None)
            data.pop("suggested_score_reason", None)
        out["ai_observation"] = {"id": obs.id, "provider": obs.provider, "model": obs.model, "fallback_used": obs.fallback_used,
                                 "confidence": obs.confidence, "advisory": ADVISORY, "output": data,
                                 "simulated": obs.provider == "demo-prepared", "error": obs.error if staff else None}
    return out


def _latest_obs(db: Session, evidence_id: str) -> AIObservation | None:
    return db.scalar(select(AIObservation).where(AIObservation.evidence_id == evidence_id).order_by(AIObservation.created_at.desc()))


@router.post("/evidence", status_code=201)
@limiter.limit("60/minute")
async def upload_evidence(
    request: Request,
    file: UploadFile = File(...),
    worker_id: str = Form(...),
    plan_id: str | None = Form(default=None),
    task_code: str | None = Form(default=None),
    criterion_code: str | None = Form(default=None),
    purpose: str = Form(default="assessment"),
    doc_type: str | None = Form(default=None),
    caption: str | None = Form(default=None, max_length=500),
    captured_offline: bool = Form(default=False),
    client_op_id: str | None = Form(default=None, max_length=36),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload assessment evidence (linked to a criterion) or a supporting document. Validated by magic bytes and size.
    Idempotent on `client_op_id` (offline sync retries)."""
    w = db.get(WorkerProfile, worker_id)
    if not w:
        raise NotFound("Worker not found.")
    ensure_worker_access(user, w)
    if client_op_id:
        dup = db.scalar(select(Evidence).where(Evidence.client_op_id == client_op_id))
        if dup:
            return {**evidence_out(dup, user), "duplicate": True}
    if purpose not in ("assessment", "document"):
        raise InvalidState("purpose must be 'assessment' or 'document'.", code="validation_error")
    criterion = attempt = None
    if purpose == "assessment":
        if not plan_id:
            raise InvalidState("plan_id is required for assessment evidence.", code="validation_error")
        p = db.get(AssessmentPlan, plan_id)
        if not p or p.worker_id != w.id:
            raise NotFound("Assessment not found for this worker.")
        workflow.require_plan_at_least(p, "TASKS_IN_PROGRESS", "upload evidence")
        workflow.require_plan_before(p, "DECIDED", "upload evidence")
        tasks = plan_tasks(db, p)
        task = next((t for t in tasks if t.task_code == task_code), None) if task_code else None
        if criterion_code:
            pair = next(((t, c) for t in tasks for c in t.criteria if c.criterion_code == criterion_code), None)
            if not pair:
                raise NotFound(f"Criterion {criterion_code} is not part of this assessment.")
            task, criterion = pair
        if task:
            attempt = db.scalar(select(AssessmentAttempt).where(AssessmentAttempt.plan_id == p.id, AssessmentAttempt.task_id == task.id))
    elif doc_type not in DOC_TYPES:
        raise InvalidState(f"doc_type must be one of {', '.join(DOC_TYPES)}.", code="validation_error")

    data, mime, kind, ext, sha = await files.read_validated(file)
    rel = files.store(w.id, data, ext)
    e = Evidence(plan_id=plan_id if purpose == "assessment" else None, worker_id=w.id, attempt_id=attempt.id if attempt else None,
                 criterion_id=criterion.id if criterion else None, purpose=purpose, doc_type=doc_type, kind=kind, mime=mime,
                 size_bytes=len(data), sha256=sha, storage_path=rel, original_name=(file.filename or "")[:200],
                 caption=caption, captured_offline=captured_offline, client_op_id=client_op_id, data_origin=w.data_origin)
    db.add(e)
    db.flush()
    if purpose == "assessment":
        workflow.advance_plan(db, p, "EVIDENCE_SUBMITTED", user)
    audit.record(db, "evidence.uploaded", "evidence", e.id, actor=user, via="sync" if captured_offline else "online",
                 summary=f"{kind} {len(data) // 1024} KB" + (f" → {criterion.criterion_code}" if criterion else f" ({doc_type or purpose})"))
    db.commit()
    return evidence_out(e, user)


@router.get("/evidence")
def list_evidence(worker_id: str | None = None, plan_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Evidence).order_by(Evidence.created_at.desc())
    if plan_id:
        p = db.get(AssessmentPlan, plan_id)
        if not p:
            raise NotFound("Assessment not found.")
        if user.role_code == "worker":
            ensure_worker_access(user, db.get(WorkerProfile, p.worker_id))
        elif user.role_code == "assessor" and p.assessor_id != user.id:
            raise Forbidden("This candidate is assigned to another assessor.")
        stmt = stmt.where(Evidence.plan_id == plan_id)
    elif worker_id:
        w = db.get(WorkerProfile, worker_id)
        if not w:
            raise NotFound("Worker not found.")
        ensure_worker_access(user, w)
        stmt = stmt.where(Evidence.worker_id == worker_id)
    elif user.role_code == "worker":
        stmt = stmt.join(WorkerProfile, WorkerProfile.id == Evidence.worker_id).where(WorkerProfile.user_id == user.id)
    else:
        raise InvalidState("Pass worker_id or plan_id.", code="validation_error")
    return [evidence_out(e, user, _latest_obs(db, e.id)) for e in db.scalars(stmt.limit(200))]


def _load(db: Session, evidence_id: str, user: User) -> Evidence:
    e = db.get(Evidence, evidence_id)
    if not e:
        raise NotFound("Evidence not found.")
    if user.role_code == "worker":
        ensure_worker_access(user, db.get(WorkerProfile, e.worker_id))
    elif user.role_code == "assessor" and e.plan_id:
        p = db.get(AssessmentPlan, e.plan_id)
        if p.assessor_id != user.id:
            raise Forbidden("This candidate is assigned to another assessor.")
    return e


@router.get("/evidence/{evidence_id}/file")
def evidence_file(evidence_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    e = _load(db, evidence_id, user)
    if not e.storage_path:
        raise NotFound("No file stored for this evidence.")
    return FileResponse(files.path_of(e.storage_path), media_type=e.mime, headers={"Cache-Control": "private, max-age=86400"})


@router.post("/evidence/{evidence_id}/analyze")
@limiter.limit(get_settings().rate_limit_ai)
def analyze(request: Request, evidence_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user),
            ai: AIService = Depends(get_ai_service)):
    """AI evidence assistance. Output is advisory: observations + (assessor-only) suggested score stored separately
    from the assessor's final score."""
    e = _load(db, evidence_id, user)
    data = files.path_of(e.storage_path).read_bytes() if e.storage_path else None
    crit_d = task_d = None
    required: list[dict] = []
    uploaded_kinds: list[str] = []
    p = db.get(AssessmentPlan, e.plan_id) if e.plan_id else None
    if e.purpose == "document":
        text = None
        if e.kind == "document" and data:
            try:
                from pypdf import PdfReader
                text = "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(data)).pages[:5])[:8000]
            except Exception:
                text = None
        res = ai.extract_document_claims(e.doc_type or "other", text, (e.mime, data) if e.kind == "image" and data else None)
        e.extracted_claims = [c.model_dump() for c in res.data.claims]
        kind = "document_claims"
    else:
        if e.criterion_id and p:
            for t in plan_tasks(db, p):
                for c in t.criteria:
                    if c.id == e.criterion_id:
                        crit_d = {"code": c.criterion_code, "text": c.text, "anchors": c.anchors, "evidence_hint": c.evidence_hint}
                        task_d = {"code": t.task_code, "title": t.title, "description": t.description}
                        required = [r for r in t.evidence_required if r["criterion"] == c.criterion_code]
            uploaded_kinds = list(db.scalars(select(Evidence.kind).where(Evidence.plan_id == p.id, Evidence.criterion_id == e.criterion_id)))
        prepared = prepared_observation(e)
        res = prepared or ai.analyze_evidence(data=data, mime=e.mime, kind=e.kind, size_bytes=e.size_bytes, caption=e.caption,
                                              criterion=crit_d, task=task_d, required=required, uploaded_kinds_for_criterion=uploaded_kinds)
        kind = "evidence_analysis"
    obs = AIObservation(plan_id=e.plan_id, worker_id=e.worker_id, evidence_id=e.id, kind=kind, provider=res.provider,
                        model=res.model, prompt_file=res.prompt_file, prompt_version=res.prompt_version,
                        output=res.data.model_dump(), confidence=res.confidence, valid=res.valid,
                        fallback_used=res.fallback_used, attempts=res.attempts, error=res.error, data_origin=e.data_origin)
    db.add(obs)
    db.flush()
    suggested = getattr(res.data, "suggested_score", None)
    if kind == "evidence_analysis" and e.criterion_id and p:
        row = db.scalar(select(AssessorScore).where(AssessorScore.plan_id == p.id, AssessorScore.criterion_id == e.criterion_id))
        if not row:
            crit_task = next(t for t in plan_tasks(db, p) if any(c.id == e.criterion_id for c in t.criteria))
            attempt_id = db.scalar(select(AssessmentAttempt.id).where(
                AssessmentAttempt.plan_id == p.id, AssessmentAttempt.task_id == crit_task.id))
            row = AssessorScore(plan_id=p.id, attempt_id=attempt_id, criterion_id=e.criterion_id, data_origin=p.data_origin)
            db.add(row)
        row.ai_observation_id = obs.id
        if suggested is not None:
            row.ai_suggested_score = suggested
            if row.final_score is not None:
                row.overrode_ai = row.final_score != suggested
        workflow.advance_plan(db, p, "AI_EVIDENCE_REVIEWED", user)
    audit.record(db, "ai.evidence_analysis" if kind == "evidence_analysis" else "ai.document_claims", "evidence", e.id, actor=user,
                 summary=f"AI suggestion generated ({res.provider}{', fallback' if res.fallback_used else ''})"
                         + (f"; suggested score {suggested}" if suggested is not None else "; no score suggested"))
    db.commit()
    return evidence_out(e, user, obs)


class ClaimsConfirmIn(BaseModel):
    claims: list[dict] = Field(max_length=30)


@router.put("/evidence/{evidence_id}/claims")
def confirm_claims(evidence_id: str, body: ClaimsConfirmIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Worker confirms (edits) the claims extracted from a supporting document. No identity verification is performed."""
    e = _load(db, evidence_id, user)
    if e.purpose != "document":
        raise InvalidState("Only supporting documents have claims.")
    e.extracted_claims, e.claims_confirmed = body.claims, True
    audit.record(db, "document.claims_confirmed", "evidence", e.id, actor=user, summary=f"{len(body.claims)} claims confirmed")
    db.commit()
    return evidence_out(e, user, _latest_obs(db, e.id))
