"""Deterministic rule-based implementations.

Evidence analysis without an LLM is limited to what code can honestly measure (image quality, required-evidence
completeness, the uploader's caption). It never suggests a score because it does not understand image content.

Used (a) as the default 'mock' provider for demos/tests/offline, and (b) as the fallback when an LLM
returns invalid output twice. Outputs carry provider='rules' so the UI can say "rule-based (no LLM)".
"""
from app.ai.schemas import DocumentClaims, EvidenceObservation, ExtractedItem, SkillExtraction
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


# ---- Evidence --------------------------------------------------------------------------------------
def image_quality(data: bytes) -> dict:
    """Heuristic quality measures (not content understanding)."""
    import io

    from PIL import Image, ImageFilter, ImageStat

    img = Image.open(io.BytesIO(data))
    w, h = img.size
    gray = img.convert("L")
    gray.thumbnail((800, 800))
    brightness = ImageStat.Stat(gray).mean[0]
    edges = gray.filter(ImageFilter.FIND_EDGES)
    sharpness = ImageStat.Stat(edges).var[0]
    return {"width": w, "height": h, "brightness": round(brightness, 1), "edge_variance": round(sharpness, 1)}


def analyze_evidence(*, kind: str, mime: str, size_bytes: int, caption: str | None, criterion_text: str | None,
                     evidence_hint: str | None, required: list[dict], uploaded_kinds_for_criterion: list[str],
                     data: bytes | None) -> EvidenceObservation:

    observed, missing, concerns = [], [], []
    observed.append(f"{kind.capitalize()} received ({mime}, {size_bytes / 1024:.0f} KB)")
    conf = 0.5
    if kind == "image" and data:
        try:
            q = image_quality(data)
            observed.append(f"Resolution {q['width']}×{q['height']}")
            if min(q["width"], q["height"]) < 480:
                missing.append("Low resolution — details of terminations/labels may not be readable")
            if q["brightness"] < 50:
                missing.append("Image is dark — retake with more light")
            elif q["brightness"] > 220:
                missing.append("Image is over-exposed — retake without direct glare")
            if q["edge_variance"] < 60:
                missing.append("Image may be blurred — hold the camera steady")
            else:
                observed.append("Image sharpness adequate (heuristic)")
            conf = 0.6
        except Exception:  # corrupt image passes magic-byte check but fails decoding
            concerns.append("Image could not be decoded — ask the candidate to re-upload")
            conf = 0.2
    if caption:
        observed.append(f"Candidate's caption: “{caption[:160]}”")
        low = caption.lower()
        if any(k in low for k in ("without gloves", "no gloves", "live wire", "bina gloves", "current chalu")):
            concerns.append("Caption suggests work on live parts or without PPE — verify safety practice")
    for r in required:
        if r["kind"] not in uploaded_kinds_for_criterion:
            missing.append(f"Required evidence not yet uploaded: {r['what']} ({r['kind']})")
    if criterion_text:
        observed.append(f"Linked to criterion: {criterion_text}")
    return EvidenceObservation(
        observed=observed, potentially_missing=missing, safety_concerns=concerns, competency_indicators=[],
        suggested_score=None,
        suggested_score_reason="No score suggested: rule-based analysis checks file quality and completeness only; it does not interpret image content.",
        confidence=conf, analysis_basis="metadata_only",
    )


def extract_document_claims(doc_type: str, text: str | None) -> DocumentClaims:
    import re


    claims = []
    if text:
        from app.services.text import years_in_text
        y = years_in_text(text)
        if y is not None:
            claims.append(ExtractedItem(label=f"Experience stated: {y:g} years", source_text=None, confidence=0.6))
        for m in re.finditer(r"(?i)(worked|employed|working)\s+(?:as|with|at)\s+([^.\n]{3,80})", text):
            claims.append(ExtractedItem(label=f"{m.group(1).capitalize()} {m.group(2).strip()}", source_text=m.group(0)[:200], confidence=0.6))
        for m in re.finditer(r"(?i)(certificate|certified|course|training)\s+(?:in|of|for)\s+([^.\n]{3,80})", text):
            claims.append(ExtractedItem(label=f"{m.group(1).capitalize()}: {m.group(2).strip()}", source_text=m.group(0)[:200], confidence=0.5))
        claims.extend(extract_worker_skills(text).skills)
    return DocumentClaims(doc_type=doc_type, claims=claims[:20], confidence=0.5 if claims else 0.2)
