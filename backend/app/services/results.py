"""DB adapter: load a plan's tasks/criteria/final scores and run the pure scoring engine."""
import json
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import DATA_DIR
from app.models import AssessmentPlan, AssessmentTask, AssessorScore, Evidence, Qualification
from app.services import scoring


@lru_cache
def competency_labels(trade: str = "electrician") -> dict:
    return json.loads((DATA_DIR / "assessment" / f"{trade}_tasks.json").read_text(encoding="utf-8"))["competencies"]


def plan_tasks(db: Session, plan: AssessmentPlan) -> list[AssessmentTask]:
    q = db.get(Qualification, plan.qualification_id)
    return list(db.scalars(select(AssessmentTask).where(
        AssessmentTask.trade_id == q.trade_id, AssessmentTask.task_code.in_(plan.task_codes)).order_by(AssessmentTask.sort_order)))


def plan_results(db: Session, plan: AssessmentPlan) -> dict:
    tasks = plan_tasks(db, plan)
    finals = {s.criterion_id: s.final_score for s in db.scalars(select(AssessorScore).where(AssessorScore.plan_id == plan.id))}
    tdefs = [scoring.TaskDef(t.task_code, t.weight, t.competency_key, tuple(t.lo_numbers)) for t in tasks]
    crits = [scoring.CriterionScore(t.task_code, c.criterion_code, c.weight, finals.get(c.id), c.qf_dimension, c.is_safety_critical)
             for t in tasks for c in t.criteria]
    out = scoring.compute(tdefs, crits)

    ev = list(db.scalars(select(Evidence.criterion_id).where(Evidence.plan_id == plan.id, Evidence.purpose == "assessment",
                                                             Evidence.upload_status == "uploaded")))
    with_evidence = {e for e in ev if e}
    all_crit = [c for t in tasks for c in t.criteria]
    required_crit = {f"{r['criterion']}" for t in tasks for r in t.evidence_required}
    req_ids = [c.id for c in all_crit if c.criterion_code in required_crit]
    out["evidence_coverage"] = round(sum(cid in with_evidence for cid in req_ids) / len(req_ids), 4) if req_ids else 1.0
    out["evidence_missing"] = sorted(c.criterion_code for c in all_crit if c.id in req_ids and c.id not in with_evidence)
    out["evidence_items"] = len(ev)
    labels = competency_labels()
    out["competency_labels"] = {k: v["label"] for k, v in labels.items()}
    out["competency_labels_hi"] = {k: v.get("label_hi", v["label"]) for k, v in labels.items()}
    out["task_titles"] = {t.task_code: t.title for t in tasks}
    out["task_competency"] = {t.task_code: t.competency_key for t in tasks}
    return out
