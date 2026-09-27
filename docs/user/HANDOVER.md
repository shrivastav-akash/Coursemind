# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-27
**Step:** 2 — PDF parser and chunker
**Status:** done, awaiting owner review (step 1 committed as `2222cb5`; step 2 uncommitted).

## Changed
- Dev test client: `httpx` → `httpx2==2.13.1` (owner approved; see DECISIONS). The Starlette warning is gone.
- New deps pinned: `pypdfium2==5.13.0`, `langchain-text-splitters==1.1.2` (runtime); `fpdf2==2.8.8` (dev, builds test PDFs in code).
- `app/parsing.py`: `Section(location, order, text)`, `Chunk(location, order, chunk_index, text)`, `parse_pdf(path)` (one section per page, `p. {n}`, `\r\n` → `\n`, closes each page after reading), `chunk_sections(sections, size, overlap)` (splits each section separately, drops whitespace-only pieces, `chunk_index` sequential across the document).
- `tests/test_parsing.py`: 5 tests (3 pages → `p. 1`–`p. 3`; long page → several chunks, all `p. 2`, none over `size`; chunks never cross sections; blank PDF → 0 chunks; whitespace-only section → 0 chunks).

## Verified
- `pytest -q` → `6 passed`, no warnings.
- Real PDFs: `shared-mime-info-spec.pdf` → 19 pages, 70 chunks, 28 ms; `foo2zjs manual.pdf` → 93 pages, 242 chunks, 67 ms. Page texts and mid-document chunks read correctly (local machine, not Render).

## Pending
- Owner OK, then commit: `feat: PDF parser and chunker`.
- Secrets (`GROQ_API_KEY`, `QDRANT_*`) are not required at startup yet. Add a fail-fast check when steps 6 and 8 start using them.

## Known issues
- None.

## Next step
- Step 3 — Word and PowerPoint parsers (adds `python-docx`, `python-pptx`). Starts only after owner review.
