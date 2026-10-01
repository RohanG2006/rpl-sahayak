from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ensure_worker_access, get_current_user, require_roles
from app.core.errors import Conflict, Forbidden, InvalidState, NotFound
from app.db.base import utcnow
from app.db.session import get_db
from app.models import AssessmentAttempt, AssessmentPlan, AssessmentTask, AssessorScore, Evidence, User, WorkerProfile
from app.repositories import qualifications as qrepo
from app.services import audit, readiness, workflow
from app.services.assignment import pick_assessor
from app.services.results import plan_results, plan_tasks
from app.services.plan_view import plan_view

router = APIRouter(prefix="/assessments", tags=["assessments"])


def load_plan(db: Session, plan_id: str, user: User) -> AssessmentPlan:
    p = db.get(AssessmentPlan, plan_id)
    if not p:
        raise NotFound("Assessment not found.")
    if user.role_code == "worker":
        ensure_worker_access(user, db.get(WorkerProfile, p.worker_id))
    elif user.role_code == "assessor" and p.assessor_id not in (None, user.id):
        raise Forbidden("This candidate is assigned to another assessor.")
    return p


class PlanCreate(BaseModel):
    worker_id: str
    qualification_id: str


@router.post("", status_code=201)
def create_assessment(body: PlanCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Worker confirms a matched qualification → an assessment plan is created and an assessor allocated."""
    w = db.get(WorkerProfile, body.worker_id)
    if not w:
        raise NotFound("Worker not found.")
    ensure_worker_access(user, w)
    workflow.require_worker_at_least(w, "QUALIFICATION_MATCHED", "choose a qualification")
    q = qrepo.get_qualification(db, body.qualification_id)
    if not q.trade.is_assessable:
        raise Conflict(f"{q.title} ({q.qualification_code}) is available for matching only; the prototype task bank covers Electrician.",
                       code="qualification_not_assessable")
    existing = db.scalar(select(AssessmentPlan).where(
        AssessmentPlan.worker_id == w.id, AssessmentPlan.qualification_id == q.id,
        AssessmentPlan.status.not_in(("DECIDED", "REPORT_ISSUED"))))
    if existing:
        return plan_view(db, existing, user)
    snap = next((r for r in (w.last_match or {}).get("results", []) if r["qualification_id"] == q.id), None)
    if snap is None:
        raise InvalidState("Run qualification matching first.")
    tasks = qrepo.tasks_for_trade(db, q.trade_id)
    assessor = pick_assessor(db)
    plan = AssessmentPlan(worker_id=w.id, qualification_id=q.id, assessor_id=assessor.id if assessor else None,
                          status="PLAN_CREATED", match_snapshot=snap, task_codes=[t.task_code for t in tasks],
                          data_origin=w.data_origin)
    db.add(plan)
    db.flush()
    for t in tasks:
        db.add(AssessmentAttempt(plan_id=plan.id, task_id=t.id, data_origin=w.data_origin))
    workflow.advance_worker(db, w, "QUALIFICATION_CONFIRMED", user)
    audit.record(db, "assessment.created", "assessment_plan", plan.id, actor=user,
                 summary=f"Plan for {q.title} ({q.qualification_code}); {len(tasks)} tasks; assessor {assessor.assessor_code if assessor else 'unassigned'}")
    db.commit()
    db.refresh(plan)
    return plan_view(db, plan, user)


@router.get("/{plan_id}")
def get_assessment(plan_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return plan_view(db, load_plan(db, plan_id, user), user)


@router.get("")
def my_assessments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Worker: own plans. Assessor: assigned plans. Admin: all (summary only)."""
    stmt = select(AssessmentPlan).order_by(AssessmentPlan.created_at.desc())
    if user.role_code == "worker":
        wid = db.scalar(select(WorkerProfile.id).where(WorkerProfile.user_id == user.id))
        stmt = stmt.where(AssessmentPlan.worker_id == wid)
    elif user.role_code == "assessor":
        stmt = stmt.where(AssessmentPlan.assessor_id == user.id)
    return [{"id": p.id, "status": p.status, "qualification_id": p.qualification_id, "worker_id": p.worker_id,
             "ncvet_stage": workflow.NCVET_STAGE.get(p.status), "updated_at": p.updated_at.isoformat()} for p in db.scalars(stmt.limit(100))]


# ---- Phase 5: self-assessment, readiness, guided tasks, standardised scoring ------------------------
class SelfAssessmentIn(BaseModel):
    responses: dict[int, Literal["regularly", "sometimes", "never"]]


@router.post("/{plan_id}/self-assessment")
def self_assessment(plan_id: str, body: SelfAssessmentIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Worker's self-assessment of in-scope learning outcomes → readiness pathway (pre-screening)."""
    p = load_plan(db, plan_id, user)
    workflow.require_plan_before(p, "TASKS_IN_PROGRESS", "change the self-assessment")
    scope = sorted({lo for t in plan_tasks(db, p) for lo in t.lo_numbers})
    unknown = set(body.responses) - set(scope)
    if unknown:
        raise InvalidState(f"Learning outcomes {sorted(unknown)} are outside this assessment's scope.", code="validation_error")
    snap = p.match_snapshot or {}
    p.self_assessment = {str(k): v for k, v in body.responses.items()}
    p.readiness_snapshot = readiness.evaluate(scope, body.responses, snap, snap.get("eligibility", []))
    p.pathway = p.readiness_snapshot["pathway"]
    workflow.advance_plan(db, p, "SELF_ASSESSED", user)
    workflow.advance_plan(db, p, "READINESS_EVALUATED", user)
    audit.record(db, "assessment.self_assessed", "assessment_plan", p.id, actor=user,
                 summary=f"Readiness: {p.pathway} ({p.readiness_snapshot['weighted_coverage']:.0%} self-assessed coverage)")
    db.commit()
    return {"readiness": p.readiness_snapshot, "status": p.status}


@router.post("/{plan_id}/start")
def start_assessment(plan_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = load_plan(db, plan_id, user)
    workflow.require_plan_at_least(p, "READINESS_EVALUATED", "start the practical assessment")
    if p.status == "READINESS_EVALUATED":
        p.started_at = utcnow()
        workflow.advance_plan(db, p, "TASKS_IN_PROGRESS", user)
        audit.record(db, "assessment.started", "assessment_plan", p.id, actor=user,
                     summary=f"Practical assessment started (pathway {p.pathway})")
        db.commit()
    return plan_view(db, p, user)


class TaskProgressIn(BaseModel):
    checklist_state: dict[str, bool] = Field(default_factory=dict)
    worker_note: str | None = Field(default=None, max_length=1000)
    status: Literal["IN_PROGRESS", "SUBMITTED"] = "IN_PROGRESS"


def _attempt(db: Session, p: AssessmentPlan, task_ref: str) -> tuple[AssessmentTask, AssessmentAttempt]:
    t = next((t for t in plan_tasks(db, p) if task_ref in (t.id, t.task_code)), None)
    if not t:
        raise NotFound("Task not in this assessment.")
    a = db.scalar(select(AssessmentAttempt).where(AssessmentAttempt.plan_id == p.id, AssessmentAttempt.task_id == t.id))
    return t, a


@router.put("/{plan_id}/tasks/{task_id}/progress")
def task_progress(plan_id: str, task_id: str, body: TaskProgressIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Worker's guided checklist for a practical task (step ticks, note, submit)."""
    p = load_plan(db, plan_id, user)
    workflow.require_plan_at_least(p, "TASKS_IN_PROGRESS", "work on tasks")
    t, a = _attempt(db, p, task_id)
    if a.status == "SCORED":
        raise InvalidState("This task has already been scored by the assessor.")
    a.checklist_state, a.worker_note = body.checklist_state, body.worker_note
    a.started_at = a.started_at or utcnow()
    a.status = body.status
    if body.status == "SUBMITTED":
        a.completed_at = utcnow()
        audit.record(db, "task.submitted", "assessment_attempt", a.id, actor=user, summary=f"{t.task_code} submitted by candidate")
    db.commit()
    return plan_view(db, p, user)


class CriterionScoreIn(BaseModel):
    criterion_code: str
    final_score: int = Field(ge=0, le=4)
    assessor_note: str | None = Field(default=None, max_length=2000)


class TaskScoreIn(BaseModel):
    scores: list[CriterionScoreIn] = Field(min_length=1)


@router.post("/{plan_id}/tasks/{task_id}/score")
def score_task(plan_id: str, task_id: str, body: TaskScoreIn, db: Session = Depends(get_db),
               user: User = Depends(require_roles("assessor"))):
    """Assessor records final rubric scores (0–4). Only these scores enter calculations.
    A score for a criterion with no linked evidence requires an observation note (rubric rule)."""
    p = load_plan(db, plan_id, user)
    workflow.require_plan_at_least(p, "TASKS_IN_PROGRESS", "score tasks")
    workflow.require_plan_before(p, "DECIDED", "change scores")
    t, a = _attempt(db, p, task_id)
    crit = {c.criterion_code: c for c in t.criteria}
    ev_by_crit: dict[str, list[str]] = {}
    for e in db.scalars(select(Evidence).where(Evidence.plan_id == p.id, Evidence.purpose == "assessment")):
        if e.criterion_id:
            ev_by_crit.setdefault(e.criterion_id, []).append(e.id)
    changes = []
    for s in body.scores:
        c = crit.get(s.criterion_code)
        if not c:
            raise NotFound(f"Criterion {s.criterion_code} is not part of {t.task_code}.")
        ev_ids = ev_by_crit.get(c.id, [])
        if not ev_ids and not (s.assessor_note and s.assessor_note.strip()):
            raise InvalidState(f"{s.criterion_code}: add an observation note when no evidence is linked.", code="note_required")
        row = db.scalar(select(AssessorScore).where(AssessorScore.plan_id == p.id, AssessorScore.criterion_id == c.id))
        if not row:
            row = AssessorScore(plan_id=p.id, attempt_id=a.id, criterion_id=c.id, weight=c.weight, data_origin=p.data_origin)
            db.add(row)
        before = row.final_score
        row.final_score, row.assessor_note, row.evidence_ids = s.final_score, s.assessor_note, ev_ids
        row.confirmed_by, row.confirmed_at = user.id, utcnow()
        row.overrode_ai = row.ai_suggested_score is not None and row.ai_suggested_score != s.final_score
        changes.append({"criterion": s.criterion_code, "before": before, "after": s.final_score,
                        "ai_suggested": row.ai_suggested_score, "overrode_ai": row.overrode_ai})
    db.flush()
    scored = set(db.scalars(select(AssessorScore.criterion_id).where(
        AssessorScore.plan_id == p.id, AssessorScore.final_score.is_not(None))))
    if all(c.id in scored for c in t.criteria):
        a.status = "SCORED"
    workflow.advance_plan(db, p, "ASSESSOR_SCORING", user)
    if all(c.id in scored for task in plan_tasks(db, p) for c in task.criteria):
        workflow.advance_plan(db, p, "SCORED", user)
    for ch in changes:
        action = "score.overridden_ai" if ch["overrode_ai"] else ("score.changed" if ch["before"] is not None else "score.recorded")
        audit.record(db, action, "assessment_plan", p.id, actor=user,
                     summary=f"{t.task_code}/{ch['criterion']}: {ch['before']} → {ch['after']}"
                             + (f" (AI suggested {ch['ai_suggested']})" if ch["ai_suggested"] is not None else ""),
                     before={"score": ch["before"]}, after={"score": ch["after"], "ai_suggested": ch["ai_suggested"]})
    db.commit()
    return plan_view(db, p, user)


@router.get("/{plan_id}/results")
def results(plan_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Computed task / LO / competency / dimension / overall percentages from assessor-confirmed scores only.
    Workers see results only after the assessor's decision."""
    p = load_plan(db, plan_id, user)
    if user.role_code == "worker" and p.status not in ("DECIDED", "REPORT_ISSUED"):
        raise Forbidden("Results are shared after the assessor's decision.", code="results_not_released")
    return plan_results(db, p)
