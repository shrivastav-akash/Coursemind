# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-27
**Step:** 9 — Document endpoints and worker
**Status:** done, awaiting owner review. Steps 7, 8 and 9 are uncommitted; the owner will commit them together.

## Changed
- Step 7: `store.ingest` / `retrieve` / `delete_document`, `RetrievalMode`, `tests/files.py`, `tests/test_ingest_live.py`.
- Step 8: `app/llm.py`, Groq key fail-fast, `langchain-groq==1.1.3`, `tests/test_llm.py`, `tests/test_llm_live.py`.
- Step 9: `app/main.py` (error table + handlers, workspace + Qdrant-ready dependencies, rate limiter, single-worker queue, `GET/POST /documents`, `DELETE /documents/{doc_id}`), `store.count_documents` / `count_chunks`, `python-multipart==0.0.32` (owner approved), `tests/test_documents_api.py` (27 tests with an in-memory fake store).

## Verified
- `pytest -q` → `79 passed` (~62 s); with no keys → `71 passed, 8 skipped` (~2 s).
- Every route error code is covered: 400, 404, 409 ×2, 413 (at cap / just over / Content-Length / chunked), 415 ×3, 422, 429 with `Retry-After`, 503 ×3. Also: duplicate → 200, failed → re-queued 202, other workspace isolated, internal fields (`sha256`, `workspace_id`) never returned, temp files always removed.
- Real server + cluster: PDF (19 pages → 70 chunks, 14.3 s), DOCX and PPTX each reached `ready` via the worker; duplicate → 200 `processing`; fake PDF → 415; 40 MB chunked upload → 413; deletes → 204 then 404; `/tmp/coursemind` empty afterwards; cluster back to 0 records.

## Pending
- **Reminder (owner asked): recreate the Qdrant cluster near the Render region** before step 15 (samples) or at latest step 17 (deploy). It is in AWS `sa-east-1` (São Paulo) now; Render has no South American region. Recommended: `us-east-1` + Render Virginia, or `ap-southeast-1` + Render Singapore if offered free. Afterwards: update `backend/.env`, re-run `python -m scripts.spike_qdrant` and `pytest -q`.
- Step 17: check how Render sets `X-Forwarded-For` (spoofing risk for the rate limiter, see DECISIONS).
- Owner may want BACKEND_SCHEMA §5 to list `unavailable` (503) on the document routes too (approved doc, not edited).
- Step 10: `POST /ask`. Order: workspace → Qdrant ready → `validation_error` (3–500 chars after trimming) → `ask_rate_limited` → `no_ready_documents` → SSE. Send `sources`, then `llm.stream_answer`; map `LLMError.code` to the `error` event; `done.model` = the returned model (null on the no-sources refusal); `refused = answer.strip() == config.REFUSAL`; close the pieces iterator on disconnect.
- Commit (owner): steps 7–9 together.

## Known issues
- An oversized chunked upload is cut off at the app (nothing stored past 25 MB), but uvicorn still reads and discards the rest of the body. Render's proxy limits may cover this; check at step 17.
- Two parallel uploads could both pass the 30-document check and give 31. The frontend sends at most 2 at once, so this is accepted.
- `pytest -q` spends 1 Groq request per run; `-m "not live"` for quick runs.

## Next step
- Step 10 — Streaming `/ask` (SSE). No new deps. Reaching it gives **Milestone A** (curl uploads a file and streams a cited answer).
