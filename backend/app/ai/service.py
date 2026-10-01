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
from app.ai.schemas import DocumentClaims, EvidenceObservation, NarrativeOut, SkillExtraction
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

    def analyze_evidence(self, *, data: bytes | None, mime: str, kind: str, size_bytes: int, caption: str | None,
                         criterion: dict | None, task: dict | None, required: list[dict],
                         uploaded_kinds_for_criterion: list[str]) -> AIResult:
        """Observation on one evidence item. Media bytes go to the LLM only when AI_SEND_EVIDENCE=true."""
        def rule_fn():
            return rules.analyze_evidence(
                kind=kind, mime=mime, size_bytes=size_bytes, caption=caption,
                criterion_text=(criterion or {}).get("text"), evidence_hint=(criterion or {}).get("evidence_hint"),
                required=required, uploaded_kinds_for_criterion=uploaded_kinds_for_criterion, data=data)

        send_media = self.settings.ai_send_evidence and data is not None and (kind == "image" or (kind == "video" and getattr(self.provider, "name", "") == "gemini"))
        if self.provider is not None and not send_media:
            # Without the media an LLM would only be guessing from text; use the honest rule-based path.
            res = AIResult(rule_fn(), "evidence_analysis", "rules", None, "evidence_analysis", load_prompt("evidence_analysis")[0],
                           error="AI_SEND_EVIDENCE disabled: metadata-only analysis")
            return res
        return self._run(
            "evidence_analysis", "evidence_analysis",
            {"criterion": criterion or {}, "task": task or {}, "caption": caption or "", "required": required},
            EvidenceObservation, rule_fn, images=[ImageInput(mime, data)] if send_media and data else None,
        )

    # ---- Narrative helpers: explain computed results; they never change a number -----------------
    def _narrative(self, kind: str, prompt: str, payload: dict, template: str) -> AIResult:
        return self._run(kind, prompt, {"data": payload}, NarrativeOut,
                         lambda: NarrativeOut(summary=template, confidence=1.0))

    def match_qualification(self, match: dict) -> AIResult:
        top = match["results"][0]
        t = (f"Closest qualification: {top['title']} ({top['qualification_code']}, NSQF {top['nsqf_level']}) at {top['final_pct']}%. "
             f"{len(top['matched_skills'])} confirmed skills map to official learning outcomes; "
             f"{top['lo_coverage']['matched']} of {top['lo_coverage']['total']} outcomes are evidenced by the declaration.")
        return self._narrative("match_explanation", "qualification_matching", {"top": {k: top[k] for k in ("title", "final_pct", "components", "matched_skills", "eligibility")}}, t)

    def generate_assessment(self, plan_summary: dict) -> AIResult:
        t = (f"Your assessment has {plan_summary['n_tasks']} practical tasks covering {plan_summary['n_los']} learning outcomes of "
             f"{plan_summary['qualification']}. Each task lists its steps, safety rules and the photos to add.")
        return self._narrative("assessment_intro", "assessment_generation", plan_summary, t)

    def summarize_competencies(self, results: dict) -> AIResult:
        comp = {results["competency_labels"].get(k, k): v for k, v in results["competencies"].items() if v is not None}
        strong = [k for k, v in comp.items() if v >= 75]
        weak = [k for k, v in comp.items() if v < 60]
        t = (f"Overall practical score {results['overall_pct']}%. "
             + (f"Strong: {', '.join(strong)}. " if strong else "")
             + (f"Below threshold: {', '.join(weak)}." if weak else "All assessed areas at or above the 60% threshold."))
        return self._narrative("competency_summary", "competency_summary", {"competencies": comp, "overall": results["overall_pct"]}, t)

    def generate_skill_gaps(self, gaps: dict) -> AIResult:
        g = [a for a in gaps["areas"] if a["status"] == "gap"]
        t = ("No competency gaps against the 60% threshold in the assessed scope." if not g else
             "Gaps: " + "; ".join(f"{a['label']} {a['demonstrated']:.0f}% (needs {a['required']:.0f}%)" for a in g) + ".")
        return self._narrative("skill_gap_summary", "skill_gap_analysis", {"areas": [{k: a[k] for k in ("label", "required", "demonstrated", "gap")} for a in gaps["areas"]]}, t)

    def generate_recommendation(self, rec: dict) -> AIResult:
        failed = [r["label"] for r in rec["rule_trace"] if not r["passed"]]
        t = (f"Suggested outcome: {rec['outcome'].replace('_', ' ').lower()}. Competency coverage {rec['competency_coverage']:.0%}, "
             f"evidence coverage {rec['evidence_coverage']:.0%}. "
             + ("All rules satisfied." if not failed else "Not satisfied: " + "; ".join(failed) + ".")
             + " The assessor makes the final decision.")
        return self._narrative("recommendation_narrative", "recommendation", {k: rec[k] for k in ("outcome", "competency_coverage", "evidence_coverage", "overall_pct", "rule_trace", "flags")}, t)

    def extract_document_claims(self, doc_type: str, text: str | None, image: tuple[str, bytes] | None = None) -> AIResult:
        return self._run(
            "document_claims", "document_claims", {"doc_type": doc_type, "text": text or ""},
            DocumentClaims, lambda: rules.extract_document_claims(doc_type, text),
            images=[ImageInput(*image)] if image and self.settings.ai_send_evidence else None,
        )


def get_ai_service() -> AIService:
    return AIService()
