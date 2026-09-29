# BUG: app stuck on "Starting server…" for ad-blocker users

**Found:** 2026-09-30 · **Status:** fixed in code, awaiting deploy

## Problem
On `https://coursemind-app.netlify.app` the header stayed on "Starting server…" and the banner "The server is starting. This can take up to a minute." never cleared. Upload and ask stayed disabled. The console filled with "Failed to load resource" errors, one every 3 s.

## Cause
The EasyPrivacy filter list contains the rule `||onrender.com/health`. It blocks every script request (fetch/XHR) to any `*.onrender.com/health…` URL; typing the URL into the address bar is not blocked. EasyPrivacy is a default list in uBlock Origin and uBlock Origin Lite and is also used by AdGuard and Brave. The frontend's server check called `GET /health`, so for those users it failed forever.

Evidence (owner's Chrome, uBlock Origin Lite 2026.926.2202):
- `fetch('https://coursemind-api.onrender.com/health')` failed in 1–2 ms, even with `mode: 'no-cors'` and even from a same-origin page; opening the URL directly returned `{"status":"ok"}`.
- Blocked: `/health`, `/health/`, `/healthz`, `/healthcheck`, `/Health`, and `attendify-x39n.onrender.com/health`. Passed: `/status`, `/ping`, `/api/health`, `/documents`, and `/health` on other domains.
- The rule is in the extension's `rulesets/main/easyprivacy.json` (`"urlFilter": "||onrender.com/health"`). No list mentions `coursemind`.
- Render logs showed no request from the owner's browser while the banner was up; the server was up the whole time.

## Change
- Backend (`app/main.py`): the health handler is registered on both `/health` and `/status` (GET and HEAD).
- Frontend (`lib/api.ts`): the server check calls `/status`.
- `/health` stays for Render's health check and UptimeRobot (server-side, no ad blocker).
- Docs: BACKEND_SCHEMA, TRD, APP_FLOW, ARCHITECTURE, DECISIONS.

## How it was tested
- `backend`: `pytest -q` → 114 passed (health tests run for both paths, GET, HEAD and 503).
- `frontend`: `npm test` 10/10, `tsc --noEmit` clean, `eslint` clean, `next build` OK.
- Local preview (static build + local backend): the page called `GET /status` → 200 and the header showed "Connected".
- Still to do after deploy: end-to-end run in the owner's Chrome with uBlock Origin Lite on.

## Roll back
Revert the commit. The frontend goes back to `/health` (broken for ad-blocker users again); the extra backend path is harmless on its own.
