# CourseMind — Implementation Plan

**Status:** Draft v1 · **Date:** 2026-09-27 · **Implements:** PRD v2, TRD v1.1, APP_FLOW v1, UI_UX_BRIEF v1, BACKEND_SCHEMA v1

Build order from the smallest working piece to the live app. Each step fits in one session (30–90 min) and ends with something you can run and check.

---

## How every step works

1. Read [HANDOVER.md](../user/HANDOVER.md) and [CONSTRAINTS.md](../user/CONSTRAINTS.md).
2. Do only that step. Anything outside it goes into HANDOVER "Pending".
3. Meet the step's **Done when** list, then:
   - `cd backend && pytest -q` passes (and `npm run build` in `frontend/` once it exists);
   - no secrets in `git status`;
   - [BACKEND_SCHEMA.md](BACKEND_SCHEMA.md) / [ARCHITECTURE.md](ARCHITECTURE.md) updated if a contract or folder changed;
   - new choices logged in [DECISIONS.md](../user/DECISIONS.md);
   - HANDOVER.md filled in;
   - commit, after your OK (`feat:` / `test:` / `docs:` prefixes).
4. Stop. You review before the next step starts.

**You** = actions only you can do (accounts, keys, files, approvals). Everything else is mine.

---

## Overview

| Phase | Steps | Needs from you first | Result |
|---|---|---|---|
| 0 Foundation | 1–4 | Nothing | Repo, backend skeleton, all three parsers, upload validation, all tested offline |
| 1 Retrieval core | 5–7 | Qdrant Cloud free cluster + API key | Documents indexed in Qdrant; hybrid + re-rank search works |
| 2 Backend MVP | 8–10 | Groq API key | **Milestone A:** `curl` uploads a file and streams a cited answer |
| 3 Frontend | 11–14 | Nothing | **Milestone B:** full app working locally in the browser |
| 4 Samples + eval | 15–16 | 3 publishable sample files (PDF, PPTX, DOCX) | Sample button, suggested questions, eval table, tuned defaults |
| 5 Ship | 17–18 | Public GitHub repo; Render, Netlify, UptimeRobot accounts | **Milestone C:** live URL, README with results |

---

## Phase 0 — Foundation (no accounts needed)

### Step 1 — Repo and backend skeleton

**Needs:** nothing. Python 3.12.3, Node 26.9, and git 2.43 are already installed; git user is configured.

**Do**
1. Initialise the repo at `~/Development/Coursemind`:
   ```bash
   git init -b main
   ```
2. Create `.gitignore`:
   ```
   # secrets and local
   .env
   .venv/
   __pycache__/
   *.pyc
   .pytest_cache/
   # frontend
   node_modules/
   .next/
   out/
   # private planning doc (never public, see CONSTRAINTS)
   docs/user/CourseMind_build_plan.md
   ```
3. Create the backend layout and virtual environment:
   ```bash
   mkdir -p backend/app backend/tests
   cd backend
   python3 -m venv .venv          # if this fails: sudo apt install python3.12-venv
   source .venv/bin/activate
   pip install fastapi "uvicorn[standard]" python-dotenv
   pip install pytest httpx
   ```
4. Pin dependencies:
   - `requirements.txt`: exact `==` versions of `fastapi`, `uvicorn[standard]`, `python-dotenv` (read them from `pip freeze`).
   - `requirements-dev.txt`: `-r requirements.txt` plus pinned `pytest`, `httpx`.
5. `backend/.python-version` containing `3.12`.
6. `backend/.env.example` with every variable from TRD §5, secrets empty:
   ```
   GROQ_API_KEY=
   LLM_MODELS=openai/gpt-oss-20b,openai/gpt-oss-120b
   QDRANT_URL=
   QDRANT_API_KEY=
   CHUNK_SIZE=700
   CHUNK_OVERLAP=100
   TOP_K=4
   PREFETCH_K=20
   RETRIEVAL_MODE=hybrid_rerank
   ALLOWED_ORIGINS=http://localhost:3000
   ```
