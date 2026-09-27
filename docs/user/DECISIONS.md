# CourseMind — Decisions

One entry per decision made during the build, newest at the bottom. Decisions made before the build live in PRD, TRD, and the other approved docs; this log records what changes or gets settled after that.

**Entry format**

```
## YYYY-MM-DD — Short title
**Context:** what forced a choice
**Decision:** what we chose
**Why:** the deciding reason (numbers if any)
**Affects:** files / docs updated
```

---

## 2026-09-27 — Docs split into docs/app and docs/user
**Context:** The owner moved the docs into `docs/app/` (product and technical specs) and `docs/user/` (constraints, decisions, handover, private build plan). Step 1's `.gitignore` still pointed at `docs/CourseMind_build_plan.md`, so the private plan would have been committed.
**Decision:** Keep the split. Ignore the exact path `docs/user/CourseMind_build_plan.md`. Fix relative links in IMPLEMENTATION_PLAN. Add a root `CLAUDE.md` that declares `Tier: full` and lists where the docs live.
**Why:** The owner prefers the split and chose the exact-path ignore. Full tier matches the doc set already in place.
**Alternatives:** Ignore the file by name anywhere (survives future moves; not chosen). Flatten back to `docs/` (not chosen).
**Affects:** `.gitignore`, `CLAUDE.md`, IMPLEMENTATION_PLAN (links, `.gitignore` snippet, step 1 check), CONSTRAINTS (path), ARCHITECTURE (folder table).

## 2026-09-27 — pytest.ini for the import path
**Context:** `pytest -q` from `backend/` could not import `app` (pytest puts `tests/` on `sys.path`, not `backend/`).
**Decision:** Add `backend/pytest.ini` with `pythonpath = .`.
**Why:** One line of config. No `conftest.py` hacks and no package install. Later steps can register the `live` marker in the same file.
**Affects:** `backend/pytest.ini`, ARCHITECTURE.

## 2026-09-27 — httpx2 for the test client
**Context:** Starlette 1.7's `TestClient` warns "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead." It imports `httpx2` first and falls back to `httpx`.
**Decision:** Replace `httpx` with `httpx2==2.13.1` in `requirements-dev.txt` (owner approved).
**Why:** Removes the deprecation warning and follows Starlette's supported path.
**Note:** `httpx` is still installed as a transitive dependency of `langchain-core` (via `langchain-text-splitters`). That is expected; it is no longer pinned directly.
**Affects:** `backend/requirements-dev.txt`.

## 2026-09-27 — DOCX and PPTX parsing details
**Context:** TRD §7.2 sets the section rules but not how headings, empty parts, and merged table cells appear in the text.
**Decision:**
- A DOCX section's text starts with its heading line, so a chunk from the top of a section carries the heading words.
- `§ (start)` is emitted only when there is text before the first heading. Headings are whitespace-collapsed in `location`, and `location` is cut to 120 chars (BACKEND_SCHEMA §4).
- Merged table cells appear once. python-docx repeats a horizontally merged cell per grid column, so repeats are dropped by identity; python-pptx gives covered cells as empty `is_spanned` placeholders, which are skipped. Empty cells that are not merged stay, so columns stay aligned with the header row. Rows with no text are dropped.
- PPTX: one section per slide even when empty (like PDF pages); the chunker drops empty ones. Soft line breaks (`\v`) become `\n`.
**Why:** Better retrieval text and correct table rows for the LLM. Verified on LibreOffice-made files as well as python-docx/python-pptx-built ones.
**Affects:** `backend/app/parsing.py`, `backend/tests/test_parsing.py`.

## 2026-09-27 — Upload validation details
**Context:** BACKEND_SCHEMA §5 has no dedicated code for a ZIP over the 200 MB uncompressed cap, and TRD §7.1 leaves the ZIP-reading failure modes open.
**Decision:**
- Over-cap ZIP → `bad_signature` (415). TRD §7.1 groups the size cap with the signature check, and `file_too_large` would show "larger than 25 MB", which is false for a small bomb.
- The cap uses the declared sizes in the ZIP's central directory. CPython's `zipfile` never inflates an entry past its declared size (`zipfile/__init__.py:1091`), so this also bounds what the parsers can decompress.
- ZIP index read failures map to `bad_signature`: `BadZipFile` and `NotImplementedError` (raised for an unsupported "version needed" field). Both were found by fuzzing 20,000 corrupted DOCX files.
- PDF must start with `%PDF-` at byte 0, as specified. Some real PDFs have junk before the header (the PDF spec allows up to 1 KB); if uploads fail on that, widen the check to the first 1,024 bytes.
**Why:** Keeps the spec's code list unchanged and gives the visitor true error copy.
**Affects:** `backend/app/parsing.py`, `backend/tests/test_parsing.py`.
