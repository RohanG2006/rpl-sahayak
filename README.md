# RPL-Sahayak AI

**AI-Assisted Prior Learning Assessment & Assessor Support Platform** — a working prototype for Smart India
Hackathon 2026, problem statement **SIH26242**: *AI-Assisted Skill Assessment Tool for Recognition of Prior Learning*.

> AI assistance only — assessor verification required. RPL-Sahayak suggests and explains; an authorised human
> assessor makes every decision. This is a prototype: it is not an NCVET/DGT system and issues no certificates.

## Problem

Millions of electricians, plumbers and other trade workers learned on the job. Recognition of Prior Learning (RPL)
lets them gain an NSQF qualification, but today the process depends on paper declarations, a single assessor's
judgement and patchy evidence. Workers struggle to describe their skills in the language of qualification files,
assessors score inconsistently, and rural candidates often have no reliable connectivity.

## Solution

A mobile-first, offline-capable workflow that follows the NCVET RPL Guidelines (Gazette, 19 June 2024, Annexure-1):

1. **Worker declares experience** in Hindi or English, by text or voice. AI extracts skills, tools, tasks and safety
   practices; the worker confirms or edits them.
2. **Qualification mapping** ranks official NSQF qualifications against the confirmed skills, showing which learning
   outcome (LO) each skill matched and why.
3. **Self-assessment and readiness**: more than 70 % LO coverage means direct assessment, otherwise upskilling is
   suggested (NCVET §6.2(c)).
4. **Guided practical tasks** with steps and safety rules, and photo/video **evidence** linked to rubric criteria,
   all usable offline.
5. **AI evidence observations** are shown to the assessor as advisory notes.
6. **Assessor scores** every criterion on a standardised 0–4 rubric with written anchors.
7. **Competency profile, skill gaps and an explainable recommendation**, built from inspectable rules with sources.
8. **The assessor records the final decision**; the worker sees the outcome, gaps and a **PDF report**.
9. **Assessor-consistency analytics** (Cohen's/Fleiss' κ, ICC) and an **audit log** for administrators.

