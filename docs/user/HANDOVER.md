# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-27
**Step:** 3 — Word and PowerPoint parsers
**Status:** done, awaiting owner review (not committed)

## Changed
- New deps pinned: `python-docx==1.2.0`, `python-pptx==1.0.2`.
- `app/parsing.py`: `parse_docx` (body in order, paragraphs + tables; new section at each `Heading*` / `Title`; `§ (start)` for text before the first heading; tables row by row with ` | `), `parse_pptx` (one section per slide; text frames, tables, nested groups, speaker notes as `Notes: …`; `slide {n}`). Merged-cell handling and other details in DECISIONS.
- `tests/test_parsing.py`: 3 new tests (DOCX headings + table order; DOCX Title + merged cells; PPTX placeholders, soft break, notes, merged table cells, nested groups, empty slide).

## Verified
- `pytest -q` → `9 passed`.
- No `.docx` / `.pptx` exist on this machine (home or system paths), so the "real file" check used LibreOffice-made files: an HTML course note → `notes.docx` (4 sections, headings, list, table with a merged cell: correct), and the 19-page system PDF → `spec.pptx` via Impress PDF import (19 slides, 70 chunks, 112 ms, text correct). Probe files deleted afterwards.
- **Not yet checked:** a real Word/PowerPoint file authored in Microsoft Office. Worth one run when you have one (command below).

```bash
cd backend && .venv/bin/python -c "import sys; from app.parsing import parse_docx, parse_pptx; p=sys.argv[1]; [print(s.location, '|', s.text[:100].replace(chr(10),' / ')) for s in (parse_docx if p.endswith('.docx') else parse_pptx)(p)]" /path/to/file.pptx
```

## Pending
- Owner OK, then commit: `feat: Word and PowerPoint parsers`.
- Secrets (`GROQ_API_KEY`, `QDRANT_*`) are not required at startup yet. Add a fail-fast check when steps 6 and 8 start using them.

## Known issues
- DOCX text in text boxes, headers, footers, and footnotes is not read (TRD scope is the body). Vertically merged cells repeat their text in each row they span.

## Next step
- Step 4 — Upload validation (`detect_type`, `parse` dispatch, `UploadError` codes, ZIP-bomb guard). No new deps. Starts only after owner review.
