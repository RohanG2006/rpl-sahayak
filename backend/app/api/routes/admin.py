"""Administration: users, task bank / rubric governance, audit log, system overview. Admin role only.

Official qualification data is read-only here (it is re-ingested from source PDFs, never hand-edited).
"""
import secrets
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.errors import Conflict, InvalidState, NotFound
from app.core.security import hash_password
from app.db.base import utcnow
from app.db.session import get_db
from app.models import (
    AIObservation, AssessmentCriterion, AssessmentPlan, AssessmentTask, AssessorDecision, AssessorScore, AuditLog,
    Evidence, Qualification, SyncQueue, User, WorkerProfile,
)
from app.services import audit

router = APIRouter(prefix="/admin", tags=["admin"])
Admin = Depends(require_roles("admin"))


# ---- Overview -------------------------------------------------------------------------------------
@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Admin):
    def grouped(col, model, *where):
        stmt = select(col, func.count()).select_from(model)
        for w in where:
            stmt = stmt.where(w)
        return dict(db.execute(stmt.group_by(col)).all())

    ai_total = db.scalar(select(func.count()).select_from(AIObservation)) or 0
    ai_fallback = db.scalar(select(func.count()).select_from(AIObservation).where(AIObservation.fallback_used.is_(True))) or 0
    with_ai = db.scalar(select(func.count()).select_from(AssessorScore).where(AssessorScore.ai_suggested_score.is_not(None), AssessorScore.final_score.is_not(None))) or 0
    overrides = db.scalar(select(func.count()).select_from(AssessorScore).where(AssessorScore.overrode_ai.is_(True))) or 0
    since = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "users_by_role": grouped(User.role_code, User),
        "workers_by_origin": grouped(WorkerProfile.data_origin, WorkerProfile),
        "plans_by_status": grouped(AssessmentPlan.status, AssessmentPlan),
        "decisions": grouped(AssessorDecision.decision, AssessorDecision),
        "evidence": {"total": db.scalar(select(func.count()).select_from(Evidence)) or 0,
                     "captured_offline": db.scalar(select(func.count()).select_from(Evidence).where(Evidence.captured_offline.is_(True))) or 0,
                     "by_kind": grouped(Evidence.kind, Evidence)},
        "ai": {"observations": ai_total, "by_provider": grouped(AIObservation.provider, AIObservation),
               "by_kind": grouped(AIObservation.kind, AIObservation),
               "fallback_rate": round(ai_fallback / ai_total, 4) if ai_total else None,
               "scores_with_ai_suggestion": with_ai, "assessor_overrides": overrides,
               "override_rate": round(overrides / with_ai, 4) if with_ai else None},
        "sync": {"by_status": grouped(SyncQueue.status, SyncQueue),
                 "last_received": (lambda t: t.isoformat() if t else None)(db.scalar(select(func.max(SyncQueue.received_at))))},
        "audit_events_today": db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.at >= since)) or 0,
        "qualifications": [{"code": q.qualification_code, "title": q.title, "assessable": q.trade.is_assessable,
                            "los": sum(c.category == "trade" for c in q.competencies), "source_url": q.source.url,
                            "sha256": q.source.sha256, "retrieved_at": q.source.retrieved_at.isoformat()}
                           for q in db.scalars(select(Qualification))],
    }


# ---- Users ----------------------------------------------------------------------------------------
class UserCreate(BaseModel):
    login: str = Field(min_length=3, max_length=120)
    full_name: str = Field(min_length=2, max_length=120)
    role: Literal["assessor", "admin"]
    assessor_code: str | None = Field(default=None, pattern=r"^A\d{2,3}$")
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserPatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None


def user_row(db: Session, u: User) -> dict:
    open_plans = db.scalar(select(func.count()).select_from(AssessmentPlan).where(
        AssessmentPlan.assessor_id == u.id, AssessmentPlan.status.not_in(("DECIDED", "REPORT_ISSUED")))) if u.role_code == "assessor" else None
    decided = db.scalar(select(func.count()).select_from(AssessorDecision).where(AssessorDecision.assessor_id == u.id)) if u.role_code == "assessor" else None
    return {"id": u.id, "login": u.login, "full_name": u.full_name, "role": u.role_code, "assessor_code": u.assessor_code,
            "is_active": u.is_active, "data_origin": u.data_origin, "created_at": u.created_at.isoformat(),
            "open_plans": open_plans, "decisions": decided}


