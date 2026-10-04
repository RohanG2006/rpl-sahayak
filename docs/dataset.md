# Datasets and Provenance

The project uses three kinds of data. They live in separate folders, are separately versioned,
and every row in the database carries a `data_origin` column so they can never be mixed
without a label.

| Label | Meaning | Where |
|---|---|---|
| **OFFICIAL SOURCE DATA** | Extracted verbatim (or field-by-field) from government publications | `data/sources/`, `data/qualifications/` |
| **PROJECT-AUTHORED REFERENCE DATA** | Written by the project team; *derived from* official LO text but not itself official (task bank, rubric anchors, skill lexicon) | `data/assessment/`, `data/qualifications/*_lexicon.json` |
| **SYNTHETIC DEMO DATA** | Invented people and assessments for demonstration. Not real worker data. | `data/demo/` (except consistency set) |
| **SIMULATION / TEST DATA** | Generated rating data used only to demonstrate the consistency measurement | `data/demo/consistency_test_set.csv` |

Dataset version: **prototype-v1** (machine-readable record: `data/qualifications/source_metadata.json`).

---

## 1. Official source data

### 1.1 Files retrieved

All files were retrieved on **2026-10-01 (17:35 UTC)** with `curl` and stored unmodified in
`data/sources/`. Text extractions (`*.txt`, via `pdfplumber`) sit beside each PDF for review.

| File | Publisher | URL | SHA-256 |
|---|---|---|---|
| `QF_Electrician_CTS2.0_NSQF-4.pdf` (25 pp.) | DGT, MSDE — NSQF Qualification File, "Approved in 22th NSQC Meeting-NCVET-25th August 2022" | https://www.nqr.gov.in/sites/default/files/QF_Electrician_CTS2.0_NSQF-4.pdf | `7ac84a9b967b710c42da0184afdc7c193fe050064a6648d7e0623b9634fd6db3` |
| `QF_Wireman_CTS2.0_NSQF-4.pdf` | DGT, MSDE — NSQF Qualification File | https://www.nqr.gov.in/sites/default/files/QF_Wireman_CTS2.0_NSQF-4.pdf | `70676fc558844158dad55d2a5deac1f83b11daca18d68f7abecb7446f6a79844` |
| `NCVET_RPL_guidelines_2023-01-30.pdf` (41 pp.) | NCVET — *Draft* Guidelines for RPL, 27 Jan 2023, Version 10.2 | https://ncvet.gov.in/wp-content/uploads/2023/01/RPL-guidelines-for-PC-30.01.23.pdf | `52039f4f97cf1938dc58ab1504d3c6a5106095c0551c940ad732ee546ea77562` |
| `NCVET_RPL_2024-09.pdf` (58 pp.) | NCVET — Guidelines for RPL, F.No. 22003/05/2023/NCVET dated 11 Aug 2023, Gazette of India Extraordinary Part III Sec 4, No. 420, 19 Jun 2024 | https://ncvet.gov.in/wp-content/uploads/2024/09/RPL.pdf | `35af675aa73c1c4830bc0a306081c264376f63f0e1de35769d28508f0e55abc0` |

National Qualification Register home: https://www.nqr.gov.in/ (index; individual QF PDFs above).

### 1.2 Fields extracted — Electrician (primary trade)

| Field | Value as published | QF location |
|---|---|---|
| Qualification title | ELECTRICIAN | §1 |
| Qualification code | DGT/1001 | §2 |
| NCVET code | 2022/POW/DGT/06309 | p.1 |
| NSQF level | 4 | §12 |
| NCO code / occupation | 7411.0100 Electrician General; 7412.0200 Electrical Fitter | §3 |
| Nature & purpose; job description | text, long-term qualification | §4, §9 |
| Awarding / accrediting body | Directorate General of Training (DGT) | §5–6 |
| Notional hours | Yr1/Yr2: Practical 840/840, Theory 240/300, Employability 120/60, total 1200/1200; OJT 150/150 | §13 |
| Entry requirement / min age | 10th pass with Science & Mathematics; 14 yrs | §15 |
| Progression | Technician → Senior Technician → Supervisor → Manager; Entrepreneur; Diploma/ATS/CITS/Advanced Diploma (Vocational) | §16 |
| RPL arrangement | Yes — "Guidelines for Private candidate", DGT MIS portal | §17 |
| Planned review | 3 years from date of approval | §19 |
| Components | 30 trade-specific LOs with skill hours, knowledge hours, level, NOS codes; 12 employability-skill LOs | §20 |
| LO assessment criteria | full criterion statements per LO, Year 1 / Year 2 | pp.11–20 |
| RPL eligibility for private candidates | Categories I–IV; Cat IV: entry qualification, age ≥ 21, ≥ 3 yrs relevant experience in registered establishment | §22 |
| Assessment strategy & marks | Practical 250, Theory 100, Employability 50, Formative 200 per year; pass 60 % practical & formative, 33 % others | §23 |
| Formative assessment dimensions & weightage | 10 terminal competencies (Safety consciousness 15 %, … VIVA 15 %) | §24 |

