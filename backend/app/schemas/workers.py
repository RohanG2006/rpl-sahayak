import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.workers import EDUCATION_RANKS

Language = Literal["en", "hi"]
Gender = Literal["female", "male", "other", "prefer_not"]
EducationLevel = Literal[tuple(EDUCATION_RANKS)]  # type: ignore[valid-type]


class ProfileFields(BaseModel):
    full_name: str = Field(min_length=2, max_length=120, examples=["Raj Kumar"])
    mobile: str | None = Field(default=None, examples=["9000012345"])
    age: int | None = Field(default=None, ge=14, le=80)
    gender: Gender | None = None
    state: str | None = Field(default=None, max_length=60)
    district: str | None = Field(default=None, max_length=60)
    locality: str | None = Field(default=None, max_length=100)
    preferred_language: Language = "en"
    occupation: str | None = Field(default=None, max_length=100)
    years_experience: float | None = Field(default=None, ge=0, le=60)
    current_employer: str | None = Field(default=None, max_length=150)
    previous_employers: list[str] = Field(default=[], max_length=10)
    informal_training: str | None = Field(default=None, max_length=1000)
    education_level: EducationLevel | None = None
    has_science_maths: bool | None = None
    existing_certificates: list[str] = Field(default=[], max_length=10)
    tools: list[str] = Field(default=[], max_length=30)
    typical_work: str | None = Field(default=None, max_length=2000)

    @field_validator("mobile")
    @classmethod
    def _mobile(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        digits = re.sub(r"\D", "", v)[-10:]
        if not re.fullmatch(r"[6-9]\d{9}", digits):
            raise ValueError("Enter a 10-digit Indian mobile number")
        return digits


class WorkerCreate(ProfileFields):
    pin: str | None = Field(default=None, min_length=4, max_length=12, description="Worker sign-in PIN (self-registration)")


class WorkerUpdate(ProfileFields):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)  # type: ignore[assignment]


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    kind: str
    label: str
    normalized_label: str | None
    source: str
    confirmed: bool
    confidence: float | None


class ExperienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    version: int
    raw_text: str
    input_mode: str
    language: str


class WorkerOut(ProfileFields):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    status: str
    ncvet_stage: str = ""
    data_origin: str
    archetype: str | None = None
    experiences: list[ExperienceOut] = []
    skills: list[SkillOut] = []
    mobile: str | None = None  # masked for non-owners


class ExperienceIn(BaseModel):
    raw_text: str = Field(min_length=10, max_length=4000)
    input_mode: Literal["text", "voice"] = "text"
    language: Language = "en"


class SkillIn(BaseModel):
    kind: Literal["skill", "tool", "task", "equipment", "safety", "learning_mode"]
    label: str = Field(min_length=1, max_length=150)
    source: Literal["ai", "worker", "assessor"] = "worker"
    confidence: float | None = Field(default=None, ge=0, le=1)


class SkillsConfirmIn(BaseModel):
    """The full, worker-approved list. Replaces previous confirmed list; AI suggestions are never auto-applied."""
    skills: list[SkillIn] = Field(max_length=120)
    occupation: str | None = Field(default=None, max_length=100)
    years_experience: float | None = Field(default=None, ge=0, le=60)
    ai_observation_id: str | None = None
