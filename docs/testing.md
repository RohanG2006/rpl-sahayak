# Testing

All automated tests run **offline with no AI keys**: the AI provider is forced to the deterministic rule engine,
real provider adapters are exercised against stand-in SDK modules, and the backend uses a dedicated PostgreSQL
database (`rpl_sahayak_test`) that is rebuilt on every run — never the development database.

## How to run

```bash
node docker/pg-embedded/start.mjs --test-db      # PostgreSQL on :5433 (creates rpl_sahayak_test)
backend/.venv/Scripts/python -m pytest backend -q                        # 134 backend tests
backend/.venv/Scripts/python -m pytest backend -q --cov=app --cov-report=term-missing   # with coverage (95%)
npm --prefix frontend test                        # 12 frontend tests (Vitest + fake IndexedDB)
npm --prefix frontend run lint                    # ESLint (clean)
npx --prefix frontend tsc --noEmit -p frontend    # type-check
npm --prefix frontend run build                   # production build
```

Each pytest run writes uploads to its own temporary folder and deletes it at the end.

## What is covered

| Area (spec §45) | Tests | Notes |
|---|---|---|
| Qualification matching | `test_mapping.py` | Score = weighted sum of reported components; Electrician vs Wireman ranking flips for a wireman profile; LO coverage; Category IV eligibility; configurable weights |
| Score calculation / weighted scoring | `test_scoring.py` | Hand-computed fixtures for task %, LO %, overall %, dimensions, safety flags |
| Skill gaps | `test_outcomes.py::test_low_scores_not_ready_and_gaps_cite_official_criteria` | Gap = required − demonstrated; topics quote official LO criteria vs "suggested" |
| Recommendation logic | `test_outcomes.py` | Eligible; safety gate; insufficient evidence → reassessment; rule trace R0–R4 with sources |
| Readiness (> 70 % rule) | `test_scoring.py::test_readiness_*` | 70 % is not > 70 %; unsupported claims flagged |
| Consistency statistics | `test_consistency.py` | ICC(2,1) = 0.29 on Shrout & Fleiss (1979); Fleiss' κ = 0.210 on the standard worked example; Cohen's κ hand example |
| Offline queue | `frontend/__tests__/syncQueue.test.ts` | Offline queueing, ordered batches (incl. same-millisecond regression), backoff, max attempts, evidence upload success/failure |
| Sync | `test_sync.py` | Idempotent replay, last-writer-wins conflict, assessor-owned ops rejected, partial failure |
| Permission checks | `test_permissions.py` | Matrix: anonymous → 401; worker → 403 on staff/admin; assessor → 403 on admin; worker↔worker and assessor↔assessor isolation; only assessors score/decide; workers never receive AI suggestions/notes |
| Evidence | `test_evidence.py` | Magic-byte validation (spoofed type rejected), size limit, idempotent upload, criterion traceability, rule analysis never suggests a score, LLM suggestion stored separately and override audited |
| AI layer (mocked) | `test_ai_service.py`, `test_providers.py` | Valid / fenced / malformed-then-valid / twice-malformed → rules / provider down; OpenAI & Gemini request shape (JSON mode, image/video parts) and error mapping |
| Error states (§47) | `test_errors_and_labels.py`, `test_auth.py`, `test_security.py` | Typed JSON errors for empty/invalid upload, unknown criterion, wrong workflow state, unknown qualification, invalid/expired token, validation fields, AI unavailable (503); internal errors never leak stack traces; login rate limit |
| Data provenance (R23) | `test_official_data.py`, `test_errors_and_labels.py` | Source PDFs match recorded SHA-256; task-bank references verbatim QF text; official / synthetic / simulation / user labels on rows and files |
| Workflow | `test_errors_and_labels.py`, `frontend/__tests__/workflow.test.ts` | States move forward only (explicit reset excepted), transitions audited, every state maps to an NCVET stage; honest lifecycle progress |
| Admin | `test_admin.py` | User lifecycle, self-lockout protection, rubric weights locked once scored, audit filtering; no password in audit |
| i18n | `frontend/__tests__/i18n.test.ts` | Hindi has every English key, identical `{placeholders}`, nothing empty or left in English |
| **Integration** | `test_outcomes.py::test_full_workflow_to_human_decision` | Worker → Profile → Match → Assessment → Self-assessment → Tasks → Evidence → Assessor scores → Recommendation → Human decision → results released to worker |

## Manual verification (in-app browser)

Run in the course of development; repeat before a demo.

- [x] Worker registration wizard at 375 px, EN ⇄ HI, no horizontal overflow
- [x] Experience → AI extraction review (remove/add items) → confirm
- [x] Qualification match (contribution bar, LO coverage grid, eligibility with QF references)
- [x] Self-assessment → readiness (75 % > 70 %) → start practical → tick/submit task
- [x] Assessor: scoring workspace (anchors, notes, AI vs assessor split) → recommendation with rule trace → decision
- [x] Worker results / progress after decision
- [x] Consistency dashboard (labelled simulation)
- [x] Offline demo: 3 photos + 4 tasks offline → Reconnect & Sync → server shows exactly-once application
- [x] Admin: overview, qualifications, rubric lock, user create/deactivate, audit filter
- [x] Session-expired notice, language persistence across reload, no hydration warnings

## Known gaps

| Gap | Why | Next step |
|---|---|---|
| Service worker (true device offline) | The embedded browser pane refuses service-worker registration | Verify in desktop Chrome: build, start, DevTools → Application → Service workers, Network → Offline, reload |
| Real LLM quality | No API keys in the test environment; adapters tested against stand-ins | Run with `AI_PROVIDER=gemini` or `openai` and compare suggestions against assessor scores |
| Browser automation in CI | Manual browser checks only | Add Playwright smoke tests for the demo path |
| Load/performance | Prototype scale (tens of candidates) | Candidate list computes results per row; paginate/cache before scaling |
