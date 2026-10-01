from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, JsonType, OriginMixin, utcnow


class SyncQueue(IdMixin, Base):
    """Server-side log of client offline operations; client_op_id makes /sync idempotent."""

    __tablename__ = "sync_queue"
    client_id: Mapped[str] = mapped_column(String(64), index=True)
    client_op_id: Mapped[str] = mapped_column(String(36), unique=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    entity: Mapped[str] = mapped_column(String(40))
    op: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JsonType, default=dict)
    client_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="received")  # applied | conflict | rejected | failed
    result: Mapped[dict] = mapped_column(JsonType, default=dict)


class AuditLog(IdMixin, Base):
    """Append-only. 'before'/'after' are PII-redacted by services.audit."""

    __tablename__ = "audit_logs"
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(16), nullable=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    before: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    after: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    via: Mapped[str] = mapped_column(String(10), default="online")  # online | sync | system | demo


class ConsistencyRating(IdMixin, OriginMixin, Base):
    """SIMULATION/TEST DATA only — see docs/dataset.md §4."""

    __tablename__ = "consistency_ratings"
    case_id: Mapped[str] = mapped_column(String(10), index=True)
    task_code: Mapped[str] = mapped_column(String(10))
    criterion_code: Mapped[str] = mapped_column(String(10))
    assessor_id: Mapped[str] = mapped_column(String(10))
    mode: Mapped[str] = mapped_column(String(14), index=True)  # baseline | standardised
    score: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
