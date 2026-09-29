# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-30
**Step:** 17 — Deploy: **done** (Milestone B is live)
**Status:** `/health` answers HEAD (live since 18:53 UTC 2026-09-29). Uncommitted: the browser's server check moved to `/status` because EasyPrivacy blocks `onrender.com/health` (BUG-health-blocked-by-easyprivacy). Tests: backend 114 passed, frontend 10/10, build OK. Not deployed yet.

## Live
- Frontend `https://coursemind-app.netlify.app` (public; previews team-only).
- Backend `https://coursemind-api.onrender.com` (Render, Oregon, free; UptimeRobot every 5 min).

## Verified (DECISIONS, 2026-09-28 and 2026-09-29)
- Fresh browser: samples, upload through the UI, cross-document answer citing the upload and the samples, citation opens the evidence, refusal.
- Rate limits hold against forged headers (429 on the 6th call); CORS is locked to the Netlify origin.
- Latency: server-side retrieval 71–86 ms, first answer piece about 0.25 s after the LLM call, full answer 0.9–1.1 s.

## Pending
- **Owner:** commit and push the `/status` fix (backend and frontend in one push; Netlify rebuilds because `frontend/` changed). Then Claude runs the full end-to-end test in the owner's Chrome with uBlock Origin Lite on.
- Hydration error #418 in the live console: being fixed in a separate session.
- **Owner:** delete the 3 leftover sample documents (46 chunks, from a lost test workspace)? Claude can do it through the API once approved.
- A frontend-only env change needs Netlify "Trigger deploy": builds are skipped when `frontend/` didn't change.
- The Render free-hours risk is shared with WhatHotel and attendify-backend (owner accepted).

## Next step
- Step 18 — README and results: pitch, screenshot/GIF, architecture diagram, eval table from `eval/results.md`, the measured latency above (plus a 50-page ingest measurement), running locally, limits, and "don't upload private documents"; tick PRD §10 metrics with real numbers.
