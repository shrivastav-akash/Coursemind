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

## 2026-09-27 — Ingest and retrieval details
**Context:** TRD §7.2 / §8.2 define the pipeline. A few boundaries needed settling for step 9.
**Decision:**
- `store.ingest(record, path)` runs the whole worker job (status updates, parse, chunk, clear old chunks, upsert in batches of 16, ready / failed) but **does not delete `path`**. The caller owns the file: upload temp files are deleted by the step 9 worker; sample files in `backend/samples/` must never be deleted.
- Any exception during ingest → partial chunks removed, `failed` / `unreadable`, stack trace logged with the doc id only. If Qdrant itself is down, the final status write can fail too. The exception then reaches the step 9 worker, and the record stays `processing` until the next startup sweep marks it `interrupted`.
- `retrieve(...)` applies `workspace_id AND doc_id IN ready_ids` inside both prefetches and on the outer query, returns `Source` items numbered from 1, and returns `[]` with no Qdrant call when there are no ready ids.
- `RetrievalMode` is one `Literal` in `schemas.py`; `config.py` validates `RETRIEVAL_MODE` against it.
- The live test asserts the target page is the **top-1** result in all three modes (stronger than the plan's "in the top 4", which a 6-page document would pass almost by default).
**Affects:** `backend/app/store.py`, `schemas.py`, `config.py`, tests.

## 2026-09-27 — Groq call settings and the LLM module interface (step 8)
**Context:** TRD §8.4 asked the spike to confirm the reasoning kwarg and the daily-limit wording.
**Findings (live, 2026-09-27):**
- Both `openai/gpt-oss-20b` and `openai/gpt-oss-120b` are listed by the Groq models API for this key.
- **Exact kwarg:** `ChatGroq(..., reasoning_effort="low", model_kwargs={"include_reasoning": False})`. `langchain-groq` 1.1.3 has no `include_reasoning` field; `model_kwargs` passes it through to `groq` 0.37.1 `chat.completions.create`, which accepts it. Groq's docs say it can't be combined with `reasoning_format`; `langchain-groq` always sends `reasoning_format=None`, and Groq accepts that.
- One call each on `gpt-oss-20b`: with `include_reasoning=False`, 0 streamed chunks carried `reasoning_content`, first token 350 ms. Without it, 7 chunks did, first token 513 ms. In neither case did reasoning appear in the answer text (`langchain-groq` keeps it in `additional_kwargs`), so the flag saves tokens and time rather than preventing a leak. These are single samples, not a benchmark.
- The daily token limit's 429 message contains "tokens per day (TPD)"; the daily request limit shows as `x-ratelimit-remaining-requests: 0` (Groq docs: that header always counts requests per day). Classification: daily if either, else per minute.
**Decision:**
- `max_retries=0` (the default of 2 would retry a 429 before falling back to the second model); `timeout=30`.
- `stream_answer(question, sources)` returns `(model, pieces)` only after the first text piece arrives, so every fallback decision happens before anything is streamed. It raises `LLMError` with `daily_limit` / `llm_busy` / `llm_error`. A non-429 failure before the first token is `llm_error` with no fallback (TRD §8.4 step 5). The iterator raises `LLMError("llm_error")` if the stream breaks later, and closing it drops the Groq connection.
- The system prompt builds its refusal sentence from `config.REFUSAL`, so the refusal check in step 10 compares against the same string.
- Startup now also fails without `GROQ_API_KEY`.
**Affects:** `backend/app/llm.py`, `backend/app/main.py`, `backend/requirements.txt` (`langchain-groq==1.1.3`), tests.

## 2026-09-27 — Document endpoints and worker (step 9)
**Context:** BACKEND_SCHEMA §5–7 define the routes, codes and check order. Some implementation choices were left open.
**Decision:**
- **Dependency added (owner approved):** `python-multipart==0.0.32`. FastAPI and Starlette can't parse multipart without it.
- **Error handling:** one `ERRORS` table maps each code to its HTTP status and a fallback message (copy from APP_FLOW). Every route raises `ApiError(code)`, and `UploadError` and FastAPI validation errors are mapped to the same `{code, message}` body. Unknown routes keep FastAPI's default 404.
- **Workspace header:** `X-Workspace-Id` must parse as a UUID with version 4, and it is normalised to canonical lowercase so any accepted spelling maps to one workspace.
- **Qdrant down:** a route that needs Qdrant returns 503 `unavailable` when `store.ensure_ready()` fails. BACKEND_SCHEMA §5 lists `unavailable` only for `/health`; using it on the document routes adds no new code.
- **Upload size cap:**
  - A `Content-Length` over 25 MB + 64 KB is rejected before any of the body is read.
  - Otherwise the body goes through a counting stream into Starlette's `MultiPartParser` (`max_files=1`, `max_fields=0`), which raises 413 the moment the cap is passed, and the exact file size is checked again after parsing.
  - Verified on a real server: a 40 MB chunked upload with no `Content-Length` got 413 and the app stored nothing past the cap. uvicorn still received and discarded the rest of the body, so disk and memory stay bounded but bandwidth does not.
- **Temp files:** uploads go to `/tmp/coursemind/`, and sha256 is computed while writing. `register()` deletes the file unless a job took it, and the worker deletes it in `finally`. Startup empties the folder, because leftovers belong to records the sweep marks interrupted.
- **File names:** client paths are stripped (`C:\Users\me\Lecture 1.pdf` → `Lecture 1.pdf`) and names are capped at 200 chars, keeping the extension.
- **Re-queued failed document:** keeps its original name.
- **Rate limiter:** sliding window per (IP, bucket), in memory. The IP is the first `X-Forwarded-For` entry, as BACKEND_SCHEMA §6 specifies. **Risk to check at deploy (step 17):** if Render appends to a client-sent `X-Forwarded-For` rather than replacing it, the first entry can be spoofed to dodge the limit; then use the entry Render adds.
**Affects:** `backend/app/main.py`, `backend/app/store.py` (`count_documents`, `count_chunks`), `backend/requirements.txt`, `backend/tests/test_documents_api.py`.
