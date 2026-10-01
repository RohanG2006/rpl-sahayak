from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, JsonType, OriginMixin, TimestampMixin


class AssessmentTask(IdMixin, TimestampMixin, Base):
    """Project-authored task bank row, derived from official LOs (see data/assessment)."""

    __tablename__ = "assessment_tasks"
    __table_args__ = (UniqueConstraint("trade_id", "task_code"),)
    trade_id: Mapped[str] = mapped_column(ForeignKey("trades.id"), index=True)
    task_code: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(200))
    title_hi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    description_hi: Mapped[str | None] = mapped_column(Text, nullable=True)
    competency_key: Mapped[str] = mapped_column(String(40))
    lo_numbers: Mapped[list] = mapped_column(JsonType, default=list)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    steps: Mapped[list] = mapped_column(JsonType, default=list)
    evidence_required: Mapped[list] = mapped_column(JsonType, default=list)
    safety_requirements: Mapped[list] = mapped_column(JsonType, default=list)
    scoring_scale: Mapped[dict] = mapped_column(JsonType, default=dict)
    source_ref: Mapped[dict] = mapped_column(JsonType, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    criteria: Mapped[list["AssessmentCriterion"]] = relationship(
        order_by="AssessmentCriterion.criterion_code", cascade="all, delete-orphan", lazy="selectin"
    )


class AssessmentCriterion(IdMixin, Base):
    __tablename__ = "assessment_criteria"
    task_id: Mapped[str] = mapped_column(ForeignKey("assessment_tasks.id", ondelete="CASCADE"), index=True)
    criterion_code: Mapped[str] = mapped_column(String(10), unique=True)
    text: Mapped[str] = mapped_column(Text)
    text_hi: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    qf_dimension: Mapped[str] = mapped_column(String(60))
    qf_criterion_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    anchors: Mapped[dict] = mapped_column(JsonType, default=dict)
    evidence_hint: Mapped[str | None] = mapped_column(Text, nullable=True)


class AssessmentPlan(IdMixin, TimestampMixin, OriginMixin, Base):
    """'Assessment' in the API. Carries the workflow state machine."""

    __tablename__ = "assessment_plans"
    worker_id: Mapped[str] = mapped_column(ForeignKey("worker_profiles.id", ondelete="CASCADE"), index=True)
    qualification_id: Mapped[str] = mapped_column(ForeignKey("qualifications.id"), index=True)
    assessor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="PLAN_CREATED", index=True)
    pathway: Mapped[str | None] = mapped_column(String(32), nullable=True)
    match_snapshot: Mapped[dict] = mapped_column(JsonType, default=dict)
    self_assessment: Mapped[dict] = mapped_column(JsonType, default=dict)
    readiness_snapshot: Mapped[dict] = mapped_column(JsonType, default=dict)
    task_codes: Mapped[list] = mapped_column(JsonType, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    attempts: Mapped[list["AssessmentAttempt"]] = relationship(cascade="all, delete-orphan")


class AssessmentAttempt(IdMixin, TimestampMixin, OriginMixin, Base):
    __tablename__ = "assessment_attempts"
    __table_args__ = (UniqueConstraint("plan_id", "task_id"),)
    plan_id: Mapped[str] = mapped_column(ForeignKey("assessment_plans.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("assessment_tasks.id"))
    status: Mapped[str] = mapped_column(String(20), default="NOT_STARTED")  # NOT_STARTED|IN_PROGRESS|SUBMITTED|SCORED
    checklist_state: Mapped[dict] = mapped_column(JsonType, default=dict)
    worker_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_op_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AssessorScore(IdMixin, TimestampMixin, OriginMixin, Base):
    """AI suggestion and human final score live in separate columns. Only final_score is used for results."""

    __tablename__ = "assessor_scores"
    __table_args__ = (UniqueConstraint("plan_id", "criterion_id"),)
    plan_id: Mapped[str] = mapped_column(ForeignKey("assessment_plans.id", ondelete="CASCADE"), index=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("assessment_attempts.id", ondelete="CASCADE"))
    criterion_id: Mapped[str] = mapped_column(ForeignKey("assessment_criteria.id"))
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    ai_suggested_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_observation_id: Mapped[str | None] = mapped_column(ForeignKey("ai_observations.id"), nullable=True)
    final_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assessor_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_ids: Mapped[list] = mapped_column(JsonType, default=list)
    confirmed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    overrode_ai: Mapped[bool] = mapped_column(Boolean, default=False)


class CompetencyResult(IdMixin, TimestampMixin, Base):
    __tablename__ = "competency_results"
    plan_id: Mapped[str] = mapped_column(ForeignKey("assessment_plans.id", ondelete="CASCADE"), index=True)
    group: Mapped[str] = mapped_column(String(20))  # task | lo | dimension | overall
    competency_key: Mapped[str] = mapped_column(String(60))
    label: Mapped[str] = mapped_column(String(200))
    score_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    required_pct: Mapped[float] = mapped_column(Float)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    inputs_hash: Mapped[str] = mapped_column(String(64))


class SkillGap(IdMixin, TimestampMixin, Base):
    __tablename__ = "skill_gaps"
    plan_id: Mapped[str] = mapped_column(ForeignKey("assessment_plans.id", ondelete="CASCADE"), index=True)
    competency_key: Mapped[str] = mapped_column(String(60))
    label: Mapped[str] = mapped_column(String(200))
    required: Mapped[float] = mapped_column(Float)
    demonstrated: Mapped[float | None] = mapped_column(Float, nullable=True)
    gap: Mapped[float] = mapped_column(Float)
    learning_topics: Mapped[list] = mapped_column(JsonType, default=list)


class Recommendation(IdMixin, TimestampMixin, Base):
    __tablename__ = "recommendations"
    plan_id: Mapped[str] = mapped_column(ForeignKey("assessment_plans.id", ondelete="CASCADE"), index=True)
    outcome: Mapped[str] = mapped_column(String(32))  # ELIGIBLE | NOT_YET_READY | REASSESSMENT_SUGGESTED
    competency_coverage: Mapped[float] = mapped_column(Float)
    evidence_coverage: Mapped[float] = mapped_column(Float)
    overall_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    rule_trace: Mapped[list] = mapped_column(JsonType, default=list)
    flags: Mapped[list] = mapped_column(JsonType, default=list)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative_ai_observation_id: Mapped[str | None] = mapped_column(ForeignKey("ai_observations.id"), nullable=True)


class AssessorDecision(IdMixin, TimestampMixin, OriginMixin, Base):
    __tablename__ = "assessor_decisions"
    plan_id: Mapped[str] = mapped_column(ForeignKey("assessment_plans.id", ondelete="CASCADE"), index=True)
    assessor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(16))  # APPROVE | REJECT | REASSESS
    comments: Mapped[str] = mapped_column(Text)
    recommendation_id: Mapped[str | None] = mapped_column(ForeignKey("recommendations.id"), nullable=True)
    agrees_with_recommendation: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reassess_task_codes: Mapped[list] = mapped_column(JsonType, default=list)
