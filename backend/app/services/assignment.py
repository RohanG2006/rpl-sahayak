"""Assessor allocation (prototype rule: least open plans among active assessors; ties by assessor code)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AssessmentPlan, User

CLOSED = ("DECIDED", "REPORT_ISSUED")


def pick_assessor(db: Session) -> User | None:
    load = (select(AssessmentPlan.assessor_id, func.count().label("n"))
            .where(AssessmentPlan.status.not_in(CLOSED)).group_by(AssessmentPlan.assessor_id).subquery())
    stmt = (select(User).outerjoin(load, load.c.assessor_id == User.id)
            .where(User.role_code == "assessor", User.is_active.is_(True))
            .order_by(func.coalesce(load.c.n, 0), User.assessor_code))
    return db.scalars(stmt).first()
