# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-28
**Step:** 17 — Deploy (live; verification part 1 done, part 2 waits on one push)
**Status:** `7969e15` is deployed. Uncommitted: the rate-limit key fix (`CF-Connecting-IP`), its test, and docs.

## Live
- Backend `https://coursemind-api.onrender.com` (Render, Oregon, free). `/health` is 200.
- Frontend `https://coursemind-app.netlify.app` (Netlify). Now public; previews stay team-only.

## Verified (see DECISIONS, 2026-09-28)
- API end to end: samples, upload, cross-document answer with citations, refusal.
- Latency: server-side retrieval 71–86 ms; full answer 0.9–1.1 s.
- CORS locked to the Netlify origin.

## Fixed, not yet deployed
- Rate limits keyed on `CF-Connecting-IP`, because a forged `X-Forwarded-For` bypassed them live.
- Netlify `NEXT_PUBLIC_API_URL` re-added. The live build still calls `localhost:8000` until the next build.

## Owner actions
1. Commit and push the fix. Both Render and Netlify auto-deploy from `main`, and that push also rebuilds Netlify with the API URL.
2. Confirm the UptimeRobot monitor on `https://coursemind-api.onrender.com/health` (every 5 min).

## Then Claude verifies (part 2)
- The forged-header rate-limit test gives 429 on the 6th call.
- In a fresh browser on the Netlify site: samples, upload, cross-document answer, citation, refusal.
- UptimeRobot is green.

## Known issues / risks
- Render free hours are shared with WhatHotel and attendify-backend (owner accepted the risk).
- httpx INFO logs print the Qdrant host on every call (host only, no key). They are noisy; lower the level if wanted.
- Small eval corpus; Firefox has no `field-sizing: content`.

## Next step
- Finish step 17 part 2, then step 18 (README and results).
