"""AIService: the only entry point the rest of the app uses for AI.

Contract for every call (spec §33):
  render prompt file -> provider.complete_json -> parse JSON -> Pydantic validate
  -> on failure retry once with a correction message
  -> on second failure use the deterministic rule implementation (fallback_used=True)
  -> if no rule implementation exists, raise AIUnavailable (UI shows a safe error state)
Provider-specific code lives only in app/ai/providers/.
"""
import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.ai import rules
from app.ai.providers.base import ImageInput, LLMProvider, ProviderError
from app.ai.schemas import SkillExtraction
from app.core.config import PROMPTS_DIR, Settings, get_settings
from app.core.errors import AIUnavailable

log = logging.getLogger("rpl.ai")
T = TypeVar("T", bound=BaseModel)

ADVISORY = "AI assistance only — assessor verification required."


@dataclass
class AIResult:
    data: BaseModel
    kind: str
    provider: str
    model: str | None
    prompt_file: str | None
    prompt_version: str | None
    valid: bool = True
    fallback_used: bool = False
    attempts: int = 1
    error: str | None = None
    extra: dict = field(default_factory=dict)

    @property
    def confidence(self) -> float | None:
        return getattr(self.data, "confidence", None)


def load_prompt(name: str) -> tuple[str, str, str]:
    """Prompt files: '# version: X' header, then '## system' and '## user' sections."""
    raw = (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")
    version = re.search(r"^# version:\s*(\S+)", raw, re.M)
    system = raw.split("## system", 1)[1].split("## user", 1)[0].strip()
    user = raw.split("## user", 1)[1].strip()
    return (version.group(1) if version else "0"), system, user


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in response")
    return json.loads(text[start : end + 1])


def build_provider(settings: Settings) -> LLMProvider | None:
    """None means: use deterministic rules (the 'mock' provider)."""
    name = settings.ai_provider.lower()
    if name == "mock":
        return None
    if name == "gemini":
        from app.ai.providers.gemini import GeminiProvider  # noqa: PLC0415
        return GeminiProvider(settings.gemini_api_key or "", settings.gemini_model, settings.ai_timeout_seconds)
    if name == "openai":
        from app.ai.providers.openai import OpenAIProvider  # noqa: PLC0415
        return OpenAIProvider(settings.openai_api_key or "", settings.openai_model, settings.ai_timeout_seconds)
    raise ProviderError(f"Unknown AI_PROVIDER '{settings.ai_provider}'")


class AIService:
    def __init__(self, provider: LLMProvider | None = None, *, use_settings: bool = True):
        self.settings = get_settings()
        self._provider_error: str | None = None
        if provider is not None or not use_settings:
            self.provider = provider
        else:
            try:
                self.provider = build_provider(self.settings)
            except ProviderError as e:
                # Configured provider unusable (e.g. missing key): run on rules, report why.
                log.warning("AI provider unavailable, using rules: %s", e)
                self.provider, self._provider_error = None, str(e)

    # ---- core ---------------------------------------------------------------------------------
    def _run(self, kind: str, prompt_name: str, variables: dict, schema: type[T],
             rule_fn: Callable[[], T] | None, images: list[ImageInput] | None = None) -> AIResult:
        version, system, user_tpl = load_prompt(prompt_name)
        if self.provider is None:
            if rule_fn is None:
                raise AIUnavailable("AI analysis is not available right now.")
            return AIResult(rule_fn(), kind, "rules", None, prompt_name, version, error=self._provider_error)

        user = user_tpl
        for k, v in variables.items():
            user = user.replace("{{" + k + "}}", v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
        schema_json = schema.model_json_schema()
        user += "\n\nReturn ONLY one JSON object matching this JSON Schema:\n" + json.dumps(schema_json)
        last_err = None
        for attempt in (1, 2):
            try:
                raw = self.provider.complete_json(system, user, schema_json, images)
                data = schema.model_validate(_extract_json(raw))
                return AIResult(data, kind, self.provider.name, self.provider.model, prompt_name, version, attempts=attempt)
            except ProviderError as e:
                last_err = str(e)
                break  # provider down: retrying the same call immediately is pointless
            except (ValueError, ValidationError) as e:
                last_err = f"invalid output: {type(e).__name__}"
                user += "\n\nYour previous reply was not valid JSON for the schema. Reply again with only the JSON object."
        log.warning("AI %s failed (%s); falling back to rules", kind, last_err)
        if rule_fn is None:
            raise AIUnavailable("AI analysis is not available right now. Please continue; the assessor can review manually.")
        return AIResult(rule_fn(), kind, "rules", None, prompt_name, version, valid=True, fallback_used=True,
                        attempts=2, error=last_err)

    # ---- public functions (spec §31) ----------------------------------------------------------
    def extract_worker_skills(self, text: str, profile: dict | None = None) -> AIResult:
        return self._run(
            "skill_extraction", "skill_extraction",
            {"declaration": text, "profile": profile or {}},
            SkillExtraction, lambda: rules.extract_worker_skills(text, profile),
        )


def get_ai_service() -> AIService:
    return AIService()
