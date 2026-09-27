# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-27
**Step:** 4 — Upload validation (Phase 0 complete)
**Status:** done, awaiting owner review (not committed)

## Changed
- `app/parsing.py`: `UploadError(code)`; `detect_type(path, filename) -> DocType` (`.doc`/`.ppt` → `legacy_format`; other extensions → `unsupported_type`; PDF must start with `%PDF-`; DOCX/PPTX must be a readable ZIP containing `word/document.xml` / `ppt/presentation.xml` with declared uncompressed total ≤ 200 MB, else `bad_signature`); `parse(path, doc_type)` dispatch.
- `tests/test_parsing.py`: 17 new parametrized cases: 3 formats detected + parsed (upper-case extensions too); 5 extension rejections; 9 `bad_signature` cases (renamed text, empty files, PDF↔DOCX↔PPTX swaps, corrupt ZIP header, fake ZIP bomb).
- No new dependencies.

## Verified
- `pytest -q` → `26 passed`.
- Mutation check: removing the ZIP-bomb cap, the `NotImplementedError` catch, or the main-part check each makes a test fail.
- Fuzzed 20,000 corrupted DOCX files: `zipfile` only raised `BadZipFile` or `NotImplementedError`, and both are handled.

## Pending
- Owner OK, then commit: `feat: upload validation`.
- Secrets (`GROQ_API_KEY`, `QDRANT_*`) are not required at startup yet. Add a fail-fast check when steps 6 and 8 start using them.

## Known issues
- A ZIP whose index is valid but whose content is corrupt passes `detect_type` and fails later in parsing. The step 7 worker maps that to `unreadable`, as TRD §7.2 specifies.

## Next step
- Phase 1, step 5 — Qdrant spike. **Owner first:** create a free Qdrant Cloud cluster (region near the planned Render region), confirm the three Inference models show "Cost: Free", create an API key, and put `QDRANT_URL` / `QDRANT_API_KEY` in `backend/.env` (never in chat or git).
