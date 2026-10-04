# Requirements Traceability Matrix

Each SIH26242 requirement / expected outcome is traced to the feature, screen, backend, data, test
and demo step that satisfies it. The **Status** column is updated at the end of every phase and is
only set to ✅ after the linked test passes and the demo step has been run.

Legend: ⬜ not started · 🟨 in progress · ✅ verified · 🧪 simulated (demo/test data)

## A. Problem-statement capabilities

| # | SIH requirement | Feature | Screen | Backend | Database | Test | Demo step | Status |
|---|---|---|---|---|---|---|---|---|
| R1 | Structured self-declaration of prior experience | Stepwise onboarding + experience declaration (text / optional voice / docs) | `/worker/profile`, `/worker/experience` | `POST /workers`, `PUT /workers/{id}`, `POST /workers/{id}/experience`, `POST /workers/{id}/documents` | `worker_profiles`, `worker_experiences` (versioned) | `test_workers.py::test_create_profile`, `::test_experience_versioning` | 1, 2 | ✅ |
| R1a | Never silently modify declaration | AI output stored as suggestion; worker confirm/edit | `/worker/experience` (review panel) | `POST /extract-skills`, `PUT /workers/{id}/skills` | `worker_skills.source/confirmed`, `ai_observations` | `test_extraction.py::test_suggestion_not_applied` | 3 | ✅ |
| R2 | Automatic mapping to NSQF qualification pack(s) | Mapping engine, ranked, per-LO coverage, explainable weights | `/worker/qualification-match` | `POST /qualifications/match`, `services/mapping.py` | `qualifications`, `qualification_competencies`, `assessment_plans.match_snapshot` | `test_mapping.py` (weights, coverage, ranking Electrician vs Wireman, eligibility) | 4 | ✅ |
| R3 | Guided practical task evaluation | Assessment plan + step checklists + safety prompts | `/worker/assessment`, `/assessor/assessment/[id]` | `POST /assessments`, `/start`, task bank loader | `assessment_tasks`, `assessment_criteria`, `assessment_attempts` | `test_assessment.py::test_plan_from_mapped_los` | 6 | ✅ |
| R4 | Video/image-based assessment aids where feasible | Evidence upload per criterion + AI evidence observation | `/worker/evidence`, assessor evidence panel | `POST /evidence`, `POST /evidence/{id}/analyze`, `AIService.analyze_evidence` | `evidence`, `ai_observations` | `test_evidence.py` (validation, linkage, mock analysis, malformed AI fallback) | 7, 8 | ✅ |
| R5 | Standardised scoring rubrics | 0–4 anchored rubric per criterion, weights | assessor scoring grid | `POST /assessments/{id}/tasks/{task_id}/score`, `services/scoring.py` | `assessor_scores` | `test_scoring.py` (task/LO/overall math) | 9 | ✅ |
| R6 | Reduced evaluator-to-evaluator variance | Rubric anchors + evidence checklist; consistency analytics | `/assessor/consistency`, `/admin/analytics` | `GET /analytics/consistency`, `services/consistency.py` | `consistency_ratings` (🧪) | `test_consistency.py` (κ, Fleiss κ, ICC vs hand fixtures) | 16 | ✅ 🧪 |
| R7 | NSQF-aligned competency profile | LO-level + official formative-dimension profile, radar/bars | `/worker/results`, candidate detail | `GET /competencies/{id}`, `services/competency.py` | `competency_results` | `test_competency.py` | 10 | ✅ |
| R8 | Certification recommendation for assessor sign-off | Rule-based recommendation with rule trace | candidate detail "Recommendation" | `POST /assessments/{id}/recommendation`, `services/recommendation.py` | `recommendations` | `test_recommendation.py` (70 % rule, safety gate, insufficient evidence) | 12 | ✅ |
| R9 | Offline-capable operation | PWA + IndexedDB + local-first writes + demo toggle | all worker screens; status chip | — (client) | Dexie stores | `frontend/__tests__/syncQueue.test.ts` | 15 | ✅ |
| R10 | Later synchronisation | Batch sync, idempotent, retry, conflict rules | "Reconnect & Sync" | `POST /sync`, `GET /sync/status`, `services/sync.py` | `sync_queue` | `test_sync.py` (idempotency, conflict, assessor-owned reject) | 15 | ✅ |

## B. Expected outcomes