@router.get("/users")
def list_users(role: str | None = None, db: Session = Depends(get_db), user: User = Admin):
    stmt = select(User).order_by(User.role_code, User.assessor_code, User.login)
    if role:
        stmt = stmt.where(User.role_code == role)
    rows = list(db.scalars(stmt.limit(500)))
    return [user_row(db, u) for u in rows]


@router.post("/users", status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db), user: User = Admin):
    login = body.login.strip().lower()
    if db.scalar(select(User).where(User.login == login)):
        raise Conflict("That login already exists.")
    if body.role == "assessor":
        if not body.assessor_code:
            raise InvalidState("Assessor code (e.g. A06) is required for assessors.", code="validation_error")
        if db.scalar(select(User).where(User.assessor_code == body.assessor_code)):
            raise Conflict("That assessor code is already used.")
    temp = body.password or secrets.token_urlsafe(9)
    u = User(login=login, full_name=body.full_name, role_code=body.role, assessor_code=body.assessor_code if body.role == "assessor" else None,
             password_hash=hash_password(temp))
    db.add(u)
    db.flush()
    audit.record(db, "admin.user_created", "user", u.id, actor=user, summary=f"{body.role} account created ({u.assessor_code or login})")
    db.commit()
    out = user_row(db, u)
    if not body.password:
        out["temporary_password"] = temp  # shown once to the admin; never stored in plain text or logged
    return out


@router.put("/users/{user_id}")
def update_user(user_id: str, body: UserPatch, db: Session = Depends(get_db), user: User = Admin):
    u = db.get(User, user_id)
    if not u:
        raise NotFound("User not found.")
    if body.is_active is False and u.id == user.id:
        raise Conflict("You cannot deactivate your own account.")
    before = {"is_active": u.is_active}
    if body.full_name is not None:
        u.full_name = body.full_name
    if body.is_active is not None:
        u.is_active = body.is_active
    audit.record(db, "admin.user_updated", "user", u.id, actor=user, before=before,
                 after={"is_active": u.is_active}, summary=f"{u.assessor_code or u.role_code} {'activated' if u.is_active else 'deactivated'}")
    db.commit()
    return user_row(db, u)


# ---- Task bank / rubric governance -----------------------------------------------------------------
class TaskPatch(BaseModel):
    weight: float | None = Field(default=None, gt=0, le=5)
    is_active: bool | None = None
    title: str | None = Field(default=None, min_length=3, max_length=200)
    title_hi: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=2000)


class CriterionPatch(BaseModel):
    weight: float | None = Field(default=None, gt=0, le=5)
    is_safety_critical: bool | None = None
    text: str | None = Field(default=None, min_length=5, max_length=500)
    anchors: dict[Literal["0", "1", "2", "3", "4"], str] | None = None


def _scores_exist(db: Session, criterion_ids: list[str]) -> int:
    return db.scalar(select(func.count()).select_from(AssessorScore).where(
        AssessorScore.criterion_id.in_(criterion_ids), AssessorScore.final_score.is_not(None))) or 0


SCORING_FIELDS = {"weight", "is_safety_critical", "is_active"}


@router.put("/tasks/{task_code}")
def update_task(task_code: str, body: TaskPatch, db: Session = Depends(get_db), user: User = Admin):
    t = db.scalar(select(AssessmentTask).where(AssessmentTask.task_code == task_code))
    if not t:
        raise NotFound("Task not found.")
    changes = body.model_dump(exclude_unset=True)
    n = _scores_exist(db, [c.id for c in t.criteria])
    if n and SCORING_FIELDS & changes.keys():
        raise Conflict(f"{n} recorded scores use {task_code}; changing weight or activation would silently change past results. "
                       "Edit wording only, or create a new rubric version.", code="rubric_locked")
    before = {k: getattr(t, k) for k in changes}
    for k, v in changes.items():
        setattr(t, k, v)
    audit.record(db, "admin.task_updated", "assessment_task", t.id, actor=user, before=before, after=changes, summary=f"{task_code} edited")
    db.commit()
    return {"task_code": t.task_code, **{k: getattr(t, k) for k in ("title", "title_hi", "description", "weight", "is_active")}}


