"""Certification recommendation for assessor sign-off. Deterministic, ordered rules; every rule evaluated is traced.

This is an AI-assisted RECOMMENDATION. The decision is recorded only by an authorised assessor (assessor_decisions).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AIObservation, AssessmentPlan, AssessorScore
from app.services.results import plan_results

DISCLAIMER = "AI-assisted assessment recommendation — final decision by authorised human assessor."
MIN_EVIDENCE_COVERAGE = 0.5  # project design rule


def recommend(db: Session, plan: AssessmentPlan, results: dict | None = None) -> dict:
    s = get_settings()
    res = results or plan_results(db, plan)
    req = s.competency_required_pct
    trace: list[dict] = []

    los = {k: v for k, v in res["learning_outcomes"].items() if v is not None}
    met = sum(v >= req for v in los.values())
    lo_share = met / len(los) if los else 0.0
    overall = res["overall_pct"]
    ev_cov = res["evidence_coverage"]

    def rule(rid, label, passed, detail, source):
        trace.append({"rule": rid, "label": label, "passed": passed, "detail": detail, "source": source})
        return passed

    outcome = None
    complete = rule("R0", "All rubric criteria scored by the assessor", res["complete"],
                    f"{res['scored_criteria']}/{res['total_criteria']} criteria have assessor-confirmed scores", "Workflow rule")
    if not complete:
        outcome = "REASSESSMENT_SUGGESTED"
    ev_ok = rule("R1", f"Evidence coverage ≥ {MIN_EVIDENCE_COVERAGE:.0%} of required evidence items", ev_cov >= MIN_EVIDENCE_COVERAGE,
                 f"{ev_cov:.0%} of required evidence uploaded" + (f"; missing: {', '.join(res['evidence_missing'])}" if res["evidence_missing"] else ""),
                 "Project design rule (evidence-based assessment, QF §24 'Means of assessment')")
    if outcome is None and not ev_ok:
        outcome = "REASSESSMENT_SUGGESTED"
    safe = rule("R2", "No safety-critical criterion scored 0 or 1", not res["safety_flags"],
                "Safety-critical criteria at 0–1: " + (", ".join(res["safety_flags"]) or "none"),
                "Project design rule; QF §25 notes errors in these outcomes 'could cause fatal accidents'")
    if outcome is None and not safe:
        outcome = "NOT_YET_READY"
    lo_ok = rule("R3", f"More than {s.lo_coverage_required:.0%} of assessed learning outcomes at ≥ {req:.0f}%", lo_share > s.lo_coverage_required,
                 f"{met} of {len(los)} assessed LOs met ({lo_share:.0%})", "NCVET RPL Guidelines (Gazette 19 Jun 2024) §6.2(c)")
    ov_ok = rule("R4", f"Overall practical score ≥ {req:.0f}%", overall is not None and overall >= req,
                 f"Overall {overall if overall is not None else '—'}%", "QF DGT/1001 §23: minimum pass for Trade Practical 60%")
    if outcome is None:
        outcome = "ELIGIBLE" if (lo_ok and ov_ok) else "NOT_YET_READY"

    # Informational flags (never change the outcome)
    flags = []
    scores = list(db.scalars(select(AssessorScore).where(AssessorScore.plan_id == plan.id)))
    with_ai = [x for x in scores if x.ai_suggested_score is not None and x.final_score is not None]
    if with_ai:
        share = sum(x.overrode_ai for x in with_ai) / len(with_ai)
        if share >= 0.3:
            flags.append(f"Assessor overrode {share:.0%} of AI score suggestions — AI assistance had low agreement on this case")
    confs = [o.confidence for o in db.scalars(select(AIObservation).where(AIObservation.plan_id == plan.id, AIObservation.kind == "evidence_analysis")) if o.confidence is not None]
    if confs and sum(confs) / len(confs) < 0.5:
        flags.append(f"Mean AI evidence confidence {sum(confs) / len(confs):.2f} (< 0.50)")
    rd = plan.readiness_snapshot or {}
    if rd.get("probe_los"):
        flags.append(f"Self-assessment claims not supported by the declaration for LO {', '.join(map(str, rd['probe_los']))}")
    if rd.get("eligibility_flags"):
        flags.append("RPL Category IV eligibility not met: " + ", ".join(rd["eligibility_flags"]) + " — assessor to determine applicable category")

    competency_cov = round(lo_share, 4)
    return {
        "outcome": outcome,
        "competency_coverage": competency_cov,
        "evidence_coverage": ev_cov,
        "overall_pct": overall,
        "rule_trace": trace,
        "flags": flags,
        "status_label": "READY FOR ASSESSOR DECISION",
        "disclaimer": DISCLAIMER,
        "scope_note": f"Recommendation covers the {len(los)} learning outcomes assessed in this prototype, not the full qualification.",
    }
