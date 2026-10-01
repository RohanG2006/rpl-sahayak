"""AI layer: deterministic tests with stub providers — no network, no API keys (spec §45)."""
import json

import pytest

from app.ai.providers.base import ProviderError
from app.ai.service import AIService
from app.core.errors import AIUnavailable

TEXT = "Main 4 saal se bijli mistri ka kaam karta hoon. Ghar ki wiring, pankha lagana, MCB lagana aur fault dhundna. Tester aur plas use karta hoon."

GOOD = {
    "occupation": "Electrician", "experience_years": 4,
    "skills": [{"label": "House wiring installation", "source_text": "Ghar ki wiring", "confidence": 0.9}],
    "confidence": 0.8, "missing_information": [],
}


class Stub:
    name, model = "stub", "stub-1"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def complete_json(self, system, user, json_schema, images=None):
        self.calls += 1
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def test_valid_llm_output_is_used():
    res = AIService(Stub([json.dumps(GOOD)])).extract_worker_skills(TEXT)
    assert res.provider == "stub" and not res.fallback_used and res.attempts == 1
    assert res.data.skills[0].label == "House wiring installation"


def test_fenced_json_is_accepted():
    res = AIService(Stub(["```json\n" + json.dumps(GOOD) + "\n```"])).extract_worker_skills(TEXT)
    assert res.provider == "stub"


def test_malformed_then_valid_retries_once():
    stub = Stub(["not json at all", json.dumps(GOOD)])
    res = AIService(stub).extract_worker_skills(TEXT)
    assert stub.calls == 2 and res.attempts == 2 and not res.fallback_used


def test_twice_malformed_falls_back_to_rules():
    bad_schema = json.dumps({"skills": [{"label": "x", "confidence": 7}], "confidence": 2})
    stub = Stub(["{oops", bad_schema])
    res = AIService(stub).extract_worker_skills(TEXT)
    assert res.fallback_used and res.provider == "rules" and "invalid output" in res.error
    assert any(s.label == "MCB / circuit breaker installation" for s in res.data.skills)


def test_provider_down_falls_back_without_retry():
    stub = Stub([ProviderError("timeout")])
    res = AIService(stub).extract_worker_skills(TEXT)
    assert stub.calls == 1 and res.fallback_used


def test_no_rule_fallback_raises_safe_error():
    svc = AIService(Stub(["{bad", "{bad"]))
    from app.ai.schemas import NarrativeOut
    with pytest.raises(AIUnavailable):
        svc._run("x", "skill_extraction", {}, NarrativeOut, None)


def test_misconfigured_provider_runs_on_rules(monkeypatch):
    from app.core.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "ai_provider", "gemini")
    monkeypatch.setattr(s, "gemini_api_key", None)
    res = AIService().extract_worker_skills(TEXT)
    assert res.provider == "rules" and "GEMINI_API_KEY" in (res.error or "")


def test_rules_extraction_hinglish():
    d = AIService(use_settings=False).extract_worker_skills(TEXT).data
    assert d.experience_years == 4 and d.occupation == "Electrician"
    assert {"Line tester", "Combination plier"} <= {t.label for t in d.tools}
    assert "No safety practices described (e.g. switching off supply, gloves, tester)" in d.missing_information