### 1.3 Fields extracted — Wireman (comparison record for ranking only)

Title WIREMAN, code DGT/1009, NCVET code 2022/POW/DGT/06310, NSQF level 4, NCO 7411.0301
Wireman, Light and Power, entry requirement 8th class pass, trade LOs with NOS codes and
assessment criteria. **No task bank or rubric is built for Wireman** — it is used only so the
mapping engine ranks real alternatives instead of scoring a single qualification against itself.

### 1.4 What is *not* taken from official sources (and is not invented)

- Fields absent from the QF (e.g. an official "RPL duration", international comparability, a
  per-NOS weighting) are stored as `null` with `"not_in_source"` notes — never filled in.
- **NOS code inconsistency:** the Electrician QF lists different NOS codes for some LOs in the
  summary table (§20) versus the LO/assessment-criteria table (pp.11–17), e.g. LO7 `PSS/N9403`
  vs `N/A`. Both are stored (`nos_codes_summary`, `nos_codes_lo_table`) with `nos_mismatch=true`.
  The UI shows the summary-table code and a footnote.
- NOS *titles/descriptions* are not in the QF; they are not populated.

### 1.5 Use of the RPL guidelines

The guidelines are used for **process design**, not as data rows:
- Workflow stages (Gazette Annexure-1, Flowchart 3, NSQF 4 without formal education).
- The "> 70 % of learning outcomes" rule (§6.2(c); Flowchart 1) used by readiness & recommendation.
- Assessor role statements (§6.2) reflected in the assessor UI and decision gate.

---

## 2. Project-authored reference data (derived, not official)

| File | Content | Derivation | Label shown in UI |
|---|---|---|---|
| `data/assessment/electrician_tasks.json` | 8 practical tasks, criteria, weights, evidence & safety requirements, 0–4 anchors | Each task cites the Electrician LO number(s) and the exact QF assessment-criterion sentence(s) it operationalises (`qf_criterion_ref`). Weights, anchors and step checklists are project design decisions. | "Prototype task bank derived from QF DGT/1001 learning outcomes" |
| `data/assessment/rubric.json` | Generic 0–4 scale + criterion → official formative dimension mapping | Scale wording from project spec; dimensions from QF §24 | as above |
| `data/qualifications/electrician_lexicon.json` | colloquial / Hinglish term → normalised skill → LO numbers | Hand-written by project team | "Project-authored lexicon" |
| `data/qualifications/electrician_nos.csv` | NOS code ↔ LO number pairs | Mechanical extraction from QF §20 + LO table | official (extracted) |

---

## 3. Synthetic demo data — `data/demo/`

Every CSV begins with the comment line
`# SYNTHETIC / DEMONSTRATION DATA — NOT REAL WORKER DATA` and every row has `data_origin=synthetic`.

The files hold **inputs only** (what a worker would provide and what a synthetic assessor would score).
Every derived value — skill extraction, qualification match, readiness, competency results, recommendation —
is computed by the application when the data is seeded through the real API (`python -m app.seed --demo`).

| File | Rows (prototype-v1) | Content |
|---|---|---|
| `workers.csv` | 40 | synthetic name, fake mobile (`90001xxxxx`), age, gender, state/district/locality, language, occupation, years, education, employer, archetype, target workflow stage |
| `experiences.csv` | 40 | free-text declaration (English / Hinglish / Hindi) |
| `skills.csv` | per worker | confirmed items: the rule extractor's output with simulated worker edits (an item removed, an item added) |
| `assessments.csv` | 25 | self-assessment answers over the 8 in-scope LOs; decision policy (`follow` the recommendation, or a deliberate synthetic-assessor disagreement) |
| `task_scores.csv` | per task | which practical tasks the worker submitted |
| `evidence.csv` | 326 | evidence metadata → one of 16 placeholder images in `data/demo/evidence/`, upload file name, caption, offline flag |
| `assessor_scores.csv` | 363 | synthetic assessor's final 0–4 score + note per criterion |
| `prepared_ai_observations.json` | 1 per evidence file | **prepared** AI observations (observed / missing / safety concern / suggested score / confidence) keyed by upload file name |
| `consistency_test_set.csv` | see §4 | **SIMULATION/TEST DATA** |

**Generation:** `scripts/generate_demo_data.py`, seeded (`SEED=2026`), reproducible.
**Names:** composed from lists of common Indian given names and surnames combined at random;
no record corresponds to a real person. Mobile numbers (`90001xxxxx`) are fake. Localities are real state/district
names (public geography). Synthetic worker accounts share the PIN `1234` (documented, demo only).

