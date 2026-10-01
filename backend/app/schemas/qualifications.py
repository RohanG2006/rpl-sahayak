from pydantic import BaseModel, ConfigDict


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_name: str
    url: str
    sha256: str | None
    retrieved_at: str | None = None
    source_type: str


class CompetencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category: str
    lo_number: int
    year: int | None
    title: str
    assessment_criteria: list[str]
    nos_codes_summary: list[str]
    nos_codes_lo_table: list[str]
    nos_mismatch: bool
    skill_hours: int | None
    knowledge_hours: int | None
    nsqf_level: float | None


class QualificationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    qualification_code: str
    ncvet_code: str | None
    nsqf_level: float
    occupations: list
    trade_code: str
    is_assessable: bool
    data_origin: str
    source_url: str


class QualificationDetail(QualificationSummary):
    nco_codes: list
    nature: str | None
    job_description: str | None
    awarding_body: str | None
    notional_hours: dict
    entry_requirements: str | None
    min_age_training: int | None
    progression: dict
    rpl_available: bool | None
    rpl_notes: str | None
    rpl_eligibility: dict
    assessment_scheme: dict
    formative_dimensions: list
    approval_note: str | None
    review_note: str | None
    not_in_source: list
    source: SourceOut
    competencies: list[CompetencyOut]
    nos: list[dict]


class CriterionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    criterion_code: str
    text: str
    weight: float
    is_safety_critical: bool
    qf_dimension: str
    qf_criterion_ref: str | None
    anchors: dict
    evidence_hint: str | None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_code: str
    title: str
    title_hi: str | None
    description: str
    description_hi: str | None
    competency_key: str
    lo_numbers: list[int]
    weight: float
    steps: list[dict]
    evidence_required: list[dict]
    safety_requirements: list[str]
    scoring_scale: dict
    source_ref: dict
    criteria: list[CriterionOut]
