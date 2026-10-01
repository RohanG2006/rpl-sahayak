from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Qualification, User
from app.repositories import qualifications as repo
from app.schemas.qualifications import CompetencyOut, QualificationDetail, QualificationSummary, SourceOut, TaskOut

router = APIRouter(tags=["qualifications"])


def _summary(q: Qualification) -> dict:
    return dict(
        id=q.id, title=q.title, qualification_code=q.qualification_code, ncvet_code=q.ncvet_code,
        nsqf_level=q.nsqf_level, occupations=q.occupations, trade_code=q.trade.code,
        is_assessable=q.trade.is_assessable, data_origin=q.data_origin, source_url=q.source.url,
    )


@router.get("/qualifications", response_model=list[QualificationSummary])
def list_qualifications(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Official qualification records (NQR). `data_origin` is always `official`."""
    return [_summary(q) for q in repo.list_qualifications(db)]


@router.get("/qualifications/{qualification_id:path}/tasks", response_model=list[TaskOut])
def get_tasks(qualification_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Prototype practical-task bank for the qualification's trade (project-authored, derived from official LOs)."""
    q = repo.get_qualification(db, qualification_id)
    return [TaskOut.model_validate(t) for t in repo.tasks_for_trade(db, q.trade_id)]


@router.get("/qualifications/{qualification_id:path}", response_model=QualificationDetail)
def get_qualification(qualification_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Accepts the internal id or the official code (e.g. `DGT/1001` URL-encoded as `DGT%2F1001`)."""
    q = repo.get_qualification(db, qualification_id)
    return QualificationDetail(
        **_summary(q),
        nco_codes=q.nco_codes, nature=q.nature, job_description=q.job_description, awarding_body=q.awarding_body,
        notional_hours=q.notional_hours, entry_requirements=q.entry_requirements, min_age_training=q.min_age_training,
        progression=q.progression, rpl_available=q.rpl_available, rpl_notes=q.rpl_notes,
        rpl_eligibility=q.rpl_eligibility, assessment_scheme=q.assessment_scheme,
        formative_dimensions=q.formative_dimensions, approval_note=q.approval_note, review_note=q.review_note,
        not_in_source=q.not_in_source,
        source=SourceOut(source_name=q.source.source_name, url=q.source.url, sha256=q.source.sha256,
                         retrieved_at=q.source.retrieved_at.isoformat(), source_type=q.source.source_type),
        competencies=[CompetencyOut.model_validate(c) for c in q.competencies],
        nos=[{"nos_code": n.nos_code, "lo_numbers": n.mapped_lo_numbers} for n in sorted(q.nos, key=lambda n: n.nos_code)],
    )


