# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-27
**Step:** 13 — Thread and streaming answers (Qdrant moved to Oregon)
**Status:** done, awaiting owner review. **Uncommitted: steps 10–13 and the cross-document fix.**

## Changed
- Qdrant cluster now AWS `us-west-2` (Oregon); Render will be Oregon too (owner). Spike + full suite re-run on it (DECISIONS).
- Step 13: `api.ask()` SSE reader; `lib/answer-text.ts` (citations incl. `【n】`, lists, bold/emphasis) + `answer-text.test.ts` (`npm test`, node:test, 8 tests); `thread-provider.tsx`; answer block, thread, and question box rewritten; caret and source fade-in animations.

## Verified
- Backend: `pytest -q` → 102 passed on the Oregon cluster.
- Frontend: `npm test` 8/8, `tsc --noEmit`, `eslint`, `npm run build` clean.
- Browser against the real stack: cross-document answer citing both files, citation opens the passage, Stop (backend confirms disconnect) and Retry, refusal, no-ready, rate limit (question restored), connection lost, question-box rules, 375 px mobile. Cluster left empty.

## Pending
- Step 14: focus ring (2 px, 2 px offset), 44 px touch targets, focus after a deleted row disappears, sheet/dialog focus return, reduced-motion spinner swap (static Clock + text), keyboard-only and screen-reader pass (J12), Lighthouse (font fallback CLS).
- Step 15: wire "Try sample documents" (inert now), disable at 28+ documents, suggested questions (samples only).
- Step 16: two-document questions in `qa.json`; tune `SECOND_DOC_RATIO`; look at over-cautious refusals and claims beyond the sources (DECISIONS, step 13).
- Step 17: set `NEXT_PUBLIC_API_URL` on Netlify; deploy Render in Oregon; check how Render sets `X-Forwarded-For`; measure latency from Render.
- Owner may want BACKEND_SCHEMA §5 to list `unavailable` on `/documents` and `/ask` (approved doc, not edited).
- Commits (owner).

## Known issues
- Model uses Markdown and sometimes cites once per paragraph; the renderer handles both.
- `pytest -q` spends 1 Groq request per run; use `-m "not live"` for quick runs.
- Firefox has no `field-sizing: content`, so the question box stays one line and scrolls there.

## Next step
- Step 14 — States, accessibility, mobile (**Milestone B** when done). Local run: preview servers `backend` + `frontend-static` (`.claude/launch.json`), rebuild the frontend first.
