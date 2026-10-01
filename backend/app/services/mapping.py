"""Qualification-pack mapping engine (deterministic, explainable). See docs/methodology.md §1.

final = w_skill·skill_sim + w_task·task_sim + w_exp·experience_rel + w_occ·occupation_sim + w_elig·eligibility

similarity(phrase, LO) = Σ idf(t) for t ∈ phrase ∩ LO  /  Σ idf(t) for t ∈ phrase      ("IDF-weighted term recall")
LO text = official LO title + official assessment criteria (QF). Worker phrases = confirmed items, expanded with
the project lexicon's technical phrasing for colloquial terms. No model training, no hidden scores.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.core.config import get_match_weights, get_settings
from app.models import Qualification, WorkerProfile
from app.models.workers import EDUCATION_RANKS
from app.services.text import find_term, lexicon, tokens

MATCHED, PARTIAL = 0.5, 0.3
SUPPORTING_KINDS = ("tool", "equipment", "safety")  # shown as supporting evidence, not mapped to LOs

# Generic verbs/nouns that open almost every LO assessment criterion; they carry no trade content and
# would otherwise make every LO look "partially" matched.
GENERIC = set(tokens(
    "test tests testing check checks install installation plan planning perform carry carryout prepare preparation "
    "make identify identification safety safe precaution precautions work norms standard compliance comply connect "
    "connection demonstrate explain maintenance maintain service repair repairing troubleshoot fault faults detect "
    "detection execute evaluate evaluation performance different various given required requirement type types use "
    "using operation operate field practical apply application determine verify measure measurement"
))


@dataclass
class Phrase:
    label: str
    kind: str
    toks: set[str]


@dataclass
class LODoc:
    lo_number: int
    title: str
    nos: list[str]
    toks: set[str]
    skill_hours: int | None


@dataclass
class Corpus:
    idf: dict[str, float]
    docs: dict[str, list[LODoc]] = field(default_factory=dict)  # qualification_id -> LO docs


def build_corpus(quals: list[Qualification]) -> Corpus:
    docs: dict[str, list[LODoc]] = {}
    df: dict[str, int] = {}
    n = 0
    for q in quals:
        out = []
        for c in q.competencies:
            if c.category != "trade":
                continue
            toks = set(tokens(" ".join([c.title, *c.assessment_criteria]))) - GENERIC
            out.append(LODoc(c.lo_number, c.title, c.nos_codes_summary or c.nos_codes_lo_table, toks, c.skill_hours))
            for t in toks:
                df[t] = df.get(t, 0) + 1
            n += 1
        docs[q.id] = out
    idf = {t: math.log(1 + n / d) for t, d in df.items()}
    return Corpus(idf=idf, docs=docs)


def _expand(label: str) -> str:
    """Append the lexicon's technical phrasing when the label is (or contains) a known colloquial term."""
    lex = lexicon()
    low = label.lower()
    extra = []
    for e in lex["skills"]:
        if e["canonical"].lower() == low or any(find_term(low, t) >= 0 for t in e["terms"]):
            extra.append(e.get("expand", ""))
    return label + " " + " ".join(extra)


def _toks(text: str) -> set[str]:
    return set(tokens(_expand(text))) - GENERIC


def worker_phrases(worker: WorkerProfile) -> tuple[list[Phrase], list[Phrase], list[Phrase]]:
    skills, tasks, supporting = [], [], []
    for s in worker.skills:
        if not s.confirmed:
            continue
        if s.kind == "skill":
            skills.append(Phrase(s.label, s.kind, _toks(s.label)))
        elif s.kind == "task":
            tasks.append(Phrase(s.label, s.kind, _toks(s.label)))
        elif s.kind in SUPPORTING_KINDS:
            supporting.append(Phrase(s.label, s.kind, set()))
    if worker.typical_work:
        for sent in worker.typical_work.split("."):
            if len(sent.strip()) > 8:
                tasks.append(Phrase(sent.strip(), "task", _toks(sent)))
    return skills, tasks, supporting


