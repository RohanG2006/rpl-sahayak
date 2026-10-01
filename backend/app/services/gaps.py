"""Skill-gap engine: required − demonstrated, per competency area and per in-scope learning outcome.

Learning topics come from the OFFICIAL LO assessment criteria behind low-scoring rubric criteria. Anything not
directly from the QF is labelled `suggested` (never presented as an official training requirement).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AssessmentPlan, AssessorScore, Qualification
from app.services.results import plan_results, plan_tasks

LOW_SCORE = 2  # criteria scored ≤ 2 ("partially demonstrated" or below) generate learning topics


def compute_gaps(db: Session, plan: AssessmentPlan, results: dict | None = None) -> dict:
    required = get_settings().competency_required_pct
    res = results or plan_results(db, plan)
    q = db.get(Qualification, plan.qualification_id)
    los = {c.lo_number: c for c in q.competencies if c.category == "trade"}
    finals = {s.criterion_id: s.final_score for s in db.scalars(select(AssessorScore).where(AssessorScore.plan_id == plan.id))}
    tasks = plan_tasks(db, plan)

    areas = []
    for key, pct in res["competencies"].items():
        k_tasks = [t for t in tasks if t.competency_key == key]
        topics, seen = [], set()
        for t in k_tasks:
            for c in t.criteria:
                s = finals.get(c.id)
                if s is None or s > LOW_SCORE:
                    continue
                ref = c.qf_criterion_ref or ""
                if ref.startswith("LO") and ref not in seen:
                    seen.add(ref)
                    topics.append({"topic": ref.split(": ", 1)[1], "lo_number": int(ref[2:ref.index(":")]),
                                   "source": "official", "because": f"{c.criterion_code} scored {s}/4"})
                topics.append({"topic": f"Practise: {c.text}", "lo_number": None, "source": "suggested",
                               "because": f"{c.criterion_code} scored {s}/4" + (" (safety-critical)" if c.is_safety_critical else "")})
        gap = None if pct is None else round(max(0.0, required - pct), 2)
        areas.append({
            "competency_key": key, "label": res["competency_labels"].get(key, key),
            "label_hi": res["competency_labels_hi"].get(key, key),
            "required": required, "demonstrated": pct, "gap": gap,
            "status": "not_assessed" if pct is None else ("gap" if gap > 0 else "met"),
            "learning_topics": topics,
        })

    lo_rows = []
    for lo, pct in res["learning_outcomes"].items():
        lo_rows.append({"lo_number": lo, "title": los[lo].title if lo in los else "", "required": required,
                        "demonstrated": pct, "gap": None if pct is None else round(max(0.0, required - pct), 2)})
    in_scope = set(res["learning_outcomes"])
    out_of_scope = [{"lo_number": n, "title": c.title} for n, c in sorted(los.items()) if n not in in_scope]
    return {
        "required_pct": required,
        "required_source": "QF DGT/1001 §23 minimum pass for Trade Practical (60%) — used as the prototype competency threshold",
        "areas": sorted(areas, key=lambda a: -(a["gap"] or 0)),
        "learning_outcomes": lo_rows,
        "not_assessed_in_prototype": out_of_scope,
        "note": "Learning topics marked 'official' quote the qualification's assessment criteria; 'suggested' topics are "
                "prototype guidance, not official training requirements.",
    }