7. `app/__init__.py` (empty).
8. `app/config.py`: load `.env` with `python-dotenv`; read the env vars above with their defaults; define the constants from BACKEND_SCHEMA §2 (`ID_NAMESPACE`, eval workspace id) and §9 (limits), `REFUSAL`, and the three Qdrant model names.
9. `app/schemas.py`: the Pydantic models from BACKEND_SCHEMA §8, copied as written.
10. `app/main.py`: FastAPI app titled "CourseMind"; `CORSMiddleware` using `ALLOWED_ORIGINS` with methods `GET, POST, DELETE`, headers `Content-Type, X-Workspace-Id`, exposed `Retry-After`; `GET /health` returning `Health(status="ok")`. (The Qdrant ping arrives in step 6.)
11. `tests/test_api.py`: `test_health` using `TestClient` expects 200 and `{"status": "ok"}`.
12. `README.md` at repo root: one-line pitch + "Work in progress. See docs/."

**Done when**
- `pytest -q` → `1 passed`.
- `uvicorn app.main:app --reload`, then `curl -s localhost:8000/health` → `{"status":"ok"}`.
- `http://localhost:8000/docs` shows the health route.
- `git status` does not list `.env`, `.venv/`, or `docs/user/CourseMind_build_plan.md`.
- First commit (after your OK): `chore: repo and backend skeleton`.

### Step 2 — PDF parser and chunker

**Adds:** `pypdfium2`, `langchain-text-splitters`; dev-only `fpdf2` (builds test PDFs in code, so no binary fixtures).

**Do**
- `app/parsing.py`: `Section(location: str, order: int, text: str)`; `parse_pdf(path) -> list[Section]` (one section per page, `location = "p. {n}"`); `chunk_sections(sections, size, overlap) -> list[Chunk]` splitting each section separately and dropping whitespace-only pieces.
- `tests/test_parsing.py`: a generated 3-page PDF gives 3 sections with `p. 1`–`p. 3`; long page text splits into several chunks that all keep that page's location; a PDF with no text gives 0 chunks.

**Done when:** tests pass; running `parse_pdf` on any PDF from your machine prints sensible page texts.

### Step 3 — Word and PowerPoint parsers

**Adds:** `python-docx`, `python-pptx`.

**Do**
- `parse_docx(path)`: body in order (paragraphs and tables); new section at each `Heading*` / `Title`; text before the first heading goes to `§ (start)`; tables flattened row by row with ` | `.
- `parse_pptx(path)`: one section per slide; text frames, table cells, grouped shapes (recursive), speaker notes prefixed `Notes:`; `location = "slide {n}"`.
- Tests build small `.docx` / `.pptx` files in code: headings + table → expected sections; slides + table + notes → expected sections.

**Done when:** tests pass; a real `.docx` and `.pptx` from your machine parse into sensible sections.

### Step 4 — Upload validation

**Do**
- `parsing.detect_type(path, filename) -> DocType`, raising `UploadError(code)` with codes from BACKEND_SCHEMA §5:
  - `.pdf` must start with `%PDF-`;
  - `.docx` / `.pptx` must be ZIP with `word/document.xml` / `ppt/presentation.xml`, total uncompressed size ≤ 200 MB;
  - `.doc` / `.ppt` → `legacy_format`; anything else → `unsupported_type`; wrong content → `bad_signature`.
- `parsing.parse(path, type)` dispatching to the three parsers.
- Tests for every code, including a renamed `.txt` → `bad_signature` and a fake ZIP bomb (large declared size) → rejected.

**Done when:** tests pass. **Phase 0 complete:** everything so far runs offline.

---

## Phase 1 — Retrieval core

**You, before step 5:**
1. Create a free cluster at cloud.qdrant.io, in a region close to where the Render service will run (e.g., AWS `eu-central-1` / Render Frankfurt, or both in Singapore if offered).
2. In the cluster's **Inference** tab, confirm `sentence-transformers/all-MiniLM-L6-v2`, `qdrant/bm25`, and `answerdotai/answerai-colbert-small-v1` show **Cost: Free**.
3. Create an API key. Put `QDRANT_URL` and `QDRANT_API_KEY` in `backend/.env` (never in chat or git).

### Step 5 — Qdrant spike (decision gate)

**Adds:** `qdrant-client`.

**Do**
- `backend/scripts/spike_qdrant.py`: creates a throwaway collection with the `chunks` schema (BACKEND_SCHEMA §4); upserts ~150 chunks from a real 50-page PDF with all three models; times the upsert; runs 10 queries in each mode (`dense`, `hybrid`, `hybrid_rerank`) and prints median latency; creates a payload-only collection (`vectors_config={}`) and upserts/reads one record; deletes both collections.

