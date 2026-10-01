"""Standardised scoring engine (pure functions, no I/O). See docs/assessment-rubric.md.

Only assessor-confirmed final scores enter these calculations. AI-suggested scores never do.

  task_pct    = Σ(w_c · s_c) / (4 · Σ w_c) · 100            over scored criteria of the task
  lo_pct      = Σ(w_t · task_pct) / Σ w_t                     over tasks mapped to the LO
  dim_pct     = Σ(w_c · s_c) / (4 · Σ w_c) · 100            over criteria tagged with the QF formative dimension
  overall_pct = Σ(w_t · task_pct) / Σ w_t                     over fully scored tasks
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CriterionScore:
    task_code: str
    criterion_code: str
    weight: float
    score: int | None  # assessor-confirmed 0..4, None = not yet scored
    dimension: str
    safety_critical: bool


@dataclass(frozen=True)
class TaskDef:
    task_code: str
    weight: float
    competency_key: str
    lo_numbers: tuple[int, ...]


def _pct(items: list[CriterionScore]) -> float | None:
    scored = [c for c in items if c.score is not None]
    if not scored:
        return None
    den = 4 * sum(c.weight for c in scored)
    return round(100 * sum(c.weight * c.score for c in scored) / den, 2) if den else None


def task_scores(tasks: list[TaskDef], crits: list[CriterionScore]) -> dict[str, dict]:
    out = {}
    for t in tasks:
        cs = [c for c in crits if c.task_code == t.task_code]
        n_scored = sum(c.score is not None for c in cs)
        out[t.task_code] = {
            "task_pct": _pct(cs),
            "complete": n_scored == len(cs) and len(cs) > 0,
            "scored": n_scored,
            "total": len(cs),
        }
    return out


def lo_scores(tasks: list[TaskDef], per_task: dict[str, dict]) -> dict[int, float | None]:
    los = sorted({lo for t in tasks for lo in t.lo_numbers})
    out = {}
    for lo in los:
        pairs = [(t.weight, per_task[t.task_code]["task_pct"]) for t in tasks if lo in t.lo_numbers and per_task[t.task_code]["task_pct"] is not None]
        out[lo] = round(sum(w * p for w, p in pairs) / sum(w for w, _ in pairs), 2) if pairs else None
    return out


def competency_scores(tasks: list[TaskDef], per_task: dict[str, dict]) -> dict[str, float | None]:
    keys = sorted({t.competency_key for t in tasks})
    out = {}
    for k in keys:
        pairs = [(t.weight, per_task[t.task_code]["task_pct"]) for t in tasks if t.competency_key == k and per_task[t.task_code]["task_pct"] is not None]
        out[k] = round(sum(w * p for w, p in pairs) / sum(w for w, _ in pairs), 2) if pairs else None
    return out


def dimension_scores(crits: list[CriterionScore]) -> dict[str, float | None]:
    dims = sorted({c.dimension for c in crits})
    return {d: _pct([c for c in crits if c.dimension == d]) for d in dims}


def overall(tasks: list[TaskDef], per_task: dict[str, dict]) -> float | None:
    pairs = [(t.weight, per_task[t.task_code]["task_pct"]) for t in tasks if per_task[t.task_code]["complete"]]
    return round(sum(w * p for w, p in pairs) / sum(w for w, _ in pairs), 2) if pairs else None


def safety_flags(crits: list[CriterionScore], gate_max: int = 1) -> list[str]:
    return [c.criterion_code for c in crits if c.safety_critical and c.score is not None and c.score <= gate_max]


def compute(tasks: list[TaskDef], crits: list[CriterionScore]) -> dict:
    per_task = task_scores(tasks, crits)
    return {
        "tasks": per_task,
        "learning_outcomes": lo_scores(tasks, per_task),
        "competencies": competency_scores(tasks, per_task),
        "dimensions": dimension_scores(crits),
        "overall_pct": overall(tasks, per_task),
        "scored_criteria": sum(c.score is not None for c in crits),
        "total_criteria": len(crits),
        "complete": all(v["complete"] for v in per_task.values()) and bool(per_task),
        "safety_flags": safety_flags(crits),
    }
