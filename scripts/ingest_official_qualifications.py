"""
Ingest OFFICIAL qualification data from NQR Qualification File PDFs into machine-readable files.

    python scripts/ingest_official_qualifications.py

Inputs : data/sources/QF_*.pdf  (downloaded unmodified from nqr.gov.in, see docs/dataset.md)
Outputs: data/qualifications/<slug>_qualification.json
         data/qualifications/electrician_nos.csv
         data/qualifications/parse_report.md   (what was parsed, what needs human review)

Parsing is geometric (pdfplumber word positions): columns are separated by x-coordinate.
Scalar summary fields (codes, level, NCO, entry requirement, etc.) are NOT guessed by the parser;
they are listed in SUMMARY_FIELDS below, transcribed from the PDF with the page reference, and the
script verifies each value literally appears in the PDF text before writing it.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "sources"
OUT = ROOT / "data" / "qualifications"
RETRIEVED_AT = "2026-10-01T17:35:26Z"

ROMAN = re.compile(r"^\((x{0,3})(ix|iv|v?i{0,3})\)$")
NOS_RE = re.compile(r"PSS/N\s?\d{4}")
HEADER_CUTOFF, FOOTER_CUTOFF = 70, 760

# ---------------------------------------------------------------------------------------------
# Summary fields transcribed from the QF (page refs). Each value is verified against PDF text.
# ---------------------------------------------------------------------------------------------
SUMMARY_FIELDS = {
    "electrician": {
        "file": "QF_Electrician_CTS2.0_NSQF-4.pdf",
        "url": "https://www.nqr.gov.in/sites/default/files/QF_Electrician_CTS2.0_NSQF-4.pdf",
        "trade_code": "ELECTRICIAN",
        "is_assessable": True,
        "title": "ELECTRICIAN",
        "qualification_code": "DGT/1001",
        "ncvet_code": "2022/POW/DGT/06309",
        "nsqf_level": 4,
        "nco_codes": [
            {"code": "7411.0100", "title": "Electrician General"},
            {"code": "7412.0200", "title": "Electrical Fitter"},
        ],
        "occupations": ["Electrician General", "Electrical Fitter"],
        "nature": "Prepare skilled Technician to undertake the job roles of Electrician and will enable the trainee to install, maintain and repair electrical machineries, equipment and fittings in factories, workshops power houses, businesses and residential premises etc. It is a long term qualification.",
        "job_description": "Electrician will be able to install, maintain and repair electrical machineries, equipment and fittings in factories, workshops, power houses, businesses and residential premises etc. and the technician generally fits and assembles electrical machineries and equipment such as motors, transformers, generators, switchgears, fans etc.",
        "awarding_body": "Directorate General of Training (DGT)",
        "notional_hours": {
            "year_1": {"professional_skill": 840, "professional_knowledge": 240, "employability_skills": 120, "total": 1200, "ojt_group_project": 150},
            "year_2": {"professional_skill": 840, "professional_knowledge": 300, "employability_skills": 60, "total": 1200, "ojt_group_project": 150},
            "total": 2400, "ojt_total": 300,
        },
        "entry_requirements": "Passed 10th class examination with Science and Mathematics or its equivalent.",
        "entry_education_rank": 4,  # 10th on the project's education ladder (app.models.workers.EDUCATION_RANKS)
        "entry_requires_science_maths": True,
        "min_age_training": 14,
        "progression": {
            "professional": ["Technician", "Senior Technician", "Supervisor", "Manager", "Entrepreneur"],
            "technical_academic": ["Diploma/ Advance Diploma (Vocational)", "ATS", "CITS"],
        },
        "rpl_available": True,
        "rpl_notes": "Yes (For more details refer “Guidelines for Private candidate” in DGT website MIS portal).",
        "rpl_eligibility": {
            "category_iv_other_candidates": {
                "min_entry_qualification": True,
                "min_age": 21,
                "min_experience_years": 3,
                "experience_setting": "establishments implementing Apprenticeship Training Scheme (ATS)/ establishments registered under the Apprenticeship portal or registered MSMEs or Entities registered with any government/local authorities / shops covered under Factories Act 1948 and Shops and Establishments Act applicable for the concerned State",
                "page": 8,
            },
            "note": "Categories I-III (ITI ex-trainees, CoE trainees, SCVT trainees) also exist; see QF p.7-8. The prototype evaluates Category IV, the category applicable to informally trained workers.",
        },
        "assessment_scheme": {
            "assessing_body": "Controller of Examinations, DGT",
            "marks_per_year": {"practical": 250, "trade_theory": 100, "employability_skills": 50, "formative": 200, "total": 600},
            "min_pass_pct": {"trade_practical": 60, "formative": 60, "other_subjects": 33},
            "page": 9,
        },
        "formative_dimensions": [
            {"key": "safety", "label": "Safety consciousness", "weight_pct": 15},
            {"key": "hygiene", "label": "Workplace hygiene", "weight_pct": 5},
            {"key": "attendance", "label": "Attendance/ Punctuality", "weight_pct": 10},
            {"key": "manuals", "label": "Ability to follow Manuals/ Written instructions", "weight_pct": 5},
            {"key": "knowledge", "label": "Application of Knowledge", "weight_pct": 10},
            {"key": "tools", "label": "Skills to handle tools / equipment/ Instruments/ Devices", "weight_pct": 10},
            {"key": "materials", "label": "Economical use of materials", "weight_pct": 5},
            {"key": "strategy", "label": "Working Strategy", "weight_pct": 10},
            {"key": "quality", "label": "Quality in workmanship/ Performance", "weight_pct": 15},
            {"key": "viva", "label": "VIVA", "weight_pct": 15},
        ],
        "approval_note": "Approved in 22th NSQC Meeting-NCVET-25th August 2022",
        "review_note": "3 Yrs. from the Date of Approval",
        "licensing": "NOT REQUIRED",
        "summary_pages": {"title": 2, "code": 2, "ncvet_code": 1, "nsqf_level": 2, "hours": 3, "entry": 3, "rpl": 3, "components": "4-6", "rpl_eligibility": "7-8", "assessment": "8-10", "lo_table": "11-17", "employability_lo": "18-20"},
        "verify_literals": ["DGT/1001", "2022/POW/DGT/06309", "7411.0100", "7412.0200", "Level 4", "Passed 10th class examination with Science and", "Minimum age 14 years", "22th NSQC Meeting-NCVET-25th August 2022", "minimum 21 years of age", "minimum of 3 years", "Safety consciousness 15", "Quality in workmanship/ Performance 15"],
    },
    "wireman": {
        "file": "QF_Wireman_CTS2.0_NSQF-4.pdf",
        "url": "https://www.nqr.gov.in/sites/default/files/QF_Wireman_CTS2.0_NSQF-4.pdf",
        "trade_code": "WIREMAN",
        "is_assessable": False,
        "title": "WIREMAN",
        "qualification_code": "DGT/1009",
        "ncvet_code": "2022/POW/DGT/06310",
        "nsqf_level": 4,
        "nco_codes": [{"code": "7411.0301", "title": "Wireman, Light and Power"}],
        "occupations": ["Wireman, Light and Power"],
        "nature": "Prepare skilled Technician to undertake the job roles of Wireman and will enable the trainee to plan, install and repair electrical wiring such as cleat, conduit, casing, concealed etc in factories, workshops, business and residential premises etc. It is a long term qualification.",
        "job_description": "Wireman will be able to plan, install and repair electrical wiring, erect switch boards and fix switch box casings cleats, conduits, meters etc. in factories, workshops, business and residential premises etc. and the technician generally fixes fuses, covers as per diagram and eliminates chances of short circuit and earthing.",
        "awarding_body": "Directorate General of Training (DGT)",
        "notional_hours": {
            "year_1": {"professional_skill": 840, "professional_knowledge": 240, "employability_skills": 120, "total": 1200, "ojt_group_project": 150},
            "year_2": {"professional_skill": 840, "professional_knowledge": 300, "employability_skills": 60, "total": 1200, "ojt_group_project": 150},
            "total": 2400, "ojt_total": 300,
        },
        "entry_requirements": "Passed 8th Class.",
        "entry_education_rank": 3,
        "entry_requires_science_maths": False,
        "min_age_training": 14,
        "progression": {
            "professional": ["Wireman", "Senior Wireman", "Supervisor", "Manager", "Entrepreneur"],
            "technical_academic": ["10th/ Diploma/ Advance Diploma (Vocational)", "ATS", "CITS"],
        },
        "rpl_available": True,
        "rpl_notes": "Yes (For more details refer “Guidelines for Private candidate” in DGT website MIS portal).",
        "rpl_eligibility": {
            "category_iv_other_candidates": {"min_entry_qualification": True, "min_age": 21, "min_experience_years": 3, "page": 8},
        },
        "assessment_scheme": {},
        "formative_dimensions": [],
        "approval_note": None,
        "review_note": "3 Yrs from the Date of Approval",
        "licensing": "NOT REQUIRED",
        "summary_pages": {"title": 2, "code": 2, "ncvet_code": 1},
        "verify_literals": ["DGT/1009", "2022/POW/DGT/06310", "7411.0301", "Level 4", "Passed 8th Class.", "minimum 21 years of age", "minimum of 3 years"],
    },
}


def norm_space(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.;:)])", r"\1", s)
    return s


def nos_list(text: str) -> list[str]:
    m = re.search(r"\(NOS\s*:?(.*?)\)", text.replace("\n", " "))
    if not m:
        return []
    inner = m.group(1)
    codes = [c.replace(" ", "") for c in NOS_RE.findall(inner)]
    if not codes and "N/A" in inner:
        return ["N/A"]
    return codes


def strip_nos(text: str) -> str:
    return norm_space(re.sub(r"\(NOS\s*:?.*?\)", "", text.replace("\n", " ")))


def lines_from_words(words: list[dict], tol: float = 3.0) -> list[dict]:
    """Group words into visual lines (by 'top'), returning text, x0, x1, top."""
    words = sorted(words, key=lambda w: (round(w["top"]), w["x0"]))
    out: list[dict] = []
    for w in words:
        if out and abs(out[-1]["top"] - w["top"]) <= tol:
            out[-1]["words"].append(w)
        else:
            out.append({"top": w["top"], "words": [w]})
    for ln in out:
        ws = sorted(ln["words"], key=lambda w: w["x0"])
        ln["text"] = " ".join(w["text"] for w in ws)
        ln["x0"], ln["x1"] = ws[0]["x0"], ws[-1]["x1"]
    return out


# Imperative verbs that open QF assessment-criterion statements (parsing aid only)
ASSESSMENT_VERBS = (
    "Analyze Apply Assemble Calculate Calibrate Carry Carryout Check Combination Comply Connect Construct Control Create Demonstrate "
    "Describe Detect Determine Discuss Distinguish Draft Draw Erect Estimate Examine Execute Exhibit Explain Extend Fasten "
    "Follow Group Highlight Identify Illustrate Install List Maintain Make Measure Mount Operation Outline Perform Plan Plot "
    "Prepare Read Repair Replace Research Rewind Role Select Service Show Solder Solve Speed Start Test Troubleshoot Use Verify Write"
).split()


# ---------------------------------------------------------------------------------------------
# §20 formal structure (components with hours, level, NOS)
# ---------------------------------------------------------------------------------------------
def parse_components(pdf: pdfplumber.PDF) -> list[dict]:
    comps: list[dict] = []
    collecting = False
    for pno, page in enumerate(pdf.pages, start=1):
        words = [w for w in page.extract_words() if HEADER_CUTOFF < w["top"] < FOOTER_CUTOFF]
        text = " ".join(w["text"] for w in words)
        if not collecting and "TRADE SPECIFIC" not in text:
            continue
        stop_top = None
        for w in words:
            if w["text"] == "CORE" and any(v["text"] == "SKILL" and abs(v["top"] - w["top"]) < 3 for v in words):
                stop_top = w["top"]
        start_top = 0
        if not collecting:
            start_top = next(w["top"] for w in words if w["text"] == "SPECIFIC")
            collecting = True
        page_words = [w for w in words if w["top"] > start_top and (stop_top is None or w["top"] < stop_top - 1)]
        markers = sorted([w for w in page_words if w["x0"] < 75 and ROMAN.match(w["text"])], key=lambda w: w["top"])
        bounds = [m["top"] - 4 for m in markers]
        for w in page_words:
            if w["x0"] < 75 and ROMAN.match(w["text"]):
                continue
            # which component on this page does it belong to?
            idx = max([i for i, b in enumerate(bounds) if w["top"] >= b], default=-1)
            if idx == -1:
                if not comps:
                    continue
                target = comps[-1]  # continuation from previous page
            else:
                need = len(comps) - (len(markers) - idx)  # placeholder, replaced below
                target = None
            if idx >= 0:
                key = (pno, markers[idx]["top"])
                existing = next((c for c in comps if c["_key"] == key), None)
                if not existing:
                    existing = {"_key": key, "roman": markers[idx]["text"], "page": pno, "title_words": [], "skill": [], "knowledge": [], "level": []}
                    comps.append(existing)
                target = existing
            col = "title_words" if w["x0"] < 350 else "skill" if w["x0"] < 430 else "knowledge" if w["x0"] < 500 else "level"
            target[col].append(w)
        # ensure components with no other words are still created
        for m in markers:
            key = (pno, m["top"])
            if not any(c["_key"] == key for c in comps):
                comps.append({"_key": key, "roman": m["text"], "page": pno, "title_words": [], "skill": [], "knowledge": [], "level": []})
        comps.sort(key=lambda c: c["_key"])
        if stop_top is not None:
            break
    result = []
    for i, c in enumerate(comps, start=1):
        title_raw = " ".join(ln["text"] for ln in lines_from_words(c["title_words"]))

        def num(ws):
            toks = [w["text"] for w in ws if re.fullmatch(r"\d+|-", w["text"])]
            if not toks:
                return None
            return None if toks[0] == "-" else int(toks[0])

        result.append({
            "component_no": i,
            "roman": c["roman"],
            "title": strip_nos(title_raw),
            "nos_codes": nos_list(title_raw),
            "skill_hours": num(c["skill"]),
            "knowledge_hours": num(c["knowledge"]),
            "level": num(c["level"]),
            "page": c["page"],
        })
    return result


# ---------------------------------------------------------------------------------------------
# Learning outcome tables (LO title column | assessment criteria column)
# ---------------------------------------------------------------------------------------------
def parse_lo_tables(pdf: pdfplumber.PDF, start_marker: str, end_marker: str | None, category: str) -> list[dict]:
    los: list[dict] = []
    started = False
    year = None
    split_x = None
    right_edge = 0.0
    page_lines: list[tuple[int, list[dict], list[dict]]] = []
    for pno, page in enumerate(pdf.pages, start=1):
        words = [w for w in page.extract_words() if HEADER_CUTOFF < w["top"] < FOOTER_CUTOFF]
        lines_all = lines_from_words(words)
        texts = [l["text"] for l in lines_all]
        start_top, end_top = 0.0, None
        if not started:
            hit = next((l for l in lines_all if start_marker in l["text"]), None)
            if not hit:
                continue
            started = True
            start_top = hit["top"]
        if end_marker:
            hit = next((l for l in lines_all if end_marker in l["text"] and l["top"] > start_top), None)
            if hit:
                end_top = hit["top"]
        ws = [w for w in words if w["top"] > start_top and (end_top is None or w["top"] < end_top)]
        # find the criteria column start: most common x0 among words right of 150
        if split_x is None:
            xs = defaultdict(int)
            for w in ws:
                if 150 < w["x0"] < 320:
                    xs[round(w["x0"])] += 1
            split_x = max(xs, key=xs.get) - 6
        left = [w for w in ws if w["x0"] < split_x]
        right = [w for w in ws if w["x0"] >= split_x]
        pass
        page_lines.append((pno, lines_from_words(left), lines_from_words(right)))
        if end_top is not None:
            break

    current = None
    pending: list[str] = []
    for pno, left_lines, right_lines in page_lines:
        # Merge both columns in reading order by 'top'
        events = [("L", l) for l in left_lines] + [("R", r) for r in right_lines]
        events.sort(key=lambda e: (e[1]["top"], 0 if e[0] == "L" else 1))
        for side, ln in events:
            t = ln["text"]
            if side == "L":
                if re.fullmatch(r"(FIRST|SECOND) YEAR", t.strip(), re.I):
                    year = 1 if t.strip().upper().startswith("FIRST") else 2
                    continue
                if t.strip() in ("LEARNING OUTCOMES ASSESSMENT CRITERIA", "LEARNING OUTCOME ASSESSMENT CRITERIA", "LEARNING OUTCOMES", "LEARNING OUTCOME"):
                    continue
                m = re.match(r"^(\d{1,2})\.?\s+(.*)$", t)
                if m and ln["x0"] < 60:
                    if current and pending:
                        current["criteria"].append(list(pending))
                        pending = []
                    current = {"lo_number": int(m.group(1)), "year": year, "category": category, "title_raw": m.group(2), "criteria": [], "page": pno}
                    los.append(current)
                elif current:
                    current["title_raw"] += " " + t
            else:
                if re.fullmatch(r"(FIRST|SECOND) YEAR", t.strip(), re.I):
                    year = 1 if t.strip().upper().startswith("FIRST") else 2
                    continue
                if current is None or t.strip() in ("ASSESSMENT CRITERIA",):
                    continue
                pending.append(t)
                if t.rstrip().endswith("."):
                    current["criteria"].append(list(pending))
                    pending = []
    if current and pending:
        current["criteria"].append(list(pending))
    # Second pass: many criteria are not punctuated. A wrapped continuation line never starts with
    # an assessment verb that begins other criteria in the same table, so split there.
    verbs = set(ASSESSMENT_VERBS) | {c[0].split()[0] for lo in los for c in lo["criteria"] if c and c[0].split() and c[0][0].isupper()}
    verbs -= {"D.C.", "AC", "DC", "CT", "PT", "LT", "HT", "IE"}
    for lo in los:
        fixed: list[list[str]] = []
        for lines in lo["criteria"]:
            buf = [lines[0]]
            for ln_text in lines[1:]:
                first = ln_text.split()[0] if ln_text.split() else ""
                prev = buf[-1].rstrip()
                if first in verbs and not prev.endswith((",", "&", "/", "-", " and", " or", " the", " of", " to")):
                    fixed.append(buf)
                    buf = [ln_text]
                else:
                    buf.append(ln_text)
            fixed.append(buf)
        lo["criteria"] = [norm_space(" ".join(b)) for b in fixed]
    for lo in los:
        lo["nos_codes_lo_table"] = nos_list(lo["title_raw"])
        lo["title"] = strip_nos(lo.pop("title_raw"))
    return los


# ---------------------------------------------------------------------------------------------
def build(slug: str) -> dict:
    meta = SUMMARY_FIELDS[slug]
    path = SRC / meta["file"]
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    with pdfplumber.open(path) as pdf:
        full_text = norm_space(" ".join((p.extract_text() or "") for p in pdf.pages))
        missing = [lit for lit in meta["verify_literals"] if norm_space(lit) not in full_text]
        if missing:
            sys.exit(f"[{slug}] summary literal(s) not found in PDF text, refusing to write: {missing}")
        components = parse_components(pdf)
        trade_los = parse_lo_tables(pdf, "LEARNING OUTCOME (TRADE SPECIFIC)", "EMPLOYABILITY SKILLS (CORE SKILL)", "trade")
        emp_los = parse_lo_tables(pdf, "EMPLOYABILITY SKILLS (CORE SKILL)", "SECTION 2", "employability")

    review: list[str] = []
    # Join component summary (hours, NOS from §20) to LO table rows by position
    if len(components) != len(trade_los):
        review.append(f"component count {len(components)} != LO table count {len(trade_los)}")
    competencies = []
    for i, lo in enumerate(trade_los):
        comp = components[i] if i < len(components) else {}
        summ = comp.get("nos_codes", [])
        lo_tab = lo["nos_codes_lo_table"]
        mismatch = sorted(set(summ)) != sorted(set(lo_tab))
        if lo["lo_number"] != i + 1:
            review.append(f"LO numbering gap at position {i + 1}: got {lo['lo_number']}")
        if not lo["criteria"]:
            review.append(f"LO {lo['lo_number']} has no parsed assessment criteria")
        competencies.append({
            "category": "trade",
            "lo_number": lo["lo_number"],
            "year": lo["year"],
            "title": lo["title"],
            "summary_title": comp.get("title"),
            "assessment_criteria": lo["criteria"],
            "nos_codes_summary": summ,
            "nos_codes_lo_table": lo_tab,
            "nos_mismatch": mismatch,
            "skill_hours": comp.get("skill_hours"),
            "knowledge_hours": comp.get("knowledge_hours"),
            "nsqf_level": comp.get("level"),
            "source_pages": {"summary": comp.get("page"), "lo_table": lo["page"]},
        })
    for lo in emp_los:
        competencies.append({
            "category": "employability", "lo_number": lo["lo_number"], "year": None, "title": lo["title"],
            "summary_title": None, "assessment_criteria": lo["criteria"], "nos_codes_summary": [],
            "nos_codes_lo_table": [], "nos_mismatch": False, "skill_hours": None, "knowledge_hours": None,
            "nsqf_level": None, "source_pages": {"lo_table": lo["page"]},
        })

    fields = {k: v for k, v in meta.items() if k not in ("file", "url", "verify_literals", "trade_code", "is_assessable")}
    not_in_source = ["NOS titles/descriptions", "International comparability", "RPL-specific duration"]
    return {
        "_label": "OFFICIAL SOURCE DATA — extracted from NQR Qualification File. Do not edit by hand; re-run scripts/ingest_official_qualifications.py.",
        "trade_code": meta["trade_code"],
        "is_assessable": meta["is_assessable"],
        **fields,
        "not_in_source": not_in_source,
        "source": {
            "source_name": "National Qualification Register (NQR) / NCVET — NSQF Qualification File submitted by DGT, MSDE",
            "source_url": meta["url"],
            "file": f"data/sources/{meta['file']}",
            "sha256": sha,
            "retrieved_at": RETRIEVED_AT,
            "source_type": "official",
        },
        "competencies": competencies,
        "_parse_review": review,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = ["# Official qualification parse report", "", f"Generated by `scripts/ingest_official_qualifications.py`. Retrieved {RETRIEVED_AT}.", ""]
    for slug in SUMMARY_FIELDS:
        q = build(slug)
        (OUT / f"{slug}_qualification.json").write_text(json.dumps(q, indent=2, ensure_ascii=False), encoding="utf-8")
        trade = [c for c in q["competencies"] if c["category"] == "trade"]
        emp = [c for c in q["competencies"] if c["category"] == "employability"]
        mism = [c["lo_number"] for c in trade if c["nos_mismatch"]]
        report += [
            f"## {q['title']} ({q['qualification_code']})",
            f"- trade LOs: {len(trade)} · employability LOs: {len(emp)} · total criteria: {sum(len(c['assessment_criteria']) for c in q['competencies'])}",
            f"- LOs whose NOS codes differ between §20 summary and LO table (kept both): {mism or 'none'}",
            f"- parser review notes: {q['_parse_review'] or 'none'}",
            "",
        ]
        print(f"{slug}: {len(trade)} trade LOs, {len(emp)} employability LOs, mismatch {mism}, review {q['_parse_review']}")
        if slug == "electrician":
            with (OUT / "electrician_nos.csv").open("w", newline="", encoding="utf-8") as f:
                f.write("# OFFICIAL SOURCE DATA — NOS codes per learning outcome, QF DGT/1001 (NQR). source_column distinguishes the two QF tables.\n")
                w = csv.writer(f)
                w.writerow(["qualification_code", "lo_number", "lo_title", "nos_code", "source_column", "nos_mismatch"])
                for c in trade:
                    for col, codes in (("summary_table_s20", c["nos_codes_summary"]), ("lo_assessment_table", c["nos_codes_lo_table"])):
                        for code in codes or ["(none listed)"]:
                            w.writerow([q["qualification_code"], c["lo_number"], c["title"], code, col, c["nos_mismatch"]])
    (OUT / "parse_report.md").write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
