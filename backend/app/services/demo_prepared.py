"""Prepared (pre-computed) AI observations for SYNTHETIC demo evidence only (spec §46: judges must not wait for
API calls). Returned with provider='demo-prepared' so every screen labels them as simulated."""
import json
from functools import lru_cache

from app.ai.schemas import EvidenceObservation
from app.ai.service import AIResult
from app.core.config import DATA_DIR
from app.models import Evidence


@lru_cache
def _index() -> dict:
    p = DATA_DIR / "demo" / "prepared_ai_observations.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get("observations", {})


def prepared_observation(e: Evidence) -> AIResult | None:
    if e.data_origin != "synthetic" or not e.original_name:
        return None
    raw = _index().get(e.original_name)
    if not raw:
        return None
    return AIResult(EvidenceObservation.model_validate(raw), "evidence_analysis", "demo-prepared", None,
                    "evidence_analysis", "prepared", error="Prepared demo output for synthetic evidence (not a live AI call)")
