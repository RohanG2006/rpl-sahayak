from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFound
from app.models import AssessmentTask, Qualification, Trade


def list_qualifications(db: Session) -> list[Qualification]:
    return list(db.scalars(select(Qualification).order_by(Qualification.title)))


def get_qualification(db: Session, qid_or_code: str) -> Qualification:
    stmt = select(Qualification).options(selectinload(Qualification.competencies), selectinload(Qualification.nos))
    q = db.scalar(stmt.where((Qualification.id == qid_or_code) | (Qualification.qualification_code == qid_or_code)))
    if not q:
        raise NotFound("Qualification not found.", code="qualification_unavailable")
    return q


def tasks_for_trade(db: Session, trade_id: str) -> list[AssessmentTask]:
    return list(db.scalars(
        select(AssessmentTask).where(AssessmentTask.trade_id == trade_id, AssessmentTask.is_active.is_(True))
        .order_by(AssessmentTask.sort_order)
    ))


def assessable_trades(db: Session) -> list[Trade]:
    return list(db.scalars(select(Trade).where(Trade.is_assessable.is_(True))))
