"""Offline sync: the client replays queued operations in order; the server applies each once.

Rules (docs/offline-sync.md):
- Idempotent on client_op_id: a replayed op returns its original result with status 'duplicate'.
- Worker-owned data (profile, declarations, task checklist) → applied; last-writer-wins by client timestamp,
  with the overwritten server copy kept in sync_queue.result.conflict.
- Assessor-owned data (scores, decisions) is server-authoritative: such ops are 'rejected', never applied.
- One op failing does not stop the batch; each op reports its own status.
Evidence files sync through POST /evidence with the same client_op_id (multipart), not through this endpoint.
"""
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.base import utcnow
from app.db.session import get_db
from app.models import AssessmentAttempt, AssessmentPlan, SyncQueue, User, WorkerExperience, WorkerProfile
from app.schemas.workers import ExperienceIn, WorkerUpdate
from app.services import audit, workflow
from app.services.results import plan_tasks

router = APIRouter(prefix="/sync", tags=["sync"])
SERVER_OWNED = {"assessor_score", "assessor_decision", "recommendation"}


class Op(BaseModel):
    op_id: str = Field(min_length=8, max_length=36)
    entity: str = Field(max_length=40)
    op: str = Field(max_length=20)
    payload: dict[str, Any] = Field(default_factory=dict)
    client_ts: datetime | None = None


class SyncIn(BaseModel):
    client_id: str = Field(min_length=4, max_length=64)
    ops: list[Op] = Field(max_length=200)


class OpResult(BaseModel):
    op_id: str
    status: Literal["applied", "duplicate", "conflict", "rejected", "failed"]
    detail: str | None = None


def _worker(db: Session, user: User) -> WorkerProfile:
    w = db.scalar(select(WorkerProfile).where(WorkerProfile.user_id == user.id))
    if not w:
        raise AppError("Only workers sync offline data in this prototype.", code="forbidden", status=403)
    return w


def _apply(db: Session, user: User, w: WorkerProfile, op: Op) -> tuple[str, str | None, dict]:
    if op.entity in SERVER_OWNED:
        return "rejected", f"{op.entity} is assessor-owned and cannot be changed from a device", {}
    if op.entity == "worker_profile" and op.op == "update":
        body = WorkerUpdate.model_validate(op.payload).model_dump(exclude_unset=True)
        conflict = {}
        if op.client_ts and w.updated_at and w.updated_at > op.client_ts:
            # server copy is newer: last-writer-wins by client timestamp means the server value stays
            conflict = {"server_newer": True, "server_values": {k: getattr(w, k) for k in body}}
            return "conflict", "Server copy is newer; device change kept for review", {"conflict": conflict}
        for k, v in body.items():
            setattr(w, k, v)
        audit.record(db, "worker.updated", "worker_profile", w.id, actor=user, via="sync", after=body, summary="Profile updated (offline sync)")
        return "applied", None, {}
    if op.entity == "worker_experience" and op.op == "create":
        body = ExperienceIn.model_validate(op.payload)
        version = (db.scalar(select(func.max(WorkerExperience.version)).where(WorkerExperience.worker_id == w.id)) or 0) + 1
        db.add(WorkerExperience(worker_id=w.id, version=version, raw_text=body.raw_text.strip(), input_mode=body.input_mode,
                                language=body.language, data_origin=w.data_origin))
        beyond = workflow.WORKER_STATES.index(w.status) > workflow.WORKER_STATES.index("EXPERIENCE_DECLARED")
        workflow.advance_worker(db, w, "EXPERIENCE_DECLARED", user, reset=beyond, via="sync")
        return "applied", f"declaration v{version}", {"version": version}
    if op.entity == "task_progress" and op.op == "update":
        plan = db.get(AssessmentPlan, op.payload.get("plan_id"))
        if not plan or plan.worker_id != w.id:
            return "rejected", "assessment not found for this worker", {}
        task = next((t for t in plan_tasks(db, plan) if t.task_code == op.payload.get("task_code")), None)
        if not task:
            return "rejected", "task not in this assessment", {}
        a = db.scalar(select(AssessmentAttempt).where(AssessmentAttempt.plan_id == plan.id, AssessmentAttempt.task_id == task.id))
        if a.status == "SCORED":
            return "rejected", "task already scored by the assessor", {}
        a.checklist_state = op.payload.get("checklist_state", {})
        a.worker_note = op.payload.get("worker_note")
        a.status = "SUBMITTED" if op.payload.get("status") == "SUBMITTED" else "IN_PROGRESS"
        a.started_at = a.started_at or utcnow()
        if a.status == "SUBMITTED":
            a.completed_at = utcnow()
        return "applied", None, {}
    return "rejected", f"unsupported operation {op.entity}.{op.op}", {}


@router.post("", response_model=dict)
def sync(body: SyncIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    w = _worker(db, user)
    results: list[OpResult] = []
    counts = {"applied": 0, "duplicate": 0, "conflict": 0, "rejected": 0, "failed": 0}
    for op in body.ops:
        prior = db.scalar(select(SyncQueue).where(SyncQueue.client_op_id == op.op_id))
        if prior:
            status, detail = "duplicate", f"already {prior.status}"
        else:
            row = SyncQueue(client_id=body.client_id, client_op_id=op.op_id, user_id=user.id, entity=op.entity, op=op.op,
                            payload=op.payload, client_ts=op.client_ts)
            try:
                with db.begin_nested():
                    status, detail, extra = _apply(db, user, w, op)
            except (ValidationError, AppError) as e:
                status, detail, extra = "failed", (e.errors()[0]["msg"] if isinstance(e, ValidationError) else e.message), {}
            row.status, row.result = status, {"detail": detail, **extra}
            row.applied_at = utcnow() if status == "applied" else None
            db.add(row)
        counts[status] += 1
        results.append(OpResult(op_id=op.op_id, status=status, detail=detail))
    audit.record(db, "sync.completed", "worker_profile", w.id, actor=user, via="sync",
                 summary=", ".join(f"{v} {k}" for k, v in counts.items() if v) or "empty batch")
    db.commit()
    return {"counts": counts, "results": [r.model_dump() for r in results], "server_time": utcnow().isoformat()}


@router.get("/status")
def status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(SyncQueue.status, func.count()).group_by(SyncQueue.status)
    if user.role_code == "worker":
        stmt = stmt.where(SyncQueue.user_id == user.id)
    last = db.scalar(select(func.max(SyncQueue.received_at)).where(SyncQueue.user_id == user.id) if user.role_code == "worker"
                     else select(func.max(SyncQueue.received_at)))
    return {"by_status": dict(db.execute(stmt).all()), "last_sync_at": last.isoformat() if last else None,
            "server_time": utcnow().isoformat()}