**Done when:** numbers recorded in DECISIONS.md, and the gate decided:
- median `hybrid_rerank` query < 1 s **and** 50-page ingest < 60 s → keep the TRD design;
- otherwise → default `RETRIEVAL_MODE=hybrid` or lower `PREFETCH_K`, logged in DECISIONS.md.

### Step 6 — Collections and document registry

**Do**
- `app/store.py`: `ensure_collections()` (both collections + payload indexes, idempotent); registry functions: create, get, list by workspace (newest first), set status / `error_code` / `chunks`, delete; `sweep_interrupted()`.
- Call both at app startup (FastAPI lifespan). `/health` now pings Qdrant → 503 `unavailable` when unreachable.
- Tests marked `@pytest.mark.live` (run only when `QDRANT_URL` is set) use a unique test workspace id and clean up after themselves.

**Done when:** offline tests pass; live tests pass against your cluster; `/health` returns 503 when `QDRANT_URL` is wrong.

### Step 7 — Ingest and retrieval

**Do**
- `store.ingest(doc)`: parse → chunk → delete existing chunks for `doc_id` → upsert in batches of 16 → mark `ready` with count; `no_text` / `unreadable` failures per TRD §7.2.
- `store.retrieve(question, workspace_id, ready_ids, mode, k) -> list[Source]` for the three modes (TRD §8.2).
- `store.delete_document(...)`: record first, then chunks (BACKEND_SCHEMA §2).
- Live test: ingest a generated PDF whose page 2 is about a unique term; all three modes return a page-2 chunk in the top 4; another workspace id gets nothing.

**Done when:** live tests pass; workspace isolation proven by test.

---

## Phase 2 — Backend MVP

**You, before step 8:** create a Groq API key at console.groq.com and put it in `backend/.env` as `GROQ_API_KEY`.

### Step 8 — LLM module

**Adds:** `langchain-groq`.

**Do**
- `app/llm.py`: `build_prompt(question, sources)` (TRD §8.3); `stream_answer(...)` yielding tokens, with model fallback, per-minute vs daily 429 classification, and daily-exhausted flags (TRD §8.4); raises typed errors mapped to `llm_busy` / `daily_limit` / `llm_error`.
- Unit tests with a fake client: minute-429 on model 1 → model 2 used; daily-429 on both → `daily_limit`; minute + daily → `llm_busy`; flag skips an exhausted model.
- One live smoke test (1 Groq call): streaming works and no reasoning text leaks into the answer (confirms the `include_reasoning` / `reasoning_effort` kwargs). Record the exact kwarg in DECISIONS.md.

**Done when:** unit tests pass; live smoke prints a short streamed answer.

### Step 9 — Document endpoints and worker

**Do**
- `app/main.py`: `X-Workspace-Id` dependency (UUID v4 check); error handler producing `{"code","message"}` bodies; in-memory rate limiter; single-worker job queue.
- Routes: `POST /documents` (full check order from BACKEND_SCHEMA §7), `GET /documents`, `DELETE /documents/{doc_id}`.
- Tests (store faked): every error code on these routes; duplicate upload → 200 with the existing record; failed record → re-queued 202; delete while processing → 409.

**Done when:** tests pass; with the real cluster:
```bash
curl -F file=@notes.pdf -H "X-Workspace-Id: $WS" localhost:8000/documents    # 202 queued
curl -H "X-Workspace-Id: $WS" localhost:8000/documents                         # later: ready, N chunks
```

### Step 10 — Streaming `/ask`

**Do**
- `POST /ask`: 409 `no_ready_documents`, 429 `ask_rate_limited`, then SSE per BACKEND_SCHEMA §7 (`sources` → `token`… → `done` | `error`); refusal without an LLM call when retrieval is empty; stop generating on client disconnect.
- Tests (store + LLM faked): event order; refusal path sends `sources: []` and `done.model = null`; stream error codes pass through; `refused` flag set correctly.

**Done when:** tests pass, and
```bash
curl -N -H "X-Workspace-Id: $WS" -H "Content-Type: application/json" \
  -d '{"question":"What are the conditions for deadlock?"}' localhost:8000/ask
```
streams sources, then a cited answer. **Milestone A reached.**

---

## Phase 3 — Frontend (no accounts needed)

### Step 11 — Next.js shell and design tokens