| # | Expected outcome | Satisfied by | Status |
|---|---|---|---|
| O1 | Working workflow self-declaration → assessor scoring for ≥ 1 trade | R1–R5, R8, R11 for Electrician (DGT/1001) | ✅ |
| O2 | NSQF qualification-pack mapping engine | R2 | ✅ |
| O3 | Consistency improvement evidence on labelled test/simulation dataset | R6 (🧪) | ✅ 🧪 |
| O4 | Offline-capable mobile/web interface | R9, R10, mobile-first worker UI | 🟨 (SW to verify in Chrome) |
| O5 | Explicit separation of AI assistance vs human judgement | R11, R12 | ✅ |

## C. Supporting requirements

| # | Requirement | Feature | Screen | Backend | Database | Test | Demo step | Status |
|---|---|---|---|---|---|---|---|---|
| R11 | Human assessor final authority | Decision only by assessor role; AI fields read-only | `/assessor/candidates/[id]` (AI vs Assessor split) | `POST /assessor/decision` (role guard) | `assessor_decisions` | `test_permissions.py::test_worker_cannot_decide`, `::test_ai_cannot_write_final_score` | 13, 14 | ✅ |
| R12 | Override every AI suggestion and store overrides | Per-criterion override, skill override, recommendation override | scoring grid | score endpoint stores `ai_suggested_score` + `final_score` + `overrode_ai` | `assessor_scores` | `test_scoring.py::test_override_recorded` | 9 | ✅ |
| R13 | Skill gap analysis | required − demonstrated, LO-sourced topics | `/worker/results`, candidate detail | `GET /skill-gaps/{id}` | `skill_gaps` | `test_gaps.py` | 11 | ✅ |
| R14 | Self-assessment & RPL readiness | LO checklist + Cat IV eligibility + > 70 % pathway | `/worker/self-assessment` | `POST /assessments/{id}/self-assessment` | `assessment_plans.readiness_snapshot` | `test_readiness.py` | 5 | ✅ |
| R15 | Evidence traceability Score → Criterion → Evidence → Submission | Linked drill-down | assessor scoring grid | `GET /assessments/{id}` nested | FKs on `evidence`, `assessor_scores` | `test_evidence.py::test_traceability_chain` | 9 | ✅ |
| R16 | Audit trail | Event logging on every state change | `/admin/audit` | `services/audit.py` | `audit_logs` | `test_audit.py` | 14 | ✅ |
| R17 | Assessment report | PDF with disclaimer + audit metadata | candidate detail "Download report" | `GET /assessments/{id}/report.pdf` | — | `test_report.py` | 14 | ⬜ |
| R18 | Multilingual (EN + HI) | i18n dictionary, worker flow translated | worker screens | — | `users.preferred_language` | `i18n keys parity test` | 1 | ✅ |
| R19 | Admin management | trades, QPs (read-only official), tasks, rubrics, users, stats, sync, audit | `/admin/*` | `/admin/*` | various | `test_admin.py` | — | ✅ |
| R20 | Security & privacy | JWT, bcrypt, RBAC, upload validation, rate limit, no keys client-side, PII-redacted logs | — | `core/security.py` | `users` | `test_security.py` | — | ✅ |
| R21 | AI provider abstraction + validation + fallback | AIService, providers, prompts, retry/fallback | — | `app/ai/*`, `/prompts` | `ai_observations` | `test_ai_service.py` (mock, malformed, fallback) | 3, 8 | ✅ |
| R22 | Demo mode (Raj Kumar) | One-click scenario | `/` & header "DEMO MODE" | `POST /demo/load` | seeded rows (🧪) | `test_demo.py` | all | ✅ 🧪 |
| R23 | Dataset provenance & labelling | dataset docs, source metadata, `data_origin` column | `/about`, admin qualification page | — | `qualification_sources`, `data_origin` | `test_data_labels.py` (every synthetic row labelled) | — | ✅ |
| R24 | Graceful error states | AI unavailable, offline, upload/sync failed, invalid evidence, malformed AI, unauthorised, expired session | global error boundary + toasts | exception handlers (no stack traces) | — | `test_errors.py` | — | ✅ |

## D. Five-minute demo script ↔ steps

1 Registration (EN→HI toggle) · 2 Experience declaration · 3 AI skill extraction (confirm/edit) ·
4 Qualification matching (Electrician vs Wireman, per-LO coverage) · 5 Self-assessment & readiness ·
6 Practical task checklist · 7 Evidence upload · 8 AI evidence observation (advisory) ·
9 Assessor standardised scoring with override + traceability · 10 Competency profile ·
11 Skill gaps · 12 Recommendation with rule trace · 13 Assessor review (AI vs Assessor panes) ·
14 Final human decision → PDF report + audit · 15 Offline toggle → continue → Reconnect & Sync ·
16 Consistency analytics (labelled simulation).
