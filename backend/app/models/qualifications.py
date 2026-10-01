"""Official qualification data (data_origin='official'). Never hand-edited with invented values."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, JsonType, OriginMixin, TimestampMixin


class Trade(IdMixin, TimestampMixin, Base):
    __tablename__ = "trades"
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    is_assessable: Mapped[bool] = mapped_column(Boolean, default=False)  # has task bank + rubric
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class QualificationSource(IdMixin, TimestampMixin, Base):
    __tablename__ = "qualification_sources"
    source_name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(400))
    file_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_type: Mapped[str] = mapped_column(String(20), default="official")
    version_note: Mapped[str | None] = mapped_column(String(300), nullable=True)


class Qualification(IdMixin, TimestampMixin, OriginMixin, Base):
    __tablename__ = "qualifications"
    trade_id: Mapped[str] = mapped_column(ForeignKey("trades.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("qualification_sources.id"))
    title: Mapped[str] = mapped_column(String(200))
    qualification_code: Mapped[str] = mapped_column(String(40), unique=True)
    ncvet_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    nsqf_level: Mapped[float] = mapped_column(Float)
    nco_codes: Mapped[list] = mapped_column(JsonType, default=list)
    occupations: Mapped[list] = mapped_column(JsonType, default=list)
    nature: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    awarding_body: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notional_hours: Mapped[dict] = mapped_column(JsonType, default=dict)
    entry_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_education_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entry_requires_science_maths: Mapped[bool] = mapped_column(Boolean, default=False)
    min_age_training: Mapped[int | None] = mapped_column(Integer, nullable=True)
    progression: Mapped[dict] = mapped_column(JsonType, default=dict)
    rpl_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rpl_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rpl_eligibility: Mapped[dict] = mapped_column(JsonType, default=dict)
    assessment_scheme: Mapped[dict] = mapped_column(JsonType, default=dict)
    formative_dimensions: Mapped[list] = mapped_column(JsonType, default=list)
    approval_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    not_in_source: Mapped[list] = mapped_column(JsonType, default=list)

    trade: Mapped[Trade] = relationship(lazy="joined")
    source: Mapped[QualificationSource] = relationship(lazy="joined")
    competencies: Mapped[list["QualificationCompetency"]] = relationship(
        back_populates="qualification", order_by="QualificationCompetency.sort_order", cascade="all, delete-orphan"
    )
    nos: Mapped[list["QualificationNos"]] = relationship(cascade="all, delete-orphan")


class QualificationNos(IdMixin, Base):
    __tablename__ = "qualification_nos"
    __table_args__ = (UniqueConstraint("qualification_id", "nos_code"),)
    qualification_id: Mapped[str] = mapped_column(ForeignKey("qualifications.id", ondelete="CASCADE"), index=True)
    nos_code: Mapped[str] = mapped_column(String(30))
    mapped_lo_numbers: Mapped[list] = mapped_column(JsonType, default=list)


class QualificationCompetency(IdMixin, OriginMixin, Base):
    """One row per Learning Outcome (LO) from the QF."""

    __tablename__ = "qualification_competencies"
    __table_args__ = (UniqueConstraint("qualification_id", "category", "lo_number"),)
    qualification_id: Mapped[str] = mapped_column(ForeignKey("qualifications.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(20))  # trade | employability
    lo_number: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(Text)
    assessment_criteria: Mapped[list] = mapped_column(JsonType, default=list)
    nos_codes_summary: Mapped[list] = mapped_column(JsonType, default=list)
    nos_codes_lo_table: Mapped[list] = mapped_column(JsonType, default=list)
    nos_mismatch: Mapped[bool] = mapped_column(Boolean, default=False)
    skill_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    knowledge_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nsqf_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Derived for matching; labelled project-authored (see docs/dataset.md §2)
    keywords: Mapped[list] = mapped_column(JsonType, default=list)
    short_label: Mapped[str | None] = mapped_column(String(60), nullable=True)

    qualification: Mapped[Qualification] = relationship(back_populates="competencies")
