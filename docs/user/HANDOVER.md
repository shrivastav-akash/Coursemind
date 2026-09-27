# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-27
**Step:** 14 — States, accessibility, mobile (**Milestone B reached**: full app working locally)
**Status:** done, awaiting owner review (not committed)

## Changed
- Global focus ring (unlayered CSS), 44 px touch targets on coarse pointers, reduced-motion spinner (static Clock), `--scrim` token for overlays, `aria-hidden` on decorative shadcn icons, focus moves to "Add files" when a focused row disappears, `app/not-found.tsx` (S13).
- LCP fix: static HTML prerendered as a first visit; returning visitors hidden from it by an inline `<head>` script + CSS; library fetched alongside `/health`.

## Verified
- Lighthouse (gzip, local backend): mobile 98 / 100 / 100 (LCP 2.3 s, CLS 0.001), desktop 100 / 100 / 100, dark-mode accessibility 100.
- UI_UX_BRIEF §9 checklist verified item by item (DECISIONS, step 14); keyboard-only pass; dialog and sheet focus behaviour; states `unreadable`, over 25 MB, `interrupted`; 404 page; 320 px dark; reduced motion via headless Chrome.
- `npm test` 8/8, `tsc`, `eslint`, build clean; backend `pytest -m "not live"` 93 passed. Cluster left empty.

## Pending
- Not triggered live: "Couldn't load your documents.", `workspace_full` / `storage_full` rows, "delete failed" toast (see DECISIONS).
- UI_UX_BRIEF §9 boxes are not ticked in the brief itself (approved doc); results are recorded in DECISIONS. Tick them if the owner wants.
- Step 15: owner puts 3 publishable sample files (PDF, PPTX, DOCX, same course topic) in `backend/samples/`; then wire "Try sample documents", disable it at 28+ documents, suggested questions.
- Step 16: two-document questions in `qa.json`; tune `SECOND_DOC_RATIO`; over-cautious refusals and claims beyond sources.
- Step 17: `NEXT_PUBLIC_API_URL` on Netlify (serves gzip/brotli; Lighthouse numbers above assume compression); Render in Oregon; `X-Forwarded-For` check; latency from Render.
- Owner may want BACKEND_SCHEMA §5 to list `unavailable` on `/documents` and `/ask`.
- Commit (owner): suggested `feat: accessibility, states, and first-paint performance`.

## Known issues
- Firefox has no `field-sizing: content`, so the question box stays one line and scrolls there.
- Model output quality items for step 16 (refusals, claims beyond sources).

## Next step
- Phase 4, step 15 — Sample documents. **Owner first:** add three files you may publish to `backend/samples/` (one PDF, one .pptx, one .docx, ideally on the same course topic).
