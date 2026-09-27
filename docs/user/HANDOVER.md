# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-27
**Step:** 15 — Sample documents (Phase 4)
**Status:** done, awaiting owner review (not committed)

## Changed
- Backend: `POST /documents/samples` adds the 3 files in `backend/samples/` once per workspace. It returns 202 if anything was queued and 200 if all were already there. It follows the upload limits, and each file is enqueued as a temp copy.
- Frontend:
  - "Try sample documents" is wired, with J2 toasts and a spinner.
  - It is disabled at 28+ documents and while the server isn't ready.
  - 3 suggested questions (`lib/samples.ts`) show while the library holds only samples and one is Ready.
  - Answers render `inline code` in mono.

## Verified
- Real browser, fresh workspace:
  - 3 samples reached Ready (10 / 25 / 11 passages).
  - The two-document suggestion streamed an answer citing the DOCX and the PPTX.
  - A second click gave "already in your library" with no duplicates.
- 375 px has no horizontal scroll.
- Test suites:
  - Frontend: `npm test` 9/9; `tsc`, `eslint` and the build are clean.
  - Backend: `pytest -m "not live"` 98 passed.
- Cluster left empty.

## Pending
- Not triggered live:
  - the 28+ disabled state;
  - `workspace_full` / `storage_full` / rate limit on samples (backend tests cover them);
  - from step 14: "Couldn't load your documents." and the "delete failed" toast.
- **Owner:** the sample files are already committed. Confirm `git-cheat-sheet.pdf` may be published (licence / source) before the repo goes public.
- Step 16: evaluation. Add two-document questions to `qa.json` (the 3 suggestions are a starting point), tune `SECOND_DOC_RATIO`, and review over-cautious refusals and claims beyond the sources.
- Step 17 (deploy):
  - Netlify: set `NEXT_PUBLIC_API_URL` (Netlify serves gzip/brotli).
  - Render: Oregon region.
  - Check `X-Forwarded-For`.
  - Measure latency from Render.
- Owner may want BACKEND_SCHEMA §5 to list `unavailable` on `/documents` and `/ask`.
- Commit (owner): suggested `feat: sample documents and suggested questions`.

## Known issues
- Firefox has no `field-sizing: content`, so the question box stays one line and scrolls there.
- Model output quality items for step 16 (refusals, claims beyond sources).

## Next step
- Phase 4, step 16 — Evaluation.
