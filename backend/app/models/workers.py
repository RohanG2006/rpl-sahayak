from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, JsonType, OriginMixin, TimestampMixin

# Education ladder used for eligibility checks (rank compared with qualification entry rank)
EDUCATION_RANKS = {
    "none": 0,
    "below_5": 1,
    "5th": 2,
    "8th": 3,
    "10th": 4,
    "12th": 5,
    "iti": 5,
    "diploma": 6,
    "graduate": 7,
}


class WorkerProfile(IdMixin, TimestampMixin, OriginMixin, Base):
    __tablename__ = "worker_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    mobile: Mapped[str | None] = mapped_column(String(15), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    state: Mapped[str | None] = mapped_column(String(60), nullable=True)
    district: Mapped[str | None] = mapped_column(String(60), nullable=True)
    locality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    occupation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    years_experience: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_employer: Mapped[str | None] = mapped_column(String(150), nullable=True)
    previous_employers: Mapped[list] = mapped_column(JsonType, default=list)
    informal_training: Mapped[str | None] = mapped_column(Text, nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    has_science_maths: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    existing_certificates: Mapped[list] = mapped_column(JsonType, default=list)
    tools: Mapped[list] = mapped_column(JsonType, default=list)
    typical_work: Mapped[str | None] = mapped_column(Text, nullable=True)
    archetype: Mapped[str | None] = mapped_column(String(40), nullable=True)  # synthetic data only
    status: Mapped[str] = mapped_column(String(30), default="REGISTERED", index=True)

    experiences: Mapped[list["WorkerExperience"]] = relationship(
        order_by="WorkerExperience.version", cascade="all, delete-orphan"
    )
    skills: Mapped[list["WorkerSkill"]] = relationship(cascade="all, delete-orphan")


class WorkerExperience(IdMixin, TimestampMixin, OriginMixin, Base):
    """Declarations are append-only: an edit creates a new version, the original stays intact."""

    __tablename__ = "worker_experiences"
    __table_args__ = (UniqueConstraint("worker_id", "version"),)
    worker_id: Mapped[str] = mapped_column(ForeignKey("worker_profiles.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    raw_text: Mapped[str] = mapped_column(Text)
    input_mode: Mapped[str] = mapped_column(String(10), default="text")  # text | voice
    language: Mapped[str] = mapped_column(String(8), default="en")


class WorkerSkill(IdMixin, TimestampMixin, OriginMixin, Base):
    __tablename__ = "worker_skills"
    worker_id: Mapped[str] = mapped_column(ForeignKey("worker_profiles.id", ondelete="CASCADE"), index=True)
    experience_id: Mapped[str | None] = mapped_column(ForeignKey("worker_experiences.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(16))  # skill | tool | task | equipment | safety | learning_mode
    label: Mapped[str] = mapped_column(String(150))
    normalized_label: Mapped[str | None] = mapped_column(String(150), nullable=True)
    source: Mapped[str] = mapped_column(String(10))  # ai | worker | assessor
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
