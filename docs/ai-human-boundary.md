# The boundary between AI assistance and human judgement

**Rule:** AI may suggest and explain. Only an authorised human assessor decides. The system never states that a
candidate is certified, passed or competent on the basis of AI output.

## What the AI does

| Function | Output | Stored as | Becomes official only if… |
|---|---|---|---|
| `extract_worker_skills` | skills, tools, tasks, safety practices, learning mode, missing information — each with the worker's own words | `ai_observations` (suggestion) | the **worker** confirms or edits the list |
| `analyze_evidence` | observed / potentially missing / safety concerns / competency indicators, optional suggested 0–4 score, confidence | `ai_observations` + `assessor_scores.ai_suggested_score` | never — the **assessor** records `final_score` separately |
| `extract_document_claims` | claims from an experience letter or certificate | `evidence.extracted_claims` | the **worker** confirms; authenticity is the assessor's call |
| `match_qualification`, `summarize_competencies`, `generate_skill_gaps`, `generate_recommendation`, `generate_assessment` | plain-language explanations | text alongside computed results | they never change a number |

## What the AI does not do

- It does not compute the qualification match, scores, competency percentages, gaps or the recommendation. These
  are deterministic, inspectable rules ([methodology.md](methodology.md)).
- It does not write `final_score`, a decision, or any workflow state reserved for the assessor. The decision endpoint
  accepts only the assigned assessor (`test_permissions.py::test_only_assessors_score_and_decide`).
- AI-suggested scores are **excluded** from all calculations (`services/scoring.py` reads `final_score` only).
- Without a real model and permission to send media (`AI_SEND_EVIDENCE=true`), evidence analysis checks only file
  quality and completeness and **suggests no score**, saying so on screen.

## How the separation is made visible

- Every AI output carries the stamp **AI ASSIST** (dashed amber) and the text *"AI assistance only — assessor
  verification required."*; assessor-owned areas carry **ASSESSOR** (solid ink).
- In the scoring workspace each criterion is split into **AI assistance** (left) and **Assessor decision** (right).
  The AI's suggested score appears only as a dashed outline on the 0–4 buttons; nothing is pre-selected.
- Choosing a different score from the AI is labelled "override" and logged (`score.overridden_ai`).
- The recommendation panel is titled "AI assistance — recommendation", lists every rule with pass/fail and source, and
  ends with *"AI-assisted assessment recommendation — final decision by authorised human assessor."*
- The decision panel records whether the assessor agreed with or differed from the recommendation; differing needs no
  justification beyond the mandatory comments — the assessor's judgement prevails.
- Rule-based outputs say "Rule-based (no LLM used)"; prepared demo outputs say "prepared demo output — not a live AI call".
- Workers never receive AI-suggested scores or assessor notes before the decision.

## Failure behaviour

Invalid AI output is retried once with a correction message; if still invalid — or the provider is down or not
configured — the deterministic rule implementation is used and marked `fallback_used`. If no rule exists, the API
returns a typed "AI unavailable" error and the assessor continues manually; an assessment never blocks on AI.

## Governance signals

The admin overview reports the AI fallback rate, how many criteria had AI suggestions, and the **assessor override
rate**. A high override rate means the AI is not helping and should be reviewed — a signal designed to keep AI
accountable to assessors rather than the reverse.