def sim(p: Phrase, d: LODoc, idf: dict[str, float]) -> float:
    if not p.toks:
        return 0.0
    den = sum(idf.get(t, 0.0) for t in p.toks)
    if den == 0:
        return 0.0
    return sum(idf.get(t, 0.0) for t in p.toks & d.toks) / den


def _best(p: Phrase, docs: list[LODoc], idf) -> tuple[float, LODoc | None]:
    best, bd = 0.0, None
    for d in docs:
        s = sim(p, d, idf)
        if s > best:
            best, bd = s, d
    return best, bd


def occupation_similarity(occupation: str | None, q: Qualification) -> float:
    if not occupation:
        return 0.0
    lex = lexicon()
    occ_low = occupation.lower()
    canonical = next((o["canonical"] for o in lex["occupations"] if any(find_term(occ_low, t) >= 0 for t in o["terms"])), occupation)
    targets = [q.title, *q.occupations, *[n["title"] for n in q.nco_codes]]
    if any(canonical.lower() == t.lower() for t in targets):
        return 1.0
    wt = set(tokens(canonical))
    qt = set(tokens(" ".join(targets)))
    return round(len(wt & qt) / len(wt), 3) if wt else 0.0


def eligibility_checks(worker: WorkerProfile, q: Qualification) -> list[dict]:
    """QF §22 Category IV (other candidates) — the category applicable to informally trained workers."""
    s = get_settings()
    cat = (q.rpl_eligibility or {}).get("category_iv_other_candidates", {})
    min_age, min_years = cat.get("min_age", s.rpl_min_age), cat.get("min_experience_years", s.rpl_min_years)
    src = f"QF {q.qualification_code} §22 Category IV, p.{cat.get('page', '?')}"
    checks = []

    def add(key, label, result, detail, source=src):
        checks.append({"key": key, "label": label, "result": result, "score": {"pass": 1.0, "unknown": 0.5, "fail": 0.0}[result],
                       "detail": detail, "source": source})

    if worker.age is None:
        add("age", f"Age ≥ {min_age}", "unknown", "Age not provided")
    else:
        add("age", f"Age ≥ {min_age}", "pass" if worker.age >= min_age else "fail", f"Declared age {worker.age}")
    if worker.years_experience is None:
        add("experience", f"Experience ≥ {min_years} years", "unknown", "Years not provided")
    else:
        add("experience", f"Experience ≥ {min_years} years", "pass" if worker.years_experience >= min_years else "fail",
            f"Declared {worker.years_experience:g} years (self-declared; documentary verification is the assessor's role)")
    entry_src = f"QF {q.qualification_code} item 15 (entry requirements)"
    if worker.education_level is None or q.entry_education_rank is None:
        add("education", "Entry qualification", "unknown", q.entry_requirements or "Not stated", entry_src)
    else:
        ok = EDUCATION_RANKS.get(worker.education_level, 0) >= q.entry_education_rank
        if ok and q.entry_requires_science_maths:
            if worker.has_science_maths is None:
                add("education", "Entry qualification", "unknown", f"{q.entry_requirements} — Science/Maths not confirmed", entry_src)
            else:
                add("education", "Entry qualification", "pass" if worker.has_science_maths else "fail",
                    f"{q.entry_requirements} — declared {worker.education_level}, Science/Maths: {'yes' if worker.has_science_maths else 'no'}", entry_src)
        else:
            add("education", "Entry qualification", "pass" if ok else "fail", f"{q.entry_requirements} — declared {worker.education_level}", entry_src)
    return checks


