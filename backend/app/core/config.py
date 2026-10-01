"""Application settings. All secrets come from environment variables / .env (never the frontend)."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
PROMPTS_DIR = REPO_ROOT / "prompts"


class MatchWeights(BaseSettings):
    """Qualification-mapping weights (spec §10). Override with MATCH_W_SKILL etc."""

    model_config = SettingsConfigDict(env_prefix="MATCH_W_", env_file=".env", extra="ignore")

    skill: float = 0.40
    task: float = 0.25
    experience: float = 0.15
    occupation: float = 0.10
    eligibility: float = 0.10

    def as_dict(self) -> dict[str, float]:
        return {
            "skill": self.skill,
            "task": self.task,
            "experience": self.experience,
            "occupation": self.occupation,
            "eligibility": self.eligibility,
        }


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RPL-Sahayak AI"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://rpl:rpl@localhost:5433/rpl_sahayak"

    jwt_secret: str = Field(default="dev-only-change-me-please-32-bytes-min", min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 8 * 60

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # AI
    ai_provider: str = "mock"  # mock | gemini | openai
    ai_send_evidence: bool = False
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: float = 30.0

    # Uploads
    storage_dir: Path = REPO_ROOT / "backend" / "storage"
    max_upload_mb: int = 15
    allowed_upload_mime: list[str] = [
        "image/jpeg", "image/png", "image/webp",
        "video/mp4", "video/webm",
        "application/pdf",
        "audio/mpeg", "audio/webm", "audio/wav",
    ]

    # Assessment thresholds (see docs/methodology.md for sources)
    competency_required_pct: float = 60.0  # QF DGT/1001 §23: practical pass 60 %
    lo_coverage_required: float = 0.70  # NCVET RPL Guidelines §6.2(c): > 70 % of LOs
    rpl_min_age: int = 21  # QF DGT/1001 §22 Category IV
    rpl_min_years: float = 3.0  # QF DGT/1001 §22 Category IV

    demo_mode_enabled: bool = True
    rate_limit_login: str = "10/minute"
    rate_limit_ai: str = "30/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_match_weights() -> MatchWeights:
    return MatchWeights()
