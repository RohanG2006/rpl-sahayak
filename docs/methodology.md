# Methodology

All numbers shown to users are produced by the deterministic rules below. Thresholds cite their source; anything that
is a project design choice says so.

## 1. Qualification mapping (`backend/app/services/mapping.py`)

For each official qualification *q* (Electrician DGT/1001, Wireman DGT/1009):

```
match(q) = 0.40·skill + 0.25·task + 0.15·experience + 0.10·occupation + 0.10·eligibility
```

- **Text basis.** Each learning outcome (LO) is represented by its official title plus its official assessment
  criteria. Worker phrases are the **worker-confirmed** skills and described work, expanded with a project-authored
  lexicon for colloquial / Hinglish terms (e.g. "MCB lagana"). Generic verbs present in almost every LO ("test",
  "install", "check" …) are excluded so they cannot inflate matches.
- **Similarity** of a phrase to an LO = IDF-weighted term recall: Σ idf(shared terms) / Σ idf(phrase terms), IDF over
  all trade LOs of all qualifications. Matched ≥ 0.5, partial ≥ 0.3.
- **skill** = mean best-LO similarity over confirmed skills; **task** = the same over described work sentences
  (falls back to skills when none).
- **experience** = min(1, years / 3) × (1 if the occupation matches, else 0.6) — 3 years from QF §22 Category IV.
- **occupation** = 1 when the declared occupation (normalised) equals the qualification title or an occupation/NCO
  title, else term overlap.
- **eligibility** = mean of the Category IV checks (QF §22): age ≥ 21, experience ≥ 3 years, entry qualification
  (QF item 15; Electrician: 10th with Science & Maths). pass = 1, unknown = 0.5, fail = 0.
- Weights are configurable (`MATCH_W_*`) and returned with every result, along with the per-LO coverage list and the
  phrase that matched each LO. Tools and safety practices are shown as supporting evidence, not mapped to LOs.

## 2. Readiness (`services/readiness.py`)

Scope = the LOs covered by the plan's practical tasks (8 of the 30 Electrician LOs in this prototype). The worker
answers *regularly* (1) / *sometimes* (0.5) / *never* (0) per LO.

- Pathway **direct assessment** if weighted coverage **> 70 %** — NCVET RPL Guidelines (Gazette No. 420,
  19 June 2024) §6.2(c); otherwise **upskilling suggested**. Per Annexure-1 the candidate may still proceed; the
  assessor decides.
- Claims of "regularly" for an LO not evidenced by the declaration are flagged for the assessor to probe.
- Self-assessment routes the candidate; it never scores them.

## 3. Scoring (`services/scoring.py`) — assessor-confirmed scores only

```
task %    = Σ(w_c · s_c) / (4 · Σ w_c) · 100          (s_c ∈ 0..4, scored criteria of the task)
LO %      = Σ(w_t · task %) / Σ w_t                    (tasks mapped to the LO)
area %    = Σ(w_t · task %) / Σ w_t                    (tasks in the competency area)
dim %     = Σ(w_c · s_c) / (4 · Σ w_c) · 100          (criteria tagged with an official formative dimension)
overall % = Σ(w_t · task %) / Σ w_t                    (fully scored tasks)
```

Rubric anchors, weights and the dimension mapping: [assessment-rubric.md](assessment-rubric.md).

## 4. Skill gaps (`services/gaps.py`)

gap = max(0, required − demonstrated), required = 60 % (QF DGT/1001 §23: minimum pass for Trade Practical; used here
as the prototype competency threshold). For criteria scored ≤ 2, learning topics are (a) the **official** LO
assessment criterion the criterion operationalises, labelled `[LO n]`, and (b) a **suggested** practice item, labelled
as not an official requirement. LOs outside the prototype scope are listed as *not assessed* — never as competent.

## 5. Recommendation (`services/recommendation.py`)

Rules are evaluated in order and all are reported:

| Rule | Condition | If it fails | Source |
|---|---|---|---|
| R0 | every criterion has an assessor score | reassessment suggested | workflow rule |
| R1 | evidence for ≥ 50 % of required items | reassessment suggested | project design rule (evidence-based assessment, QF §24) |
| R2 | no safety-critical criterion scored 0–1 | not yet ready | project design rule; QF §25 notes such errors "could cause fatal accidents" |
| R3 | > 70 % of assessed LOs at ≥ 60 % | not yet ready | NCVET RPL Guidelines §6.2(c) |
| R4 | overall ≥ 60 % | not yet ready | QF DGT/1001 §23 |

All pass → **eligible for assessor sign-off**. Informational flags (not changing the outcome): assessor overrode
≥ 30 % of AI suggestions; mean AI evidence confidence < 0.5; unsupported self-assessment claims; Category IV
eligibility not met. The assessor's decision is recorded separately with an agree/differ flag.

## 6. Assessor consistency (`services/consistency.py`, `services/stats.py`)

Each simulated case is scored with the live formula above for every assessor, then:

- per case: mean, sample SD, variance, range of the five assessors' overall %;
- per criterion item: exact and within-±1 pairwise agreement;
- quadratic-weighted Cohen's κ for each of the 10 assessor pairs (mean reported);
- Fleiss' κ over the five raters (0–4 treated as nominal — conservative);
- ICC(2,1), two-way random, absolute agreement, single rater, on case overall % (Shrout & Fleiss 1979).

Implementations are verified against published values (ICC 0.29 on Shrout & Fleiss Table 2; Fleiss' κ 0.210 on the
standard worked example). The dataset is a labelled simulation whose improvement is an input assumption
([dataset.md](dataset.md) §4); with real multi-assessor ratings the same code applies unchanged.

## 7. Evidence analysis without an LLM

Image checks: resolution (< 480 px short side flagged), brightness (< 50 dark, > 220 over-exposed), edge variance
(< 60 possibly blurred); required-evidence completeness per criterion; caption keywords suggesting unsafe work.
No score is suggested because the rules do not interpret image content.
