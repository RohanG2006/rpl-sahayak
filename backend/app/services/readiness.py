"""RPL readiness from self-assessment (pre-screening). Deterministic.

Scope = learning outcomes covered by the plan's practical tasks ("declared learning outcomes" for this assessment).
Pathway rule: NCVET RPL Guidelines (Gazette 19-Jun-2024) §6.2(c) — direct RPL assessment requires the applicant to
have met > 70 % of the declared learning outcomes; Annexure-1 routes others to skill-gap training / upskilling.
Self-assessment is the worker's own claim; it routes the candidate, it never scores them.
"""
from app.core.config import get_settings

CLAIM_VALUE = {"regularly": 1.0, "sometimes": 0.5, "never": 0.0}


def evaluate(scope_los: list[int], responses: dict[int, str], match_snapshot: dict, eligibility: list[dict]) -> dict:
    s = get_settings()
    lo_rows = {r["lo_number"]: r for r in match_snapshot.get("learning_outcomes", [])}
    rows = []
    for lo in scope_los:
        claim = responses.get(lo, "never")
        evid = lo_rows.get(lo, {}).get("status", "not_evidenced")
        rows.append({
            "lo_number": lo,
            "claim": claim,
            "claim_value": CLAIM_VALUE[claim],
            "declaration_evidence": evid,
            "corroborated": claim != "never" and evid in ("matched", "partial"),
            "needs_probe": claim == "regularly" and evid == "not_evidenced",
        })
    n = len(rows) or 1
    claimed = sum(r["claim"] != "never" for r in rows) / n
    weighted = sum(r["claim_value"] for r in rows) / n
    corroborated = sum(r["corroborated"] for r in rows) / n
    threshold = s.lo_coverage_required
    elig_fail = [c for c in eligibility if c["result"] == "fail"]
    elig_unknown = [c for c in eligibility if c["result"] == "unknown"]
    pathway = "DIRECT_ASSESSMENT" if weighted > threshold else "UPSKILLING_SUGGESTED"
    reasons = [
        f"Self-assessed coverage of in-scope learning outcomes: {weighted:.0%} (regularly = 1, sometimes = 0.5) "
        f"{'>' if weighted > threshold else '≤'} {threshold:.0%} threshold (NCVET RPL Guidelines §6.2(c)).",
        f"{corroborated:.0%} of claims are also supported by the experience declaration.",
    ]
    if elig_fail:
        reasons.append("Category IV eligibility not met: " + "; ".join(c["label"] for c in elig_fail)
                       + ". The assessor decides whether another category applies.")
    if elig_unknown:
        reasons.append("Eligibility information missing: " + "; ".join(c["label"] for c in elig_unknown) + ".")
    return {
        "scope_los": scope_los,
        "rows": rows,
        "claimed_share": round(claimed, 4),
        "weighted_coverage": round(weighted, 4),
        "corroborated_share": round(corroborated, 4),
        "threshold": threshold,
        "threshold_source": "NCVET RPL Guidelines (Gazette No. 420, 19 Jun 2024) §6.2(c)",
        "pathway": pathway,
        "eligibility_flags": [c["key"] for c in elig_fail],
        "probe_los": [r["lo_number"] for r in rows if r["needs_probe"]],
        "reasons": reasons,
        "note": "Self-assessment routes the candidate; it is not a score. The practical assessment decides competence.",
    }
