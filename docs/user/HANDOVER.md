# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-27
**Step:** 17 — Deploy (in progress: config ready, waiting on owner actions)
**Status:** not committed. The step 16 follow-up (evidence scoring, 700 defaults, PRD / TRD / APP_FLOW) and the deploy config are all uncommitted.

## Changed
- `render.yaml` (Blueprint for `coursemind-api`) and `netlify.toml` (base `frontend`), both at the repo root.
- Netlify project `coursemind-app` created. Env `NEXT_PUBLIC_API_URL=https://coursemind-api.onrender.com` (builds). Not linked to GitHub yet.

## Owner actions (in order)
1. Commit and push: step 16 follow-up + deploy config.
2. **Render:** Dashboard → New → Blueprint → repo `shrivastav-akash/Coursemind`. Enter `GROQ_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY` when asked → Apply. If the URL isn't `https://coursemind-api.onrender.com`, tell Claude (the Netlify env var must match).
3. **Netlify:** app.netlify.com/projects/coursemind-app → Project configuration → Build & deploy → Link repository → GitHub → `shrivastav-akash/Coursemind`, branch `main`. Build settings come from `netlify.toml`.
4. **UptimeRobot**, once `/health` is green: HTTP(s) monitor on `https://coursemind-api.onrender.com/health`, every 5 minutes.

## Then Claude verifies
- `/health` is live; CORS from the Netlify origin works.
- `X-Forwarded-For` spoof test (see DECISIONS).
- Done-when in a fresh browser: samples, upload, cross-document answer, citation, refusal.
- Latency from Render (first token, full answer).
- The Netlify site is public: the project was created with team-login protection reported as on, so check that an anonymous visitor isn't blocked.

## Known issues / risks
- Render free hours are shared with WhatHotel and attendify-backend (owner accepted the risk; see DECISIONS).
- Small eval corpus; modes differ within noise.
- Firefox has no `field-sizing: content`.

## Next step
- Finish step 17 verification, then step 18 (README and results).
