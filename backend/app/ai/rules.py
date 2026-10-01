"""Deterministic rule-based implementations.

Used (a) as the default 'mock' provider for demos/tests/offline, and (b) as the fallback when an LLM
returns invalid output twice. Outputs carry provider='rules' so the UI can say "rule-based (no LLM)".
"""
from app.ai.schemas import ExtractedItem, SkillExtraction
from app.services.text import find_term, lexicon, sentences, years_in_text

ACTION_HINTS = (
    "install", "repair", "fit", "fix", "wire", "wiring", "troubleshoot", "maintain", "service", "replace", "connect",
    "test", "check", "lagana", "lagata", "lagate", "theek", "dhundna", "banata", "लगाना", "ठीक", "बदलना",
)
GENERIC_TERMS = {"light", "fan", "switch", "testing", "meter", "board", "panel", "earth", "joint", "layout", "battery", "pump", "fault", "wiring", "iron"}
EQUIPMENT = {
    "Motor wiring and maintenance": "Electric motors / starters",
    "Pump set installation": "Pump sets",
    "Inverter / UPS / stabilizer servicing": "Inverter / UPS / stabilizer",
    "Transformer maintenance": "Transformer",
    "Solar panel installation": "Solar panels",
    "Control panel wiring": "Control panel",
    "Energy meter board installation": "Energy meter",
    "MCB / circuit breaker installation": "Distribution board / MCB",
}


def _match(text: str, entries: list[dict]) -> list[ExtractedItem]:
    low = text.lower()
    out = []
    for e in entries:
        hits = [(find_term(low, t), t) for t in e["terms"]]
        hits = [(i, t) for i, t in hits if i >= 0]
        if not hits:
            continue
        idx, term = min(hits)
        specific = [t for _, t in hits if t.lower() not in GENERIC_TERMS]
        conf = 0.9 if specific and len(hits) > 1 else 0.8 if specific else 0.6
        snippet = text[max(0, idx - 30): idx + len(term) + 30].strip()
        out.append(ExtractedItem(label=e["canonical"], source_text=snippet, confidence=conf))
    return out


def extract_worker_skills(text: str, profile: dict | None = None) -> SkillExtraction:
    lex = lexicon()
    profile = profile or {}
    occ = _match(text, lex["occupations"])
    skills = _match(text, lex["skills"])
    tools = _match(text, lex["tools"])
    safety = _match(text, lex["safety"])
    modes = _match(text, lex["learning_modes"])
    equipment = [ExtractedItem(label=EQUIPMENT[s.label], source_text=s.source_text, confidence=s.confidence)
                 for s in skills if s.label in EQUIPMENT]
    sents = sentences(text)
    tasks = [ExtractedItem(label=s[:150], source_text=s[:400], confidence=0.7)
             for s in sents if any(h in s.lower() for h in ACTION_HINTS)]
    years = years_in_text(text)
    evidence = [s for s in sents if years_in_text(s) is not None or any(
        k in s.lower() for k in ("worked", "employer", "company", "contractor", "shop", "uncle", "under", "ke saath", "naukri"))]

    missing = []
    if years is None and not profile.get("years_experience"):
        missing.append("Years of experience not stated")
    if not tools and not profile.get("tools"):
        missing.append("Tools used not mentioned")
    if not safety:
        missing.append("No safety practices described (e.g. switching off supply, gloves, tester)")
    if not any(k in text.lower() for k in ("worked", "employer", "company", "contractor", "shop", "site")) and not profile.get("current_employer"):
        missing.append("Employer or work setting not described")
    if not profile.get("education_level"):
        missing.append("Formal education level not provided")
    if not skills:
        missing.append("No recognisable trade skills found — please describe the work you do")

    conf = 0.35 + 0.1 * min(4, len(skills)) + (0.1 if years is not None else 0) + (0.1 if occ else 0)
    return SkillExtraction(
        occupation=occ[0].label if occ else None,
        experience_years=years,
        skills=skills,
        tools=tools,
        tasks=tasks,
        equipment=equipment,
        safety_practices=safety,
        learning_mode=modes,
        experience_evidence=evidence[:5],
        confidence=round(min(conf, 0.9), 2),
        missing_information=missing,
    )
