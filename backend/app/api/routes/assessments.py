from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ensure_worker_access, get_current_user
from app.core.errors import Conflict, Forbidden, InvalidState, NotFound
from app.db.session import get_db
from app.models import AssessmentAttempt, AssessmentPlan, User, WorkerProfile
from app.repositories import qualifications as qrepo
from app.services import audit, workflow
from app.services.assignment import pick_assessor
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
