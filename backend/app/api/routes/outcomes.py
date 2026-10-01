"""Competency profile, skill gaps, recommendation, and the assessor's final decision."""
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.ai.service import AIService, get_ai_service
from app.api.deps import get_current_user, require_roles
from app.api.routes.assessments import load_plan
from app.core.config import get_settings
from app.core.errors import Forbidden, InvalidState
from app.db.session import get_db
from app.models import (
    AIObservation, AssessmentAttempt, AssessmentPlan, AssessorDecision, CompetencyResult, Evidence, Qualification,
    Recommendation, SkillGap, User, WorkerProfile,
)
from app.services import audit, workflow
from app.services.gaps import compute_gaps
from app.services.plan_view import plan_view
from app.services.recommendation import DISCLAIMER, recommend
from app.services.results import plan_results

router = APIRouter(tags=["outcomes"])
RELEASED = ("DECIDED", "REPORT_ISSUED")


def _worker_gate(p: AssessmentPlan, user: User) -> None:
    if user.role_code == "worker" and p.status not in RELEASED:
        raise Forbidden("Results are shared after the assessor's decision.", code="results_not_released")


def _hash(res: dict) -> str:
    import hashlib
    import json
    return hashlib.sha256(json.dumps({k: res[k] for k in ("tasks", "dimensions")}, sort_keys=True, default=str).encode()).hexdigest()


@router.get("/competencies/{assessment_id}")
def competencies(assessment_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user),
                 ai: AIService = Depends(get_ai_service)):
    """Competency profile from assessor-confirmed scores: task, LO, competency-area and official formative-dimension %."""
    p = load_plan(db, assessment_id, user)
    _worker_gate(p, user)
    res = plan_results(db, p)
    h = _hash(res)
    if not db.scalar(select(func.count()).select_from(CompetencyResult).where(CompetencyResult.plan_id == p.id, CompetencyResult.inputs_hash == h)):
        db.execute(delete(CompetencyResult).where(CompetencyResult.plan_id == p.id))
        req = get_settings().competency_required_pct
        rows = [("overall", "overall", "Overall practical score", res["overall_pct"])]
        rows += [("competency", k, res["competency_labels"].get(k, k), v) for k, v in res["competencies"].items()]
        rows += [("lo", f"LO{k}", f"Learning outcome {k}", v) for k, v in res["learning_outcomes"].items()]
        rows += [("dimension", k, k, v) for k, v in res["dimensions"].items()]
        rows += [("task", k, res["task_titles"][k], v["task_pct"]) for k, v in res["tasks"].items()]
        for g, k, label, v in rows:
            db.add(CompetencyResult(plan_id=p.id, group=g, competency_key=k, label=label, score_pct=v, required_pct=req, inputs_hash=h))
        db.commit()
    summary = ai.summarize_competencies(res) if res["overall_pct"] is not None else None
    return {**res, "summary": None if not summary else {"text": summary.data.summary, "provider": summary.provider,
                                                         "fallback_used": summary.fallback_used}}


@router.get("/skill-gaps/{assessment_id}")
def skill_gaps(assessment_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user),
               ai: AIService = Depends(get_ai_service)):
    p = load_plan(db, assessment_id, user)
    _worker_gate(p, user)
    g = compute_gaps(db, p)
    db.execute(delete(SkillGap).where(SkillGap.plan_id == p.id))
    for a in g["areas"]:
        if a["gap"] is not None:
            db.add(SkillGap(plan_id=p.id, competency_key=a["competency_key"], label=a["label"], required=a["required"],
                            demonstrated=a["demonstrated"], gap=a["gap"], learning_topics=a["learning_topics"]))
    db.commit()
    s = ai.generate_skill_gaps(g)
    return {**g, "summary": {"text": s.data.summary, "provider": s.provider, "fallback_used": s.fallback_used}}


