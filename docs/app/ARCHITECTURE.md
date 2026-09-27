# CourseMind — Architecture

Living map of the code. **Update this file whenever a folder, module, or connection is added or changes.** Status: `planned` = not built yet, `exists` = in the repo.

_Last updated: 2026-09-27 (step 13: thread and streaming answers)_

## How the pieces connect

```
 Browser
   │  Next.js static site (Netlify CDN)
   │  sends X-Workspace-Id on every call
   ▼
 FastAPI backend (Render, one process)
   ├─ main.py ──── routes, validation, rate limits, SSE
   ├─ parsing.py ─ file type checks; PDF / DOCX / PPTX → sections
   ├─ store.py ─── Qdrant: registry, ingest worker, retrieval ──────► Qdrant Cloud
   │                                                                  (documents, chunks;
   │                                                                   embeddings + re-rank
   │                                                                   run inside Qdrant)
   └─ llm.py ───── prompt, streaming, model fallback ───────────────► Groq API
 UptimeRobot ── GET /health every 5 min ──► backend ──► Qdrant (keeps both awake)
```

**Upload:** browser → `POST /documents` → validate → temp file → 1-worker queue → parse → chunk → upsert text to Qdrant (Qdrant embeds) → record `ready` → browser polls `GET /documents`.

**Ask:** browser → `POST /ask` → one Qdrant query (dense + BM25 → RRF → ColBERT re-rank, filtered to the workspace's ready docs) → prompt → Groq stream → SSE `sources`, `token`…, `done` → browser renders citations.

Data shapes and endpoint details: [BACKEND_SCHEMA.md](BACKEND_SCHEMA.md). Design reasons: [TRD.md](TRD.md).

## Folder structure

| Path | Purpose | Status |
|---|---|---|
| `docs/app/` | PRD, TRD, APP_FLOW, UI_UX_BRIEF, BACKEND_SCHEMA, IMPLEMENTATION_PLAN, this file | exists |
| `docs/user/` | CONSTRAINTS, DECISIONS, HANDOVER; private `CourseMind_build_plan.md` (git-ignored) | exists |
| `backend/app/main.py` | FastAPI app, CORS, routes, error bodies, rate limiter, job queue | exists: CORS, lifespan (fails without settings, clears `/tmp/coursemind`, then `store.ping()`), error table + handlers, `X-Workspace-Id` and Qdrant-ready dependencies, rate limiter, 1-worker ingest queue, `GET /health`, `GET/POST /documents`, `DELETE /documents/{doc_id}`, `POST /ask` (SSE via `answer_events`) (samples in step 15) |
| `backend/app/config.py` | Env vars, limits, fixed ids, model names | exists |
| `backend/app/schemas.py` | Pydantic models | exists |
| `CLAUDE.md` | Tier, doc locations, commands for AI sessions | exists |
| `backend/requirements.txt`, `requirements-dev.txt` | Pinned runtime / dev dependencies | exists |
| `backend/pytest.ini` | Puts `backend/` on the import path for tests | exists |
| `backend/.env.example` | Env var names, no secrets | exists |
| `backend/app/parsing.py` | Type detection, parsers, chunking | exists: `detect_type`, `parse`, `parse_pdf`, `parse_docx`, `parse_pptx`, `chunk_sections`, `UploadError` |
| `backend/app/store.py` | Qdrant collections, registry, ingest, retrieval, delete | exists: `ensure_ready`, `ping`, `ensure_collections`, `sweep_interrupted`, registry CRUD, `count_documents`, `count_chunks`, `ingest`, `retrieve` (3 modes), `delete_document` |
| `backend/app/llm.py` | Prompt, Groq streaming, rate-limit handling | exists: `build_prompt`, `stream_answer` → `(model, pieces)`, `LLMError(code)`, daily-exhausted flags |
| `backend/tests/` | Offline tests + `live`-marked tests | exists: `test_api.py`, `test_parsing.py`, `test_store.py`, `test_llm.py`, `test_documents_api.py` (routes with an in-memory fake store), `test_ask_api.py` (SSE with faked store + LLM), `test_store_live.py`, `test_ingest_live.py`, `test_llm_live.py` (`live` marker, skipped without the service's settings); `files.py` shared test-file builders |
| `backend/scripts/spike_qdrant.py` | One-off performance spike (`python -m scripts.spike_qdrant`) | exists |
| `backend/samples/` | 3 publishable sample files | planned (step 15, owner provides) |
| `backend/eval/` | `qa.json`, `run_eval.py`, `results.md` | planned (step 16) |
| `frontend/app/` | `layout.tsx` (fonts, viewport, TooltipProvider, Toaster), `page.tsx` (renders `Workspace`), `globals.css` (UI_UX_BRIEF tokens, row-flash keyframes) | exists |
| `frontend/components/` | `workspace-provider.tsx` (client state: health, library, uploads, polling, delete dialog, drag and drop, announcements), `workspace.tsx` (layout), `app-header.tsx` (status + mobile sheet), `server-banner.tsx`, `library.tsx`, `first-visit.tsx`, `question-box.tsx` (draft, counter, Enter/Shift+Enter, send/Stop), `guarded-button.tsx`, `file-name.tsx`; `thread-provider.tsx` (turns, streaming, stop, retry, answer errors), `thread.tsx`, `answer.tsx` (progress, parsed answer, citations, sources); shadcn `ui/` | exists |
| `frontend/lib/` | `api.ts` (typed calls, `ApiError`, `ask()` SSE reader), `answer-text.ts` (+ `answer-text.test.ts`, `npm test` via `node --test`), `workspace.ts` (UUID v4 in localStorage), `copy.ts` (APP_FLOW §5 strings), `types.ts`, `limits.ts`, `format.ts`, `utils.ts`; `samples.ts` (step 15) | exists |
| `frontend/.env.example` | `NEXT_PUBLIC_API_URL` (baked in at build; default `http://localhost:8000`) | exists |
| `frontend/netlify.toml` | Build settings | planned (step 17) |
| `.claude/launch.json` | Local preview servers: `frontend-static` (`frontend/out` on :3000), `backend` (uvicorn on :8000) | exists |

## External services

| Service | Used for | Config (env) |
|---|---|---|
| Qdrant Cloud (free, AWS `us-west-2` Oregon) | Storage, embeddings, hybrid search, re-rank | `QDRANT_URL`, `QDRANT_API_KEY` |
| Groq (free) | Answer generation | `GROQ_API_KEY`, `LLM_MODELS` |
| Render (free, Oregon) | Backend hosting | Render env vars |
| Netlify (free) | Frontend hosting | `NEXT_PUBLIC_API_URL` |
| UptimeRobot (free) | Keep-alive + downtime email | Monitor URL |
