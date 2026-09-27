# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-27
**Step:** 5 — Qdrant spike (decision gate)
**Status:** done, gate passed; awaiting owner review (not committed)

## Changed
- `qdrant-client==1.19.1` pinned in `requirements.txt`.
- `backend/scripts/spike_qdrant.py` (run: `cd backend && .venv/bin/python -m scripts.spike_qdrant [pdf]`). It uses random-suffix throwaway collections and deletes them in `finally`.
- Results and gate decision in DECISIONS.md: `hybrid_rerank` median 717–774 ms, 50-page ingest ~23 s. The TRD design is kept.

## Verified
- Two full runs; both print `Cleanup: done` (no spike collections left on the cluster).
- Chunks schema from BACKEND_SCHEMA §4 (dense 384 cosine, BM25 sparse with IDF, ColBERT multivector MAX_SIM with `m=0`, on-disk, float16) is accepted by the cluster, and all three Cloud Inference models work on the free tier.
- Payload-only collection (`vectors_config={}`) works for the `documents` registry.

## Pending
- **Owner decision: cluster region.** The cluster is in AWS `sa-east-1` (São Paulo); Render has no South American region. The cluster is empty, so switching is cheap now and costly later. See the chat for options.
- Owner OK, then commit: `feat: Qdrant spike`.
- `backend/.env` is mode 664 (group-readable); `chmod 600 backend/.env` is safer.
- Secrets are not required at startup yet. Add a fail-fast check in step 6 (Qdrant) and step 8 (Groq).

## Known issues
- Latency numbers were measured from India, not from Render. Re-measure from the deployed service in step 17.

## Next step
- Step 6 — Collections and document registry (`store.py`, startup lifespan, `/health` pings Qdrant, `live`-marked tests). Starts after the region decision and owner review.