def match_one(worker: WorkerProfile, q: Qualification, corpus: Corpus) -> dict:
    weights = get_match_weights().as_dict()
    docs, idf = corpus.docs[q.id], corpus.idf
    skills, tasks, supporting = worker_phrases(worker)

    matched, unclear = [], []
    skill_scores = []
    for p in skills:
        s, d = _best(p, docs, idf)
        skill_scores.append(s)
        row = {"label": p.label, "kind": p.kind, "similarity": round(s, 3),
               "lo_number": d.lo_number if d else None, "lo_title": d.title if d else None, "nos": d.nos if d else []}
        (matched if s >= MATCHED else unclear).append({**row, "status": "matched" if s >= MATCHED else ("partial" if s >= PARTIAL else "unclear")})
    skill_sim = sum(skill_scores) / len(skill_scores) if skill_scores else 0.0

    task_basis = "tasks" if tasks else "skills (no work sentences declared)"
    tsrc = tasks or skills
    task_scores = [_best(p, docs, idf)[0] for p in tsrc]
    task_sim = sum(task_scores) / len(task_scores) if task_scores else 0.0

    lo_rows = []
    for d in docs:
        best, by = 0.0, None
        for p in skills + tasks:
            s = sim(p, d, idf)
            if s > best:
                best, by = s, p.label
        status = "matched" if best >= MATCHED else "partial" if best >= PARTIAL else "not_evidenced"
        lo_rows.append({"lo_number": d.lo_number, "title": d.title, "nos": d.nos, "status": status,
                        "similarity": round(best, 3), "matched_by": by if status != "not_evidenced" else None,
                        "skill_hours": d.skill_hours})
    n_m = sum(r["status"] == "matched" for r in lo_rows)
    n_p = sum(r["status"] == "partial" for r in lo_rows)
    lo_cov = (n_m + 0.5 * n_p) / len(lo_rows) if lo_rows else 0.0

    occ = occupation_similarity(worker.occupation, q)
    years = worker.years_experience or 0.0
    exp_rel = min(1.0, years / get_settings().rpl_min_years) * (1.0 if occ >= 0.5 else 0.6)
    checks = eligibility_checks(worker, q)
    elig = sum(c["score"] for c in checks) / len(checks)

    components = {"skill": skill_sim, "task": task_sim, "experience": exp_rel, "occupation": occ, "eligibility": elig}
    final = sum(weights[k] * components[k] for k in weights) / sum(weights.values())
    not_evidenced = sorted([r for r in lo_rows if r["status"] == "not_evidenced"], key=lambda r: -(r["skill_hours"] or 0))

    return {
        "qualification_id": q.id,
        "qualification_code": q.qualification_code,
        "title": q.title,
        "nsqf_level": q.nsqf_level,
        "is_assessable": q.trade.is_assessable,
        "source_url": q.source.url,
        "final_score": round(final, 4),
        "final_pct": round(final * 100),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "contributions": {k: round(weights[k] * components[k] / sum(weights.values()), 4) for k in weights},
        "task_basis": task_basis,
        "matched_skills": sorted(matched, key=lambda r: -r["similarity"]),
        "unclear_skills": sorted(unclear, key=lambda r: -r["similarity"]),
        "supporting_evidence": [{"label": p.label, "kind": p.kind} for p in supporting],
        "lo_coverage": {"matched": n_m, "partial": n_p, "total": len(lo_rows), "pct": round(lo_cov * 100)},
        "learning_outcomes": lo_rows,
        "areas_not_evidenced": [{"lo_number": r["lo_number"], "title": r["title"]} for r in not_evidenced[:8]],
        "eligibility": checks,
    }


def match_worker(worker: WorkerProfile, quals: list[Qualification]) -> dict:
    corpus = build_corpus(quals)
    results = sorted((match_one(worker, q, corpus) for q in quals), key=lambda r: -r["final_score"])
    for i, r in enumerate(results, 1):
        r["rank"] = i
    return {
        "method": "IDF-weighted term recall between worker's confirmed items and official LO text; weighted sum of 5 components",
        "thresholds": {"matched": MATCHED, "partial": PARTIAL},
        "results": results,
    }
