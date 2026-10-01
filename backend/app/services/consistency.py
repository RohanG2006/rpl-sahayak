"""Assessor-consistency analysis over the multi-rater dataset (consistency_ratings, data_origin='simulation').

Case score per assessor uses the SAME weighted formula as real assessments (services.scoring), so the dashboard
compares exactly what candidates would receive. All statistics are computed at request time from the rows.
"""
from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from itertools import combinations
from statistics import mean, median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import DATA_DIR
from app.models import ConsistencyRating
from app.services import scoring, stats

MODES = ("baseline", "standardised")
LABEL = "Prototype / Test Dataset Demonstration — not real-world validated improvement"


@lru_cache
def _bank() -> tuple[list[scoring.TaskDef], dict[str, tuple[str, float, str, bool]]]:
    d = json.loads((DATA_DIR / "assessment" / "electrician_tasks.json").read_text(encoding="utf-8"))
    tasks = [scoring.TaskDef(t["task_id"], t["weight"], t["competency_id"], tuple(t["lo_numbers"])) for t in d["tasks"]]
    crit = {c["criterion_id"]: (t["task_id"], c["weight"], c["qf_dimension"], c["is_safety_critical"]) for t in d["tasks"] for c in t["criteria"]}
    return tasks, crit


def _params() -> dict:
    p = DATA_DIR / "demo" / "consistency_parameters.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load(db: Session) -> dict[str, dict]:
    """→ {mode: {case: {assessor: {criterion: score}}}}"""
    data: dict[str, dict] = {m: defaultdict(lambda: defaultdict(dict)) for m in MODES}
    for r in db.scalars(select(ConsistencyRating)):
        data[r.mode][r.case_id][r.assessor_id][r.criterion_code] = r.score
    return data


def _case_scores(ratings: dict[str, int]) -> dict:
    tasks, crit = _bank()
    cs = [scoring.CriterionScore(crit[c][0], c, crit[c][1], s, crit[c][2], crit[c][3]) for c, s in ratings.items() if c in crit]
    return scoring.compute(tasks, cs)


def analyse(db: Session) -> dict:
    data = load(db)
    if not any(data[m] for m in MODES):
        return {"label": LABEL, "available": False}
    out: dict = {"label": LABEL, "available": True, "parameters": _params(), "modes": {}, "cases": {}}
    assessors = sorted({a for m in MODES for c in data[m].values() for a in c})
    cases = sorted(data["baseline"])
    for m in MODES:
        overall: dict[str, dict[str, float]] = {}
        task_pct: dict[str, dict[str, dict]] = {}
        for c in cases:
            overall[c], task_pct[c] = {}, {}
            for a in assessors:
                res = _case_scores(data[m][c][a])
                overall[c][a] = res["overall_pct"]
                task_pct[c][a] = {k: v["task_pct"] for k, v in res["tasks"].items()}
        spreads = {c: stats.spread(list(overall[c].values())) for c in cases}
        # criterion-level items: every (case, criterion) rated by all assessors
        items = [[data[m][c][a][k] for a in assessors] for c in cases for k in sorted(data[m][c][assessors[0]])]
        exact, adjacent = stats.pairwise_agreement(items)
        counts = [[row.count(v) for v in range(5)] for row in items]
        pair_k = {f"{x}-{y}": stats.cohen_kappa([r[i] for r in items], [r[j] for r in items], [0, 1, 2, 3, 4], "quadratic")
                  for (i, x), (j, y) in combinations(enumerate(assessors), 2)}
        matrix = [[overall[c][a] for a in assessors] for c in cases]
        out["modes"][m] = {
            "mean_case_sd": mean(s["sd"] for s in spreads.values()),
            "mean_case_variance": mean(s["variance"] for s in spreads.values()),
            "mean_case_range": mean(s["range"] for s in spreads.values()),
            "max_case_range": max(s["range"] for s in spreads.values()),
            "exact_agreement": exact, "adjacent_agreement": adjacent,
            "fleiss_kappa": stats.fleiss_kappa(counts),
            "mean_pairwise_weighted_kappa": mean(v for v in pair_k.values() if v is not None),
            "pairwise_weighted_kappa": pair_k,
            "icc_2_1": stats.icc_2_1(matrix),
            "assessor_mean": {a: mean(overall[c][a] for c in cases) for a in assessors},
            "assessor_sd": {a: stats.spread([overall[c][a] for c in cases])["sd"] for a in assessors},
            "score_distribution": {a: [sum(1 for c in cases for v in data[m][c][a].values() if v == s) for s in range(5)] for a in assessors},
            "n_items": len(items), "n_cases": len(cases), "n_assessors": len(assessors),
        }
        for c in cases:
            out["cases"].setdefault(c, {})[m] = {"overall": overall[c], "spread": spreads[c], "tasks": task_pct[c]}

    b, s = out["modes"]["baseline"], out["modes"]["standardised"]

    def rel(key: str, lower_is_better: bool) -> dict:
        before, after = b[key], s[key]
        change = after - before
        pct = (change / before * 100) if before else None
        return {"before": before, "after": after, "change": change, "relative_pct": pct,
                "improved": (change < 0) if lower_is_better else (change > 0)}

    out["change"] = {
        "mean_case_sd": rel("mean_case_sd", True), "mean_case_variance": rel("mean_case_variance", True),
        "mean_case_range": rel("mean_case_range", True), "exact_agreement": rel("exact_agreement", False),
        "adjacent_agreement": rel("adjacent_agreement", False), "fleiss_kappa": rel("fleiss_kappa", False),
        "mean_pairwise_weighted_kappa": rel("mean_pairwise_weighted_kappa", False), "icc_2_1": rel("icc_2_1", False),
    }
    ranked = sorted(cases, key=lambda c: out["cases"][c]["baseline"]["spread"]["range"])
    featured = ranked[len(ranked) // 2]
    out["featured_case"] = {"case_id": featured, "rule": "Case with the median baseline score range (not the most dramatic case)",
                            "median_baseline_range": median(out["cases"][c]["baseline"]["spread"]["range"] for c in cases)}
    out["assessors"] = assessors
    out["case_ids"] = cases
    return out
