# CourseMind — Architecture

Living map of the code. **Update this file whenever a folder, module, or connection is added or changes.** Status: `planned` = not built yet, `exists` = in the repo.

_Last updated: 2026-09-27 (step 2: PDF parser and chunker)_

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
| `backend/app/main.py` | FastAPI app, CORS, routes, error bodies, rate limiter, job queue | exists: CORS + `GET /health` (routes in steps 9, 10) |
| `backend/app/config.py` | Env vars, limits, fixed ids, model names | exists |
| `backend/app/schemas.py` | Pydantic models | exists |
| `CLAUDE.md` | Tier, doc locations, commands for AI sessions | exists |
| `backend/requirements.txt`, `requirements-dev.txt` | Pinned runtime / dev dependencies | exists |
| `backend/pytest.ini` | Puts `backend/` on the import path for tests | exists |
| `backend/.env.example` | Env var names, no secrets | exists |
| `backend/app/parsing.py` | Type detection, parsers, chunking | exists: `parse_pdf`, `chunk_sections` (DOCX/PPTX step 3, type checks step 4) |
| `backend/app/store.py` | Qdrant collections, registry, ingest, retrieval, delete | planned (steps 6–7) |
| `backend/app/llm.py` | Prompt, Groq streaming, rate-limit handling | planned (step 8) |
| `backend/tests/` | Offline tests + `live`-marked tests | exists: `test_api.py`, `test_parsing.py` |
| `backend/scripts/spike_qdrant.py` | One-off performance spike | planned (step 5) |
| `backend/samples/` | 3 publishable sample files | planned (step 15, owner provides) |
| `backend/eval/` | `qa.json`, `run_eval.py`, `results.md` | planned (step 16) |
| `frontend/app/` | `layout.tsx`, `page.tsx` | planned (step 11) |
| `frontend/components/` | `Library.tsx`, `Chat.tsx`, `Answer.tsx`, shadcn `ui/` | planned (steps 11–13) |
| `frontend/lib/` | `api.ts`, `types.ts`, `workspace.ts`, `limits.ts`, `samples.ts` | planned (steps 12, 15) |
| `frontend/netlify.toml` | Build settings | planned (step 17) |

## External services

| Service | Used for | Config (env) |
|---|---|---|
| Qdrant Cloud (free) | Storage, embeddings, hybrid search, re-rank | `QDRANT_URL`, `QDRANT_API_KEY` |
| Groq (free) | Answer generation | `GROQ_API_KEY`, `LLM_MODELS` |
| Render (free) | Backend hosting | Render env vars |
| Netlify (free) | Frontend hosting | `NEXT_PUBLIC_API_URL` |
| UptimeRobot (free) | Keep-alive + downtime email | Monitor URL |