**Do**
- `npx create-next-app@latest frontend` (TypeScript, App Router, Tailwind, ESLint, no `src/`); `next.config.ts` with `output: 'export'` and `images.unoptimized: true`.
- `npx shadcn@latest init` (Next template; Phosphor icons if offered, otherwise install `@phosphor-icons/react`); add the components listed in UI_UX_BRIEF §6.
- Replace theme tokens with UI_UX_BRIEF §3.1 (light + dark via `prefers-color-scheme`); add `--evidence*` and `--success`; fonts via `next/font/google` (Atkinson Hyperlegible Next + Mono).
- Static layout with placeholder data: header, split view ≥ 1024 px, library sheet below that, first-visit empty state, question box.

**Done when:** `npm run build` produces `out/`; layout matches UI_UX_BRIEF §4.1–4.2 and §4.5 in both color schemes at 320, 768, 1024, and 1440 px.

### Step 12 — Library wired to the API

**Do**
- `lib/workspace.ts`, `lib/api.ts` (typed calls, error bodies), `lib/types.ts`, `lib/limits.ts` (BACKEND_SCHEMA §8–9).
- Health check + server banner + header status (APP_FLOW §2).
- Library: add files (picker + drag and drop), client pre-checks, 2 parallel uploads, polling while queued/processing, all row states, delete with confirmation, duplicate toast, error copy from APP_FLOW §5.

**Done when:** in the browser against the local backend, uploading one valid PDF, DOCX, and PPTX plus one invalid file shows every row state correctly; delete works; reload keeps the library.

### Step 13 — Thread and streaming answers

**Do**
- `ask()` SSE reader (async generator over `fetch`); thread with `MessageScroller`; question bubble; answer block with progress line, streamed text, `[n]` → evidence citation buttons, numbered source list with collapsible passages, Stop / Retry, all stream error codes, refusal hint.

**Done when:** a cross-document question streams with citations to both documents; opening a citation shows the passage; Stop and Retry work; the refusal shows no sources.

### Step 14 — States, accessibility, mobile

**Do**
- Every APP_FLOW §5 state reachable and correct; UI_UX_BRIEF §9 checklist; keyboard-only and screen-reader pass (J12); mobile pass (J11); reduced-motion check.

**Done when:** UI_UX_BRIEF §9 fully ticked in both color schemes. **Milestone B reached.**

---

## Phase 4 — Samples and evaluation

**You, before step 15:** put three files you're allowed to publish in `backend/samples/`: one PDF, one `.pptx`, one `.docx`, ideally on the same course topic (so two-document questions exist).

### Step 15 — Sample documents

**Do**
- `POST /documents/samples` (`is_sample = true`, 202 / 200 per BACKEND_SCHEMA §7); "Sample" badge; "Try sample documents" button; `lib/samples.ts` with 3 suggested questions shown only while every document is a sample.

**Done when:** a fresh browser → Try sample documents → 3 rows reach Ready → a suggested question streams a cited answer.

### Step 16 — Evaluation and tuning

**Do**
- I draft `eval/qa.json` from the sample files (15 questions with expected locations, 3 out-of-scope); **you** check and correct the expected locations.
- `eval/run_eval.py` per TRD §11; `--refusal` flag; writes `eval/results.md`.
- Set `CHUNK_SIZE`, `TOP_K`, `RETRIEVAL_MODE` defaults from the best row.

**Done when:** `results.md` has the full grid; defaults updated; refusal check 3/3 (or the real result, recorded honestly).

---

## Phase 5 — Ship

**You, before step 17:** create a public GitHub repo `shrivastav-akash/coursemind`; create Render, Netlify, and UptimeRobot accounts (free). I don't create accounts or push without your OK.

### Step 17 — Deploy

**Do**
- Push to GitHub (after your OK). Render web service per TRD §12; Netlify site (`frontend`, publish `out`, `NEXT_PUBLIC_API_URL`); set `ALLOWED_ORIGINS` to the Netlify URL; UptimeRobot 5-minute monitor on `/health`.

**Done when:** live site works in an incognito window: samples, upload, cross-document answer, citation, refusal; `/health` monitor green.

### Step 18 — README and results

**Do**
- README: pitch, screenshot/GIF, architecture diagram, evaluation table, measured latency (first token, full answer, 50-page ingest), how to run locally, limits, "don't upload private documents".
- Tick PRD §10 success metrics with real numbers.

**Done when:** a reviewer can understand, run, and judge the project from the README alone. **Milestone C reached.**
