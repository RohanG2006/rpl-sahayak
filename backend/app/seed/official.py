"""Load OFFICIAL qualification data and the project-authored task bank into the database (idempotent).

Trade packs are discovered from data/qualifications/*_qualification.json; a trade is assessable only
when data/assessment/<slug>_tasks.json exists. Adding a trade = adding these files (spec §61).
"""
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import DATA_DIR
from app.models import (
    AssessmentCriterion, AssessmentTask, Qualification, QualificationCompetency, QualificationNos,
    QualificationSource, Trade,
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_qualifications(db: Session) -> list[Qualification]:
    out = []
    for path in sorted((DATA_DIR / "qualifications").glob("*_qualification.json")):
        d = _load(path)
        src = d["source"]
        trade = db.scalar(select(Trade).where(Trade.code == d["trade_code"]))
        if not trade:
            trade = Trade(code=d["trade_code"], name=d["title"].title())
            db.add(trade)
        trade.is_assessable = bool(d.get("is_assessable"))
        source = db.scalar(select(QualificationSource).where(QualificationSource.url == src["source_url"]))
        if not source:
            source = QualificationSource(url=src["source_url"], source_name=src["source_name"],
                                         retrieved_at=datetime.fromisoformat(src["retrieved_at"].replace("Z", "+00:00")))
            db.add(source)
        source.file_path, source.sha256, source.source_type = src["file"], src["sha256"], src["source_type"]
        db.flush()

        q = db.scalar(select(Qualification).where(Qualification.qualification_code == d["qualification_code"]))
        if not q:
            q = Qualification(qualification_code=d["qualification_code"], trade_id=trade.id, source_id=source.id,
                              title=d["title"], nsqf_level=d["nsqf_level"])
            db.add(q)
        for f in ("title", "ncvet_code", "nsqf_level", "nco_codes", "occupations", "nature", "job_description",
                  "awarding_body", "notional_hours", "entry_requirements", "entry_education_rank",
                  "entry_requires_science_maths", "min_age_training", "progression", "rpl_available", "rpl_notes",
                  "rpl_eligibility", "assessment_scheme", "formative_dimensions", "approval_note", "review_note",
                  "not_in_source"):
            setattr(q, f, d.get(f))
        q.data_origin = "official"
        q.trade_id, q.source_id = trade.id, source.id
        db.flush()

        existing = {(c.category, c.lo_number): c for c in q.competencies}
        for i, c in enumerate(d["competencies"]):
            row = existing.get((c["category"], c["lo_number"]))
            if not row:
                row = QualificationCompetency(qualification_id=q.id, category=c["category"], lo_number=c["lo_number"])
                db.add(row)
                q.competencies.append(row)
            row.sort_order = i
            row.year, row.title = c["year"], c["title"]
            row.assessment_criteria = c["assessment_criteria"]
            row.nos_codes_summary, row.nos_codes_lo_table = c["nos_codes_summary"], c["nos_codes_lo_table"]
            row.nos_mismatch = c["nos_mismatch"]
            row.skill_hours, row.knowledge_hours, row.nsqf_level = c["skill_hours"], c["knowledge_hours"], c["nsqf_level"]
            row.data_origin = "official"

        nos_map: dict[str, set[int]] = {}
        for c in d["competencies"]:
            for code in set(c["nos_codes_summary"]) | set(c["nos_codes_lo_table"]):
                if code.startswith("PSS/"):
                    nos_map.setdefault(code, set()).add(c["lo_number"])
        have = {n.nos_code: n for n in q.nos}
        for code, los in sorted(nos_map.items()):
            n = have.get(code) or QualificationNos(qualification_id=q.id, nos_code=code)
            n.mapped_lo_numbers = sorted(los)
            if code not in have:
                q.nos.append(n)
        out.append(q)
    db.flush()
    return out


def load_task_banks(db: Session) -> int:
    count = 0
    for path in sorted((DATA_DIR / "assessment").glob("*_tasks.json")):
        d = _load(path)
        trade = db.scalar(select(Trade).where(Trade.code == d["trade_code"]))
        if not trade:
            raise RuntimeError(f"Task bank {path.name} references unknown trade {d['trade_code']}")
        for i, t in enumerate(d["tasks"]):
            task = db.scalar(select(AssessmentTask).where(AssessmentTask.trade_id == trade.id, AssessmentTask.task_code == t["task_id"]))
            if not task:
                task = AssessmentTask(trade_id=trade.id, task_code=t["task_id"])
                db.add(task)
            task.title, task.title_hi = t["title"], t.get("title_hi")
            task.description, task.description_hi = t["description"], t.get("description_hi")
            task.competency_key, task.lo_numbers, task.weight = t["competency_id"], t["lo_numbers"], t["weight"]
            task.steps, task.evidence_required = t["steps"], t["evidence_required"]
            task.safety_requirements, task.scoring_scale = t["safety_requirements"], d["scoring_scale"]
            task.source_ref, task.sort_order = t["source_ref"], i
            db.flush()
            have = {c.criterion_code: c for c in task.criteria}
            for c in t["criteria"]:
                row = have.get(c["criterion_id"]) or AssessmentCriterion(task_id=task.id, criterion_code=c["criterion_id"])
                row.text, row.weight = c["text"], c["weight"]
                row.is_safety_critical, row.qf_dimension = c["is_safety_critical"], c["qf_dimension"]
                row.qf_criterion_ref, row.anchors, row.evidence_hint = c["qf_criterion_ref"], c["anchors"], c.get("evidence_hint")
                if c["criterion_id"] not in have:
                    task.criteria.append(row)
            count += 1
    db.flush()
    return count
