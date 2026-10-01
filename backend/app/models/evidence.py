from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, JsonType, OriginMixin, TimestampMixin


class Evidence(IdMixin, TimestampMixin, OriginMixin, Base):
    __tablename__ = "evidence"
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("assessment_plans.id", ondelete="CASCADE"), nullable=True, index=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("worker_profiles.id", ondelete="CASCADE"), index=True)
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("assessment_attempts.id"), nullable=True)
    criterion_id: Mapped[str | None] = mapped_column(ForeignKey("assessment_criteria.id"), nullable=True, index=True)
    purpose: Mapped[str] = mapped_column(String(20), default="assessment")  # assessment | document
    doc_type: Mapped[str | None] = mapped_column(String(30), nullable=True)  # resume | experience_letter | certificate | id_placeholder
    kind: Mapped[str] = mapped_column(String(10))  # image | video | document | audio
    mime: Mapped[str] = mapped_column(String(60))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    original_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_offline: Mapped[bool] = mapped_column(Boolean, default=False)
    upload_status: Mapped[str] = mapped_column(String(16), default="uploaded")  # pending | uploaded | failed
    client_op_id: Mapped[str | None] = mapped_column(String(36), nullable=True, unique=True)
    extracted_claims: Mapped[list] = mapped_column(JsonType, default=list)
    claims_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)


class AIObservation(IdMixin, TimestampMixin, OriginMixin, Base):
    """Immutable record of every AI call result. Advisory only."""

    __tablename__ = "ai_observations"
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("assessment_plans.id", ondelete="CASCADE"), nullable=True, index=True)
    worker_id: Mapped[str | None] = mapped_column(ForeignKey("worker_profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(30))
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    prompt_file: Mapped[str | None] = mapped_column(String(60), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    output: Mapped[dict] = mapped_column(JsonType, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    valid: Mapped[bool] = mapped_column(Boolean, default=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
