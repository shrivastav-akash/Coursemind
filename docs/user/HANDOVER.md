# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-27
**Step:** 16 — Evaluation and tuning (Phase 4)
**Status:** done, awaiting owner review (not committed)

## Changed
- `backend/eval/`:
  - `qa.json` (15 questions, 3 two-document with per-part locations, 3 out-of-scope);
  - `run_eval.py` (grid + ratio sweep + `--refusal`);
  - `results.md` (generated from the final run).
- New defaults: `RETRIEVAL_MODE=hybrid`, `CHUNK_SIZE=400`, `TOP_K=4`; `SECOND_DOC_RATIO` stays 0.95. Reasons and numbers are in DECISIONS (step 16).
- `store.py` refactored so the eval reuses production code; the routes are unchanged.
- Suggested question 3 is now a real two-document question (eval q15).
- Answers render `*` inside code correctly, and fenced ``` blocks render as code blocks.

## Verified
- Final eval: `400 hybrid` scored hit@4 15/15, MRR@6 0.956, Both@4 3/3. Refusal check 3/3.
- Crowding check (step 10 files): `hybrid` kept both documents 3/3 at every size.
- Browser on the new defaults: 3 samples Ready (65 passages); the two-document suggestion cited DOCX § 11 and PDF p. 2.
- Tests:
  - Backend: `pytest -m "not live"` 98 passed; live Qdrant tests 8 passed.
  - Frontend: `npm test` 10/10; `tsc`, `eslint` and the build are clean.
- Cluster left empty.

## Pending
- **Owner:**
  - Check the expected locations in `backend/eval/qa.json`, then re-run `.venv/bin/python -m eval.run_eval --refusal` from `backend/`.
  - Confirm `git-cheat-sheet.pdf` may be published before the repo goes public.
- **Owner decision:** answers sometimes add uncited claims beyond the sources (seen: a `*/.env` pattern). The fix is one prompt sentence, but TRD §8.3 holds the approved prompt.
- **Owner decision:** TRD §5 / §8.2 still say `700` / `hybrid_rerank` as defaults (approved doc); DECISIONS records the change. Update the TRD if you want them to match.
- The resume bullet (TRD §17) can't claim a re-rank gain. The measured gain is dense to hybrid on two-document questions (Both@4 2/3 to 3/3; crowding 1/3 to 3/3).
- Step 17 (deploy):
  - Netlify: set `NEXT_PUBLIC_API_URL` (Netlify serves gzip/brotli).
  - Render: Oregon region; set env from `.env.example` (new defaults).
  - Check `X-Forwarded-For`; measure latency from Render.
- Not triggered live (from steps 14–15): "Couldn't load your documents.", the "delete failed" toast, the 28+ disabled samples button.
- Commit (owner): suggested `feat: retrieval evaluation and tuned defaults`.

## Known issues
- The eval corpus is small (65 chunks at 400) and the three files overlap heavily. Modes differ by one or two questions, which is within run-to-run noise.
- Firefox has no `field-sizing: content`, so the question box stays one line and scrolls there.

## Next step
- Phase 5, step 17 — Deploy. **Owner first:** create the public GitHub repo and the Render, Netlify and UptimeRobot accounts.
