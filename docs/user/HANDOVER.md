# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-27
**Step:** 6 — Collections and document registry
**Status:** done, awaiting owner review (not committed)

## Changed
- `app/store.py`: lazy Qdrant client; `ensure_collections()` (`documents` payload-only + `chunks` per BACKEND_SCHEMA §4, payload indexes, idempotent); `sweep_interrupted()`; `ensure_ready()` (setup once per process, under a lock, retried after an outage); `ping()`; registry: `create_document`, `get_document` (None for other workspaces), `list_documents` (newest first), `set_status` (enforces error_code ⇔ failed), `delete_record`.
- `app/main.py`: lifespan fails without Qdrant settings, otherwise tries setup; `/health` → 200 `ok` or 503 `unavailable` with the standard error body.
- Tests: `test_api.py` (health 200/503 with a faked store; startup fails without settings), `test_store.py` (setup once, retry after failure, error_code rule), `test_store_live.py` (`live` marker: idempotent collections, full registry lifecycle, workspace isolation, sweep). `pytest.ini` registers `live`.

## Verified
- `pytest -q` with the cluster → `36 passed` (~22 s); without `QDRANT_URL` → `33 passed, 3 skipped` (~2 s).
- Server with a wrong `QDRANT_URL`: starts, `/health` → 503 `{"code":"unavailable",…}`. With the real URL: 200, log `qdrant ready; 0 interrupted document(s) marked failed`.
- Cluster after tests: collections `chunks`, `documents`; 0 records in each (live tests clean up).

## Pending
- **Reminder (owner asked): recreate the Qdrant cluster near the Render region** before step 15 (samples) or at latest step 17 (deploy). It is in AWS `sa-east-1` (São Paulo) now; Render has no South American region. Recommended: `us-east-1` + Render Virginia, or `ap-southeast-1` + Render Singapore if offered free. Afterwards: update `backend/.env`, re-run `python -m scripts.spike_qdrant` and `pytest -q`.
- Step 9: every route that touches Qdrant must call `store.ensure_ready()` first (e.g., as a FastAPI dependency).
- Owner OK, then commit: `feat: Qdrant collections and document registry`.
- Groq key fail-fast at startup lands in step 8.

## Known issues
- `sweep_interrupted()` is global by design, so running the live tests while a local server is processing an upload would mark that upload `interrupted`.

## Next step
- Step 7 — Ingest and retrieval (`store.ingest`, `store.retrieve` for the three modes, `store.delete_document`; live test proving workspace isolation). No new deps.