**Archetypes (10, ≥ 3 each):** highly experienced (5); medium (5); beginner (4); domestic (5); industrial (4);
informal apprentice (4); incomplete documentation (3); strong practical / weak theory (4); safety gaps (3);
missing evidence (3).

**Workflow spread after seeding:** 25 assessment plans — 5 decided, 7 awaiting the assessor's decision, 3 partly
scored, 4 with evidence and AI notes, 3 with tasks in progress, 3 before the practical — and 15 workers at earlier
stages (profile, declaration, extraction, confirmation, match).

**Assumptions:** experience years and skills are drawn per archetype; criterion scores are drawn from
archetype-specific distributions (e.g. "safety gaps" lowers safety-critical criteria by ~2 points; "strong practical /
weak theory" lowers knowledge, viva and drawing criteria; "missing evidence" uploads ~30 % of required items).
These are design assumptions for demonstrating realistic UI states, not empirical estimates. Some synthetic decisions
deliberately differ from the recommendation so "agreement with recommendation" is not trivially 100 %.

**Evidence images:** 16 placeholder schematics generated with Pillow, each watermarked "SYNTHETIC EVIDENCE
PLACEHOLDER — not a real photo" and captioned with the criterion it stands for.

**Prepared AI observations:** because the placeholder images contain no real work, AI observations for them are
pre-written to be consistent with the synthetic assessor's scores (suggested score equals the final score ~72 % of the
time, otherwise ±1). They are stored with provider `demo-prepared` and every screen labels them "prepared demo output
— not a live AI call". Uploads that are not in this file (real photos) go through the live rule/LLM path.

**Demo persona:** *Raj Kumar*, 6 years informal electrician experience (learned from his uncle) — synthetic. His
C02.1 observation reproduces the example in the project specification. `POST /api/v1/demo/raj` rebuilds only this
record at a checkpoint (`fresh`, `practical`, `evidence_ready`, `awaiting_decision`) and is available only when
`DEMO_MODE_ENABLED=true`.

**Assessors:** 5 synthetic assessor accounts (A01–A05); Raj is always assigned to A01.

---

## 4. Simulation / test data — assessor consistency

`data/demo/consistency_test_set.csv` columns:
`case_id, task_code, criterion_code, assessor_id, mode, score, data_origin`.

- 20 shared cases (C001–C020) × 8 tasks × all criteria × 5 synthetic assessors (A01–A05) × 2 modes
  (`baseline`, `standardised`).
- Generated by `scripts/generate_consistency.py` (seeded). Model, per case `i`, criterion `c`,
  assessor `a`:
  - latent level `T_ic` ∈ [0,4] (drawn from the case archetype)
  - baseline: `round(T_ic + b_a + e)`, `b_a ~ N(0, σ_b)` assessor severity/leniency, `e ~ N(0, σ_e)` interpretation noise
  - standardised: `round(T_ic + k·b_a + e')`, `k < 1`, `e' ~ N(0, σ_e')`, `σ_e' < σ_e` — models anchored
    rubric descriptors and a shared evidence checklist
  - clipped to 0–4. Parameter values are recorded in the CSV header and in `source_metadata.json`.
- **Important:** because `k`, `σ_e'` are chosen by us, the existence and size of any improvement in this
  dataset is a **consequence of the simulation assumptions**. The dataset demonstrates that the
  platform computes variance, SD, range, pairwise agreement, weighted Cohen's κ, Fleiss' κ and ICC
  correctly and displays a before/after comparison. It is **not** evidence of real-world improvement.
  A real pilot would replace this file with ratings collected from assessors scoring the same
  recorded evidence with and without the rubric.
- Parameters used for `prototype-v1` (also in `data/demo/consistency_parameters.json` and the CSV header):
  seed 2026; ability ~ U(1.2, 3.6); criterion SD 0.6; assessor severity ~ N(0, 0.5) → drawn A01 +0.433, A02 +0.402,
  A03 −0.989, A04 −0.074, A05 +0.284; baseline noise σ 0.7; standardised: severity × 0.35, noise σ 0.4.
  5,600 rows = 20 cases × 28 criteria × 5 assessors × 2 modes.
- Statistics (`backend/app/services/stats.py`) are verified in tests against published worked examples:
  ICC(2,1) = 0.29 on Shrout & Fleiss (1979) Table 2; Fleiss' κ = 0.210 on the standard 10-subject × 14-rater example.
- UI label: **"Prototype / Test Dataset Demonstration — not real-world validated improvement."**

---

## 5. Data ethics

- No real worker personal data is used anywhere in the repository.
- Users entering data in a live demo are told it is a prototype; minimal PII fields; no
  government ID numbers collected (ID document upload is a placeholder that stores only a
  document type and AI-extracted *claims*, and is never verified).
- Official qualification data retains attribution in the database (`qualification_sources`), in API
  responses (`source` object) and in the UI footer of every qualification view.
