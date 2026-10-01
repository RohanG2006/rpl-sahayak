"""Workflow state machine (docs/project-blueprint.md §3).

Worker-level states run until a qualification is confirmed; from then on the AssessmentPlan carries the
state. States only move forward, except an explicit re-declaration which resets downstream worker states.
"""
from sqlalchemy.orm import Session

from app.core.errors import InvalidState
from app.models import AssessmentPlan, User, WorkerProfile
from app.services import audit

WORKER_STATES = [
    "REGISTERED",
    "PROFILE_COMPLETE",
    "EXPERIENCE_DECLARED",
    "SKILLS_EXTRACTED",
    "SKILLS_CONFIRMED",
    "QUALIFICATION_MATCHED",
    "QUALIFICATION_CONFIRMED",
]

PLAN_STATES = [
    "PLAN_CREATED",
    "SELF_ASSESSED",
    "READINESS_EVALUATED",
    "TASKS_IN_PROGRESS",
    "EVIDENCE_SUBMITTED",
    "AI_EVIDENCE_REVIEWED",
    "ASSESSOR_SCORING",
    "SCORED",
    "RECOMMENDATION_GENERATED",
    "UNDER_ASSESSOR_REVIEW",
    "DECIDED",
    "REPORT_ISSUED",
]

# Human-readable stage mapping to NCVET Annexure-1 Flowchart 3 (NSQF 4, without formal education)
NCVET_STAGE = {
    "REGISTERED": "Enrolment",
    "PROFILE_COMPLETE": "Enrolment",
    "EXPERIENCE_DECLARED": "Enrolment",
    "SKILLS_EXTRACTED": "Enrolment",
    "SKILLS_CONFIRMED": "Enrolment",
    "QUALIFICATION_MATCHED": "Orientation",
    "QUALIFICATION_CONFIRMED": "Orientation",
    "PLAN_CREATED": "Orientation",
    "SELF_ASSESSED": "Orientation",
    "READINESS_EVALUATED": "Assignment of RPL assessor",
    "TASKS_IN_PROGRESS": "Assessment (practical skills)",
    "EVIDENCE_SUBMITTED": "Assessment (practical skills)",
    "AI_EVIDENCE_REVIEWED": "Assessment (practical skills)",
    "ASSESSOR_SCORING": "Assessment (practical skills)",
    "SCORED": "Assessment (practical skills)",
    "RECOMMENDATION_GENERATED": "Assessment (practical skills)",
    "UNDER_ASSESSOR_REVIEW": "Assessment (practical skills)",
    "DECIDED": "Certification & Feedback",
    "REPORT_ISSUED": "Certification & Feedback",
}


def _idx(states: list[str], s: str) -> int:
    if s not in states:
        raise InvalidState(f"Unknown state {s}")
    return states.index(s)


def advance_worker(db: Session, worker: WorkerProfile, to: str, actor: User | None, *, reset: bool = False, via: str = "online") -> None:
    cur, nxt = _idx(WORKER_STATES, worker.status), _idx(WORKER_STATES, to)
    if nxt <= cur and not reset:
        return  # already at or beyond; idempotent
    before = worker.status
    worker.status = to
    audit.record(db, "workflow.worker_state", "worker_profile", worker.id, actor=actor,
                 summary=f"{before} → {to}", before={"status": before}, after={"status": to}, via=via)


def require_worker_at_least(worker: WorkerProfile, state: str, action: str) -> None:
    if _idx(WORKER_STATES, worker.status) < _idx(WORKER_STATES, state):
        raise InvalidState(f"Cannot {action} yet: complete '{state.replace('_', ' ').lower()}' first.",
                           details={"current": worker.status, "required": state})


def advance_plan(db: Session, plan: AssessmentPlan, to: str, actor: User | None, *, via: str = "online", allow_back: bool = False) -> None:
    cur, nxt = _idx(PLAN_STATES, plan.status), _idx(PLAN_STATES, to)
    if nxt <= cur and not allow_back:
        return
    before = plan.status
    plan.status = to
    audit.record(db, "workflow.plan_state", "assessment_plan", plan.id, actor=actor,
                 summary=f"{before} → {to}", before={"status": before}, after={"status": to}, via=via)


def require_plan_at_least(plan: AssessmentPlan, state: str, action: str) -> None:
    if _idx(PLAN_STATES, plan.status) < _idx(PLAN_STATES, state):
        raise InvalidState(f"Cannot {action} yet: assessment must reach '{state.replace('_', ' ').lower()}'.",
                           details={"current": plan.status, "required": state})


def require_plan_before(plan: AssessmentPlan, state: str, action: str) -> None:
    if _idx(PLAN_STATES, plan.status) >= _idx(PLAN_STATES, state):
        raise InvalidState(f"Cannot {action}: assessment is already at '{plan.status.replace('_', ' ').lower()}'.",
                           details={"current": plan.status})