Trade in this prototype: **Electrician** (DGT/1001, NSQF 4). Wireman (DGT/1009) is loaded for ranking only. Adding a
trade is data, not code ([architecture.md](docs/architecture.md#adding-a-trade)).

## Architecture

```
Next.js 16 PWA (EN/HI, IndexedDB + sync queue)  ──JWT──▶  FastAPI  ──▶  PostgreSQL
                                                             │
                     deterministic engines ◀─────────────────┤ mapping · readiness · scoring · gaps · recommendation
                                                             │ consistency · workflow (19 states) · PDF report · audit
                     AIService ◀─────────────────────────────┘ rules (default) | Gemini | OpenAI — JSON-validated, fallback
```

Diagrams and details: [docs/architecture.md](docs/architecture.md).

| Folder | Contents |
|---|---|
| `backend/` | FastAPI app (`app/`), Alembic migrations, seeders, 144 pytest tests |
| `frontend/` | Next.js app: worker, assessor, admin, demo and public pages; offline layer; Vitest tests |
| `prompts/` | All LLM prompts as text files |
| `data/sources/` | Official PDFs (with SHA-256 hashes) |
| `data/qualifications/` | Parsed official qualification data |
| `data/assessment/` | Project-authored task bank and rubric |
| `data/demo/` | Synthetic workers and simulation datasets (all labelled) |
| `scripts/` | Ingestion and synthetic-data generators |
| `docker/pg-embedded/` | Zero-install local PostgreSQL |
| `docs/` | Documentation set (see below) |

## Setup

Prerequisites: **Python 3.12+**, **Node.js 20+**. PostgreSQL is optional, because the repo ships an embedded one.

```bash
# 1. Database: PostgreSQL 18 on :5433 (user/password rpl/rpl, databases rpl_sahayak + rpl_sahayak_test)
npm --prefix docker/pg-embedded install
node docker/pg-embedded/start.mjs --test-db         # leave running

# 2. Backend
python -m venv backend/.venv
backend/.venv/Scripts/pip install -r backend/requirements.txt     # macOS/Linux: backend/.venv/bin/pip
cd backend && .venv/Scripts/alembic upgrade head && cd ..
cd backend && .venv/Scripts/python -m app.seed --demo && cd ..   # official data + task bank + demo accounts/workers
backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000

# 3. Frontend
npm --prefix frontend install
npm --prefix frontend run dev                         # http://localhost:3000
```

To use your own PostgreSQL instead, set `DATABASE_URL`. API docs are at http://localhost:8000/docs.

### Environment variables (backend, via `backend/.env` or the environment)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://rpl:rpl@localhost:5433/rpl_sahayak` | Database |
| `JWT_SECRET` | dev-only value | **Set a random value of 32+ characters outside development** |
| `JWT_EXPIRY_MINUTES` | `480` | Session length |
| `CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000"]` | Frontend origins |
| `AI_PROVIDER` | `mock` | `mock` (deterministic rules), `gemini` or `openai` |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | — / `gemini-2.5-flash` | Gemini provider |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | — / `gpt-4o-mini` | OpenAI provider |
| `AI_SEND_EVIDENCE` | `false` | Allow sending evidence media to the AI provider |
| `AI_TIMEOUT_SECONDS` | `30` | Provider timeout |
| `STORAGE_DIR` / `MAX_UPLOAD_MB` | `backend/storage` / `15` | Evidence storage |
| `COMPETENCY_REQUIRED_PCT` | `60` | QF DGT/1001 §23 |
| `LO_COVERAGE_REQUIRED` | `0.70` | NCVET RPL §6.2(c) |
| `MATCH_W_SKILL` … `MATCH_W_ELIGIBILITY` | 0.40/0.25/0.15/0.10/0.10 | Mapping weights |
| `DEMO_MODE_ENABLED` | `true` | **Set `false` in any real deployment** (disables `/demo` endpoints) |
| `RATE_LIMIT_LOGIN` / `RATE_LIMIT_AI` | `10/minute` / `30/minute` | Rate limits |

Frontend: `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000/api/v1`). API keys never go to the frontend.

### AI provider setup

The default `mock` provider uses the deterministic rule engine, so everything works with no keys and no internet.
For a real model:

```bash
backend/.venv/Scripts/pip install -r backend/requirements-ai.txt
```

Then set `AI_PROVIDER=gemini` and `GEMINI_API_KEY=…` (or the OpenAI equivalents). Every response is validated against
a Pydantic schema. If validation fails, the call is retried once and then falls back to the rules; the fallback is shown in the UI.

### Dataset setup

The official data is already parsed in `data/qualifications/`. To regenerate:

```bash
backend/.venv/Scripts/pip install -r backend/requirements-scripts.txt
backend/.venv/Scripts/python scripts/ingest_official_qualifications.py   # from data/sources/*.pdf
backend/.venv/Scripts/python scripts/generate_demo_data.py               # synthetic workers (fixed seed)
backend/.venv/Scripts/python scripts/generate_consistency.py             # simulation ratings (fixed seed)
cd backend && .venv/Scripts/python -m app.seed --reset-demo
```

## Demo

**Accounts.** All of them are synthetic, for the prototype only.

| Role | Login | Password |
|---|---|---|
| Administrator | `admin@demo.rpl` | `demo1234` |
| Assessors A01–A05 | `assessor1@demo.rpl` … `assessor5@demo.rpl` | `demo1234` |
| Workers (40 synthetic) | mobile from `data/demo/workers.csv`, e.g. Raj Kumar `9000100001` | PIN `1234` |

**Demo workflow.** Open http://localhost:3000/demo, the presenter console. Each step resets the synthetic worker
**Raj Kumar** to a checkpoint and signs in as the right person in one click:

1. **Fresh profile** (worker): declare experience → extracted skills → Electrician match with LO trace →
   self-assessment.
2. **Practical** (worker): guided tasks and evidence, including the offline demo below.
3. **Evidence ready** (assessor A01): AI observations next to the 0–4 rubric → score.
4. **Awaiting decision** (assessor A01): recommendation with its rules → final decision → PDF report.
5. **Consistency analytics** (assessor), then the **admin** overview and audit log.

**Offline demo.** In the worker app, tap the *✓ Synced* chip and choose *Offline* (demo network mode), then do some work:
profile edits, task steps, photos. The chip counts the queued items. Press *Reconnect & Sync* and the queue replays in
order and exactly once. Real offline mode (turning off the network in DevTools) works the same way; the service worker caches
the app shell in production builds (`npm run build && npm start`). See [docs/offline-sync.md](docs/offline-sync.md).

## Tests

```bash
backend/.venv/Scripts/python -m pytest backend -q       # 144 tests, ~95 % coverage, test DB, no AI keys
npm --prefix frontend test                              # Vitest: sync queue, i18n, workflow
npm --prefix frontend run lint
```

Details and the manual browser checks: [docs/testing.md](docs/testing.md).

## Implemented, simulated and future scope

| Area | Status |
|---|---|
| Worker registration, profile, experience (text + voice), EN/HI | Implemented |
| AI skill extraction with worker confirmation | Implemented (rules by default; Gemini/OpenAI adapters, not tested against live keys) |
| Qualification mapping against official LO text, with trace | Implemented (Electrician + Wireman) |
| Self-assessment, readiness (> 70 %), guided tasks, evidence upload | Implemented |
| AI evidence analysis | Implemented as quality/completeness checks; image *content* needs a real model + `AI_SEND_EVIDENCE` |
| Rubric scoring, competency profile, gaps, recommendation, decision, PDF report | Implemented |
| Offline PWA + sync | Implemented (queue/sync tested; service worker not yet verified in desktop Chrome) |
| Assessor allocation, dashboards, admin, audit log | Implemented |
| Assessor consistency analytics | Implemented; runs on a **labelled simulation** dataset |
| Demo workers, evidence images, prepared AI observations | **Synthetic**, labelled everywhere |
| Integration with Skill India Digital / NCVET certification, Aadhaar/DigiLocker | Future scope |
| More trades; real assessor rating study; proctoring / live video assessment | Future scope |

## Limitations

- This is a prototype. It is not affiliated with or approved by NCVET, DGT or MSDE, and its outputs are not certifications.
- Only 8 of the 30 Electrician trade LOs are covered by practical tasks. The other 22 are shown as "not assessed in prototype".
- The task bank, rubric anchors, safety-gate rule and AI evidence thresholds are project-authored design choices
  ([assessment-rubric.md](docs/assessment-rubric.md)).
- The consistency results come from a simulation. The improvement they show is an assumption built into the simulation, not a measured result.
- The PDF report uses a Latin font, so Hindi text is replaced by a note. The web app shows Hindi in full.
- Answers from real LLM providers have not been tested with live keys. The rule fallback is what has been tested.
- The service-worker app-shell cache has not been verified in desktop Chrome, because the embedded test browser blocks service-worker registration.

## Documentation

| Document | |
|---|---|
| [project-blueprint.md](docs/project-blueprint.md) | Scope, users, workflow, design decisions |
| [architecture.md](docs/architecture.md) | Components, data flow, data model, security |
| [methodology.md](docs/methodology.md) | Every formula and threshold, with its source |
| [assessment-rubric.md](docs/assessment-rubric.md) | 0–4 scale, tasks, criteria and anchors |
| [ai-human-boundary.md](docs/ai-human-boundary.md) | What the AI may and may not do |
| [dataset.md](docs/dataset.md) | Official, project-authored, synthetic and simulation data |
| [sources.md](docs/sources.md) | Official sources, hashes, fields used |
| [offline-sync.md](docs/offline-sync.md) | Offline model and sync protocol |
| [testing.md](docs/testing.md) | Test suites and manual checks |
| [requirements-traceability.md](docs/requirements-traceability.md) | Requirement → implementation → test |