@router.post("/assessments/{assessment_id}/recommendation")
def make_recommendation(assessment_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles("assessor")),
                        ai: AIService = Depends(get_ai_service)):
    """Generate the explainable recommendation. Requires all criteria scored (state SCORED)."""
    p = load_plan(db, assessment_id, user)
    workflow.require_plan_at_least(p, "SCORED", "generate a recommendation")
    workflow.require_plan_before(p, "DECIDED", "regenerate the recommendation")
    rec = recommend(db, p)
    nar = ai.generate_recommendation(rec)
    obs = AIObservation(plan_id=p.id, worker_id=p.worker_id, kind="recommendation_narrative", provider=nar.provider, model=nar.model,
                        prompt_file=nar.prompt_file, prompt_version=nar.prompt_version, output=nar.data.model_dump(),
                        confidence=nar.confidence, fallback_used=nar.fallback_used, attempts=nar.attempts, data_origin=p.data_origin)
    db.add(obs)
    db.flush()
    row = Recommendation(plan_id=p.id, outcome=rec["outcome"], competency_coverage=rec["competency_coverage"],
                         evidence_coverage=rec["evidence_coverage"], overall_pct=rec["overall_pct"], rule_trace=rec["rule_trace"],
                         flags=rec["flags"], narrative=nar.data.summary, narrative_ai_observation_id=obs.id)
    db.add(row)
    workflow.advance_plan(db, p, "RECOMMENDATION_GENERATED", user)
    workflow.advance_plan(db, p, "UNDER_ASSESSOR_REVIEW", user)
    audit.record(db, "recommendation.generated", "assessment_plan", p.id, actor=user,
                 summary=f"AI-assisted recommendation: {rec['outcome']} (coverage {rec['competency_coverage']:.0%}, evidence {rec['evidence_coverage']:.0%})")
    db.commit()
    return recommendation_out(row, nar.provider)


def recommendation_out(r: Recommendation, provider: str | None = None) -> dict:
    return {"id": r.id, "outcome": r.outcome, "competency_coverage": r.competency_coverage, "evidence_coverage": r.evidence_coverage,
            "overall_pct": r.overall_pct, "rule_trace": r.rule_trace, "flags": r.flags, "narrative": r.narrative,
            "narrative_provider": provider, "status_label": "READY FOR ASSESSOR DECISION", "disclaimer": DISCLAIMER,
            "created_at": r.created_at.isoformat()}


