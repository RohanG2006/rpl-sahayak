"""Pydantic contracts for every AI output. Anything that fails validation is never shown as AI output."""
from pydantic import BaseModel, Field, field_validator


class ExtractedItem(BaseModel):
    label: str = Field(min_length=1, max_length=150)
    source_text: str | None = Field(default=None, max_length=400, description="Worker's own words that support this item")
    confidence: float = Field(ge=0, le=1)


class SkillExtraction(BaseModel):
    occupation: str | None = None
    experience_years: float | None = Field(default=None, ge=0, le=60)
    skills: list[ExtractedItem] = []
    tools: list[ExtractedItem] = []
    tasks: list[ExtractedItem] = []
    equipment: list[ExtractedItem] = []
    safety_practices: list[ExtractedItem] = []
    learning_mode: list[ExtractedItem] = []
    experience_evidence: list[str] = []
    confidence: float = Field(ge=0, le=1)
    missing_information: list[str] = []

    @field_validator("skills", "tools", "tasks", "equipment", "safety_practices", "learning_mode")
    @classmethod
    def _dedupe(cls, v: list[ExtractedItem]) -> list[ExtractedItem]:
        seen, out = set(), []
        for i in v:
            k = i.label.strip().lower()
            if k not in seen:
                seen.add(k)
                out.append(i)
        return out


class EvidenceObservation(BaseModel):
    observed: list[str] = []
    potentially_missing: list[str] = []
    safety_concerns: list[str] = []
    competency_indicators: list[str] = []
    suggested_score: int | None = Field(default=None, ge=0, le=4)
    suggested_score_reason: str | None = None
    confidence: float = Field(ge=0, le=1)
    analysis_basis: str = Field(description="image | metadata_only")


class DocumentClaims(BaseModel):
    doc_type: str
    claims: list[ExtractedItem] = []
    confidence: float = Field(ge=0, le=1)


class NarrativeOut(BaseModel):
    summary: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)
