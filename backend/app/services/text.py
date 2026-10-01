"""Tiny, dependency-free text utilities + lexicon access (shared by extraction and matching)."""
import json
import re
from functools import lru_cache

from app.core.config import DATA_DIR

_WORD = re.compile(r"[a-z0-9]+|[ऀ-ॿ]+")

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "twenty-five": 25, "thirty": 30,
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6, "che": 6, "saat": 7,
    "aath": 8, "nau": 9, "das": 10, "बारह": 12, "दस": 10, "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6, "सात": 7,
    "आठ": 8, "नौ": 9, "चार": 4, "तीन": 3, "दो": 2, "एक": 1,
}


@lru_cache
def lexicon(trade: str = "electrician") -> dict:
    return json.loads((DATA_DIR / "qualifications" / f"{trade}_lexicon.json").read_text(encoding="utf-8"))


@lru_cache
def stopwords() -> frozenset[str]:
    return frozenset(lexicon()["stopwords"])


def stem(w: str) -> str:
    """Very light English suffix stripping, enough to align 'installing'/'installation'/'install'."""
    if not w.isascii() or len(w) <= 4:
        return w
    for suf in ("ations", "ation", "ings", "ing", "ers", "er", "ies", "es", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: -len(suf)]
            break
    if w.endswith("ic") and len(w) > 6:  # electric/electrical -> electr? keep 'electric'
        return w
    return w


def tokens(text: str) -> list[str]:
    sw = stopwords()
    return [stem(t) for t in _WORD.findall(text.lower()) if t not in sw and len(t) > 1]


def find_term(text_lower: str, term: str) -> int:
    """Index of term in text (word-bounded for Latin terms), or -1."""
    term = term.lower()
    if term.isascii():
        m = re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?:s|es)?(?![a-z0-9])", text_lower)
        return m.start() if m else -1
    return text_lower.find(term)


def years_in_text(text: str) -> float | None:
    t = text.lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?|saal|sal|साल|वर्ष)", t)
    if m:
        return float(m.group(1))
    for word, n in sorted(NUMBER_WORDS.items(), key=lambda kv: -len(kv[0])):
        if re.search(r"(?<![\wऀ-ॿ])" + re.escape(word) + r"\s+(?:years?|yrs?|saal|sal|साल|वर्ष)", t):
            return float(n)
    return None


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?।])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]
