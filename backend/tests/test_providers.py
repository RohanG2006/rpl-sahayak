"""Real-provider adapters tested against stand-in SDK modules (no network, no keys): request shape + error mapping."""
import json
import sys
import types

import pytest

from app.ai.providers.base import ImageInput, ProviderError

GOOD = {"occupation": "Electrician", "experience_years": 5, "skills": [], "confidence": 0.8, "missing_information": []}


def fake_openai(monkeypatch, behaviour):
    calls = {}

    class Completions:
        def create(self, **kw):
            calls.update(kw)
            if behaviour == "raise":
                raise RuntimeError("quota")
            msg = types.SimpleNamespace(content=json.dumps(GOOD))
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    class OpenAI:
        def __init__(self, api_key, timeout):
            calls["init"] = {"api_key": api_key, "timeout": timeout}
            self.chat = types.SimpleNamespace(completions=Completions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=OpenAI))
    return calls


def test_openai_request_shape_json_mode_and_image(monkeypatch):
    calls = fake_openai(monkeypatch, "ok")
    from app.ai.providers.openai import OpenAIProvider
    p = OpenAIProvider("sk-test", "gpt-test", 12)
    out = p.complete_json("SYS", "USER", {}, [ImageInput("image/png", b"\x89PNG")])
    assert json.loads(out)["occupation"] == "Electrician"
    assert calls["response_format"] == {"type": "json_object"} and calls["model"] == "gpt-test"
    user = calls["messages"][1]["content"]
    assert user[0] == {"type": "text", "text": "USER"} and user[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert calls["messages"][0] == {"role": "system", "content": "SYS"}


def test_openai_errors_become_provider_error(monkeypatch):
    fake_openai(monkeypatch, "raise")
    from app.ai.providers.openai import OpenAIProvider
    with pytest.raises(ProviderError):
        OpenAIProvider("sk-test", "m", 5).complete_json("s", "u", {})


def test_missing_keys_rejected():
    from app.ai.providers.gemini import GeminiProvider
    from app.ai.providers.openai import OpenAIProvider
    with pytest.raises(ProviderError):
        OpenAIProvider("", "m", 5)
    with pytest.raises(ProviderError):
        GeminiProvider("", "m", 5)


def fake_gemini(monkeypatch, behaviour):
    calls = {}

    class Part:
        @staticmethod
        def from_text(text):
            return ("text", text)

        @staticmethod
        def from_bytes(data, mime_type):
            return ("bytes", mime_type, len(data))

    gtypes = types.SimpleNamespace(
        Part=Part, Content=lambda role, parts: {"role": role, "parts": parts},
        GenerateContentConfig=lambda **kw: kw,
    )

    class Models:
        def generate_content(self, model, contents, config):
            calls.update(model=model, contents=contents, config=config)
            if behaviour == "raise":
                raise RuntimeError("503")
            return types.SimpleNamespace(text=json.dumps(GOOD))

    class Client:
        def __init__(self, api_key, http_options):
            calls["timeout_ms"] = http_options["timeout"]
            self.models = Models()

    genai = types.SimpleNamespace(Client=Client, types=gtypes)
    google = types.ModuleType("google")
    google.genai = genai
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    return calls


def test_gemini_request_shape_json_mime_and_media(monkeypatch):
    calls = fake_gemini(monkeypatch, "ok")
    from app.ai.providers.gemini import GeminiProvider
    out = GeminiProvider("g-test", "gemini-test", 7).complete_json("SYS", "USER", {}, [ImageInput("video/mp4", b"0000")])
    assert json.loads(out)["experience_years"] == 5
    assert calls["config"]["response_mime_type"] == "application/json" and calls["config"]["system_instruction"] == "SYS"
    assert calls["contents"][0]["parts"] == [("text", "USER"), ("bytes", "video/mp4", 4)] and calls["timeout_ms"] == 7000


def test_gemini_errors_become_provider_error(monkeypatch):
    fake_gemini(monkeypatch, "raise")
    from app.ai.providers.gemini import GeminiProvider
    with pytest.raises(ProviderError):
        GeminiProvider("g", "m", 5).complete_json("s", "u", {})


def test_service_uses_configured_provider_end_to_end(monkeypatch):
    """AI_PROVIDER=openai with a key → AIService routes through the adapter and validates the JSON."""
    fake_openai(monkeypatch, "ok")
    from app.ai.service import AIService
    from app.core.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "ai_provider", "openai")
    monkeypatch.setattr(s, "openai_api_key", "sk-test")
    res = AIService().extract_worker_skills("I am an electrician for 5 years.")
    assert res.provider == "openai" and not res.fallback_used and res.data.experience_years == 5
