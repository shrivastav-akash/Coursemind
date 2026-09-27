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

## 2026-09-27 — Qdrant spike (step 5 gate): keep the TRD design
**Context:** IMPLEMENTATION_PLAN step 5 gate: keep `hybrid_rerank` only if the median query is under 1 s and a 50-page ingest is under 60 s.
**Setup:** `scripts/spike_qdrant.py`, run twice from the owner's machine (India, IST) against the free cluster in AWS `sa-east-1` (São Paulo). The PDF was the first 50 pages of `foo2zjs manual.pdf` → 130 chunks (700/100), upserted in batches of 16 with all three models via Cloud Inference. There were 10 questions per mode, `TOP_K=4`, `PREFETCH_K=20`, and the workspace + doc filter was applied on every prefetch and on the outer query.

| Measure | Run 1 | Run 2 |
|---|---|---|
| Network round trip (`get_collections`, median) | 408 ms | 335 ms |
| Ingest, 50 pages (parse 73 ms + upsert) | 22.9 s | 23.2 s |
| Upsert per 16-chunk batch (median) | 2.66 s | 2.79 s |
| `dense` query (median) | 564 ms | 560 ms |
| `hybrid` query (median) | 584 ms | 567 ms |
| `hybrid_rerank` query (median, max) | 774 ms (922) | 717 ms (818) |
| Payload-only collection (`vectors_config={}`) upsert + retrieve | ok | ok |

**Decision:** Gate passes on both runs. Keep `RETRIEVAL_MODE=hybrid_rerank` and `PREFETCH_K=20`.
**Why:** 717–774 ms < 1 s and ~23 s < 60 s, measured with the worst-case network path (India ↔ São Paulo). Roughly 335–408 ms of each query is network round trip, so the Qdrant-side cost of `hybrid_rerank` is about 0.4 s (an estimate: query time minus measured round trip).
**Open:** Render has no South American region (Oregon, Ohio, Virginia, Frankfurt, Singapore). The cluster region vs Render region choice is pending with the owner (see HANDOVER).
**Affects:** `backend/scripts/spike_qdrant.py`, `backend/requirements.txt` (`qdrant-client==1.19.1`), ARCHITECTURE.

## 2026-09-27 — Qdrant region kept for now
**Context:** The step 5 spike showed the cluster is in AWS `sa-east-1` (São Paulo), and Render has no South American region.
**Decision:** Keep the current cluster during development. Recreate it near the chosen Render region before deploy (owner asked to be reminded; tracked in HANDOVER).
**Why:** The cluster is still cheap to replace, and development latency is acceptable (the gate passed from India).
**Alternatives:** AWS `us-east-1` + Render Virginia (recommended), or `ap-southeast-1` + Render Singapore if the free tier offers it.
**Affects:** HANDOVER (pending item), step 17.

## 2026-09-27 — Startup when Qdrant is down; registry details
**Context:** TRD §7.3 runs `ensure_collections()` + the sweep at startup, but APP_FLOW J9 needs the backend to stay up and answer `/health` 503 when the vector store is down. Crashing at boot would also make Render restart-loop during a Qdrant outage.
**Decision:**
- Missing `QDRANT_URL` / `QDRANT_API_KEY` stops startup (config error). An unreachable Qdrant does not: `store.ensure_ready()` runs setup once per process under a lock. It is tried at startup, by `/health`, and (from step 9) before any route that touches Qdrant, so it recovers by itself when Qdrant comes back.
- The sweep always finishes before any request can create a record, so it never marks new work as interrupted.
- `created_at` / `updated_at` use RFC 3339 UTC with microseconds (`2026-09-27T10:15:02.123456Z`). The format is still RFC 3339; the extra precision keeps "newest first" stable for two uploads in the same second. The BACKEND_SCHEMA example shows seconds only and was left unchanged (approved doc).
- Qdrant's `set_payload` removes keys whose value is `None`, so a cleared `error_code` comes back missing. All reads go through one helper that restores `error_code: None`. The live tests caught this.
- An outage logs one warning line without a traceback, because the frontend re-checks `/health` every 3 s.
**Affects:** `backend/app/store.py`, `backend/app/main.py`, tests, ARCHITECTURE.