@router.get("/assessments/{assessment_id}/recommendation")
def get_recommendation(assessment_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = load_plan(db, assessment_id, user)
    _worker_gate(p, user)
    r = db.scalar(select(Recommendation).where(Recommendation.plan_id == p.id).order_by(Recommendation.created_at.desc()))
    if not r:
        return None
    prov = db.scalar(select(AIObservation.provider).where(AIObservation.id == r.narrative_ai_observation_id))
    return recommendation_out(r, prov)


class DecisionIn(BaseModel):
    plan_id: str
    decision: Literal["APPROVE", "REJECT", "REASSESS"]
    comments: str = Field(min_length=10, max_length=4000)
    reassess_task_codes: list[str] = Field(default_factory=list, max_length=20)


AGREES = {"APPROVE": "ELIGIBLE", "REJECT": "NOT_YET_READY", "REASSESS": "REASSESSMENT_SUGGESTED"}


@router.post("/assessor/decision")
def decide(body: DecisionIn, db: Session = Depends(get_db), user: User = Depends(require_roles("assessor"))):
    """The ONLY place a final outcome is recorded — by the assigned, authorised human assessor."""
    p = load_plan(db, body.plan_id, user)
    if p.assessor_id != user.id:
        raise Forbidden("Only the assigned assessor can record the decision.")
    workflow.require_plan_at_least(p, "UNDER_ASSESSOR_REVIEW", "record a decision")
    workflow.require_plan_before(p, "DECIDED", "record another decision")
    if body.decision == "REASSESS" and not body.reassess_task_codes:
        raise InvalidState("Choose the tasks to reassess.", code="validation_error")
    rec = db.scalar(select(Recommendation).where(Recommendation.plan_id == p.id).order_by(Recommendation.created_at.desc()))
    d = AssessorDecision(plan_id=p.id, assessor_id=user.id, decision=body.decision, comments=body.comments.strip(),
                         recommendation_id=rec.id if rec else None,
                         agrees_with_recommendation=(AGREES[body.decision] == rec.outcome) if rec else None,
                         reassess_task_codes=body.reassess_task_codes, data_origin=p.data_origin)
    db.add(d)
    workflow.advance_plan(db, p, "DECIDED", user)
    audit.record(db, "decision.recorded", "assessment_plan", p.id, actor=user,
                 summary=f"Final decision {body.decision} by assessor {user.assessor_code}"
                         + (f" ({'agrees with' if d.agrees_with_recommendation else 'differs from'} recommendation {rec.outcome})" if rec else ""),
                 after={"decision": body.decision, "reassess": body.reassess_task_codes})
    db.commit()
    return {"decision": decision_out(d, user), "plan": plan_view(db, p, user)}


def decision_out(d: AssessorDecision, assessor: User | None) -> dict:
    return {"id": d.id, "decision": d.decision, "comments": d.comments, "agrees_with_recommendation": d.agrees_with_recommendation,
            "reassess_task_codes": d.reassess_task_codes, "decided_at": d.created_at.isoformat(),
            "assessor": {"name": assessor.full_name, "code": assessor.assessor_code} if assessor else None}


@router.get("/assessments/{assessment_id}/decision")
def get_decision(assessment_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = load_plan(db, assessment_id, user)
    d = db.scalar(select(AssessorDecision).where(AssessorDecision.plan_id == p.id).order_by(AssessorDecision.created_at.desc()))
    return decision_out(d, db.get(User, d.assessor_id)) if d else None


# ---- Assessor workspace --------------------------------------------------------------------------
PENDING = ("EVIDENCE_SUBMITTED", "AI_EVIDENCE_REVIEWED", "ASSESSOR_SCORING", "SCORED", "RECOMMENDATION_GENERATED", "UNDER_ASSESSOR_REVIEW")


@router.get("/assessor/candidates")
def candidates(status: str | None = None, q: str | None = None, page: int = 1, page_size: int = 25,
               db: Session = Depends(get_db), user: User = Depends(require_roles("assessor", "admin"))):
    page_size = max(1, min(page_size, 100))
    stmt = select(AssessmentPlan, WorkerProfile).join(WorkerProfile, WorkerProfile.id == AssessmentPlan.worker_id)
    if user.role_code == "assessor":
        stmt = stmt.where(AssessmentPlan.assessor_id == user.id)
    if status == "pending":
        stmt = stmt.where(AssessmentPlan.status.in_(PENDING))
    elif status == "completed":
        stmt = stmt.where(AssessmentPlan.status.in_(RELEASED))
    elif status == "in_progress":
        stmt = stmt.where(AssessmentPlan.status.not_in(PENDING + RELEASED))
    elif status:
        stmt = stmt.where(AssessmentPlan.status == status)
    if q:
        stmt = stmt.where(WorkerProfile.full_name.ilike(f"%{q.strip()}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(stmt.order_by(AssessmentPlan.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    out = []
    for p, w in rows:
        res = plan_results(db, p)
        dec = db.scalar(select(AssessorDecision.decision).where(AssessorDecision.plan_id == p.id).order_by(AssessorDecision.created_at.desc()))
        rec = db.scalar(select(Recommendation.outcome).where(Recommendation.plan_id == p.id).order_by(Recommendation.created_at.desc()))
        submitted = db.scalar(select(func.count()).select_from(AssessmentAttempt).where(AssessmentAttempt.plan_id == p.id, AssessmentAttempt.status.in_(("SUBMITTED", "SCORED"))))
        out.append({
            "plan_id": p.id, "worker_id": w.id, "candidate": w.full_name, "trade": db.get(Qualification, p.qualification_id).trade.name,
            "qualification": (p.match_snapshot or {}).get("title"), "qualification_code": (p.match_snapshot or {}).get("qualification_code"),
            "experience_years": w.years_experience, "ai_match_pct": (p.match_snapshot or {}).get("final_pct"),
            "assessment_score": res["overall_pct"], "scored": f"{res['scored_criteria']}/{res['total_criteria']}",
            "tasks_submitted": submitted, "evidence_items": res["evidence_items"], "status": p.status,
            "ncvet_stage": workflow.NCVET_STAGE.get(p.status), "pathway": p.pathway, "recommendation": rec, "decision": dec,
            "data_origin": p.data_origin, "updated_at": p.updated_at.isoformat(),
        })
    return {"total": total, "page": page, "page_size": page_size, "rows": out}


@router.get("/analytics/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(require_roles("assessor", "admin"))):
    """KPIs computed from the database (assessor: own caseload; admin: all)."""
    base = select(AssessmentPlan)
    if user.role_code == "assessor":
        base = base.where(AssessmentPlan.assessor_id == user.id)
    plans = list(db.scalars(base))
    ids = [p.id for p in plans]
    decisions = list(db.scalars(select(AssessorDecision).where(AssessorDecision.plan_id.in_(ids)))) if ids else []
    scores, ev_cov = [], []
    for p in plans:
        r = plan_results(db, p)
        if r["overall_pct"] is not None:
            scores.append(r["overall_pct"])
        if p.status not in ("PLAN_CREATED", "SELF_ASSESSED", "READINESS_EVALUATED"):
            ev_cov.append(r["evidence_coverage"])
    ai_cases = db.scalar(select(func.count(func.distinct(AIObservation.plan_id))).where(
        AIObservation.plan_id.in_(ids), AIObservation.kind == "evidence_analysis")) if ids else 0
    agree = [d.agrees_with_recommendation for d in decisions if d.agrees_with_recommendation is not None]
    mean = sum(scores) / len(scores) if scores else None
    var = sum((x - mean) ** 2 for x in scores) / (len(scores) - 1) if len(scores) > 1 else None
    by_status: dict[str, int] = {}
    for p in plans:
        by_status[p.status] = by_status.get(p.status, 0) + 1
    return {
        "assigned": len(plans),
        "pending_review": sum(p.status in PENDING for p in plans),
        "in_progress": sum(p.status not in PENDING + RELEASED for p in plans),
        "completed": sum(p.status in RELEASED for p in plans),
        "reassessments": sum(d.decision == "REASSESS" for d in decisions),
        "approved": sum(d.decision == "APPROVE" for d in decisions),
        "average_score": round(mean, 1) if mean is not None else None,
        "score_variance_across_candidates": round(var, 1) if var is not None else None,
        "evidence_coverage": round(sum(ev_cov) / len(ev_cov), 4) if ev_cov else None,
        "ai_assisted_cases": ai_cases,
        "decision_agreement_with_recommendation": round(sum(agree) / len(agree), 4) if agree else None,
        "by_status": by_status,
        "evidence_items": db.scalar(select(func.count()).select_from(Evidence).where(Evidence.plan_id.in_(ids))) if ids else 0,
        "note": "Score variance here is across different candidates (spread of ability), not assessor disagreement — see /analytics/consistency.",
    }


@router.get("/analytics/consistency")
def consistency(db: Session = Depends(get_db), user: User = Depends(require_roles("assessor", "admin"))):
    """Multi-rater consistency on the labelled SIMULATION dataset: baseline vs standardised workflow.
    Every statistic is computed from the stored ratings at request time."""
    from app.services.consistency import analyse
    return analyse(db)