@router.put("/criteria/{criterion_code}")
def update_criterion(criterion_code: str, body: CriterionPatch, db: Session = Depends(get_db), user: User = Admin):
    c = db.scalar(select(AssessmentCriterion).where(AssessmentCriterion.criterion_code == criterion_code))
    if not c:
        raise NotFound("Criterion not found.")
    changes = body.model_dump(exclude_unset=True)
    n = _scores_exist(db, [c.id])
    if n and SCORING_FIELDS & changes.keys():
        raise Conflict(f"{n} recorded scores use {criterion_code}; its weight and safety flag are locked.", code="rubric_locked")
    if "anchors" in changes and set(changes["anchors"]) != {"0", "1", "2", "3", "4"}:
        raise InvalidState("Provide all five anchors (0–4).", code="validation_error", status=422)
    before = {k: getattr(c, k) for k in changes}
    for k, v in changes.items():
        setattr(c, k, v)
    audit.record(db, "admin.criterion_updated", "assessment_criterion", c.id, actor=user, before=before, after=changes,
                 summary=f"{criterion_code} edited ({', '.join(changes)})")
    db.commit()
    return {"criterion_code": c.criterion_code, "weight": c.weight, "is_safety_critical": c.is_safety_critical, "text": c.text,
            "anchors": c.anchors, "scores_recorded": n}


@router.get("/tasks")
def tasks_with_usage(db: Session = Depends(get_db), user: User = Admin):
    out = []
    for t in db.scalars(select(AssessmentTask).order_by(AssessmentTask.sort_order)):
        out.append({"task_code": t.task_code, "title": t.title, "title_hi": t.title_hi, "description": t.description, "weight": t.weight,
                    "is_active": t.is_active, "competency_key": t.competency_key, "lo_numbers": t.lo_numbers,
                    "scores_recorded": _scores_exist(db, [c.id for c in t.criteria]),
                    "criteria": [{"criterion_code": c.criterion_code, "text": c.text, "weight": c.weight, "is_safety_critical": c.is_safety_critical,
                                  "qf_dimension": c.qf_dimension, "qf_criterion_ref": c.qf_criterion_ref, "anchors": c.anchors,
                                  "scores_recorded": _scores_exist(db, [c.id])} for c in t.criteria]})
    return out


# ---- Audit log & sync ------------------------------------------------------------------------------
@router.get("/audit")
def audit_log(action: str | None = None, entity: str | None = None, actor_role: str | None = None, via: str | None = None,
              q: str | None = None, page: int = 1, page_size: int = 50, db: Session = Depends(get_db), user: User = Admin):
    page_size = max(1, min(page_size, 200))
    stmt = select(AuditLog, User).outerjoin(User, User.id == AuditLog.actor_id)
    if action:
        stmt = stmt.where(AuditLog.action.like(f"{action}%"))
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    if actor_role:
        stmt = stmt.where(AuditLog.actor_role == actor_role)
    if via:
        stmt = stmt.where(AuditLog.via == via)
    if q:
        stmt = stmt.where(AuditLog.summary.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(stmt.order_by(AuditLog.at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    actions = [a for (a,) in db.execute(select(AuditLog.action).distinct().order_by(AuditLog.action))]
    return {"total": total, "page": page, "page_size": page_size, "actions": actions,
            "rows": [{"id": a.id, "at": a.at.isoformat(), "action": a.action, "entity": a.entity, "entity_id": a.entity_id,
                      "actor": (u.assessor_code or u.full_name) if u else "system", "actor_role": a.actor_role, "via": a.via,
                      "summary": a.summary, "before": a.before, "after": a.after} for a, u in rows]}


@router.get("/sync")
def sync_log(db: Session = Depends(get_db), user: User = Admin):
    rows = list(db.scalars(select(SyncQueue).order_by(SyncQueue.received_at.desc()).limit(100)))
    return [{"client_op_id": r.client_op_id, "client_id": r.client_id, "entity": r.entity, "op": r.op, "status": r.status,
             "detail": (r.result or {}).get("detail"), "client_ts": r.client_ts.isoformat() if r.client_ts else None,
             "received_at": r.received_at.isoformat()} for r in rows]
