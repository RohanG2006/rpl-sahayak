"""Serialise an assessment plan for the API (tasks, criteria, attempts, scores, evidence links).

Workers never see AI-suggested scores or assessor notes before a decision is recorded; assessors see everything.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AssessmentAttempt, AssessmentPlan, AssessmentTask, AssessorScore, Evidence, Qualification, User, WorkerProfile,
)
from app.services import workflow


def plan_view(db: Session, plan: AssessmentPlan, viewer: User) -> dict:
    q = db.get(Qualification, plan.qualification_id)
    w = db.get(WorkerProfile, plan.worker_id)
    assessor = db.get(User, plan.assessor_id) if plan.assessor_id else None
    attempts = {a.task_id: a for a in db.scalars(select(AssessmentAttempt).where(AssessmentAttempt.plan_id == plan.id))}
    scores = {s.criterion_id: s for s in db.scalars(select(AssessorScore).where(AssessorScore.plan_id == plan.id))}
    evidence = list(db.scalars(select(Evidence).where(Evidence.plan_id == plan.id, Evidence.purpose == "assessment")))
    staff = viewer.role_code in ("assessor", "admin")
    decided = plan.status in ("DECIDED", "REPORT_ISSUED")

    tasks = []
    for t in db.scalars(select(AssessmentTask).where(AssessmentTask.task_code.in_(plan.task_codes),
                                                    AssessmentTask.trade_id == q.trade_id).order_by(AssessmentTask.sort_order)):
        a = attempts.get(t.id)
        crit = []
        for c in t.criteria:
            sc = scores.get(c.id)
            ev = [e.id for e in evidence if e.criterion_id == c.id]
            crit.append({
                "id": c.id, "criterion_code": c.criterion_code, "text": c.text, "weight": c.weight,
                "is_safety_critical": c.is_safety_critical, "qf_dimension": c.qf_dimension,
                "qf_criterion_ref": c.qf_criterion_ref, "anchors": c.anchors, "evidence_hint": c.evidence_hint,
                "evidence_ids": ev,
                "score": None if not sc else {
                    "final_score": sc.final_score if (staff or decided) else None,
                    "confirmed": sc.final_score is not None,
                    "ai_suggested_score": sc.ai_suggested_score if staff else None,
                    "ai_observation_id": sc.ai_observation_id if staff else None,
                    "overrode_ai": sc.overrode_ai if staff else None,
                    "assessor_note": sc.assessor_note if (staff or decided) else None,
                    "confirmed_at": sc.confirmed_at.isoformat() if sc.confirmed_at else None,
                },
            })
        tasks.append({
            "id": t.id, "task_code": t.task_code, "title": t.title, "title_hi": t.title_hi, "description": t.description,
            "description_hi": t.description_hi, "competency_key": t.competency_key, "lo_numbers": t.lo_numbers,
            "weight": t.weight, "steps": t.steps, "evidence_required": t.evidence_required,
            "safety_requirements": t.safety_requirements, "source_ref": t.source_ref, "criteria": crit,
            "attempt": None if not a else {"id": a.id, "status": a.status, "checklist_state": a.checklist_state,
                                           "worker_note": a.worker_note,
                                           "started_at": a.started_at.isoformat() if a.started_at else None,
                                           "completed_at": a.completed_at.isoformat() if a.completed_at else None},
        })

    return {
        "id": plan.id,
        "status": plan.status,
        "ncvet_stage": workflow.NCVET_STAGE.get(plan.status),
        "pathway": plan.pathway,
        "data_origin": plan.data_origin,
        "worker": {"id": w.id, "full_name": w.full_name, "status": w.status, "years_experience": w.years_experience,
                   "occupation": w.occupation, "data_origin": w.data_origin},
        "qualification": {"id": q.id, "title": q.title, "qualification_code": q.qualification_code,
                          "ncvet_code": q.ncvet_code, "nsqf_level": q.nsqf_level, "source_url": q.source.url},
        "assessor": None if not assessor else {"id": assessor.id, "name": assessor.full_name, "code": assessor.assessor_code},
        "match_snapshot": plan.match_snapshot,
        "self_assessment": plan.self_assessment,
        "readiness": plan.readiness_snapshot,
        "tasks": tasks,
        "evidence_count": len(evidence),
        "created_at": plan.created_at.isoformat(),
        "updated_at": plan.updated_at.isoformat(),
    }
