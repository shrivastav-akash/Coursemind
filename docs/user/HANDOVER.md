# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-30
**Step:** 17 — Deploy: **done** (Milestone B is live)
**Status:** `34552a6` live: the browser's server check uses `/status` (EasyPrivacy blocks `onrender.com/health`); `/health` answers HEAD. End-to-end run passed in the owner's Chrome with uBlock Origin Lite on (BUG-health-blocked-by-easyprivacy). Uncommitted: these doc updates.

## Live
- Frontend `https://coursemind-app.netlify.app` (public; previews team-only).
- Backend `https://coursemind-api.onrender.com` (Render, Oregon, free; UptimeRobot every 5 min).

## Verified (DECISIONS, 2026-09-28 and 2026-09-29)
- Fresh browser: samples, upload through the UI, cross-document answer citing the upload and the samples, citation opens the evidence, refusal.
- Rate limits hold against forged headers (429 on the 6th call); CORS is locked to the Netlify origin.
- Latency: server-side retrieval 71–86 ms, first answer piece about 0.25 s after the LLM call, full answer 0.9–1.1 s.

## Pending
- Hydration error #418 in the live console: being fixed in a separate session.
- **Owner:** delete the 3 leftover sample documents (46 chunks, from a lost test workspace)? Claude can do it through the API once approved.
- A frontend-only env change needs Netlify "Trigger deploy": builds are skipped when `frontend/` didn't change.
- The Render free-hours risk is shared with WhatHotel and attendify-backend (owner accepted).

## Next step
- Step 18 — README and results: pitch, screenshot/GIF, architecture diagram, eval table from `eval/results.md`, the measured latency above (plus a 50-page ingest measurement), running locally, limits, and "don't upload private documents"; tick PRD §10 metrics with real numbers.
