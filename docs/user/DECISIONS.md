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

## 2026-09-27 — Streaming /ask (step 10) and Milestone A findings
**Decision:**
- **Before the stream starts:** workspace → Qdrant ready → question validation → rate limit (5/min/IP) → registry read + retrieval → `no_ready_documents`. Any Qdrant failure in that phase is a normal 503 `unavailable`, never a broken stream.
- **Question validation:** `AskRequest` gains `ConfigDict(str_strip_whitespace=True, extra="forbid")`. The "stripped before validation" comment in BACKEND_SCHEMA §8 is now enforced, and unknown keys are rejected. The fields and limits are unchanged.
- **The stream:** `answer_events()` is an async generator: `sources` → `token`… → `done` | `error`. SSE data is `json.dumps`, so a newline inside a piece never breaks the framing.
  - Empty retrieval → refusal token and `done {refused: true, model: null}`, with no LLM call.
  - `refused` is computed as `answer.strip() == config.REFUSAL`.
- **Disconnect:** `pieces.close()` in `finally` drops the Groq connection when the visitor leaves. Verified live: curl left after 1.5 s and the server logged `ask: disconnected` at 1.6 s. A mutation check shows the offline test fails without the close.
- **Logging:** per ask, counts and timings only (sources, pieces, first-piece ms, total ms, outcome). Never the question text, and never the workspace id, since it works as a bearer capability.
**Measured (local machine in India → Qdrant São Paulo → Groq; 4 asks; single samples, not a benchmark):** registry read + retrieval 1.0–2.7 s; first piece at 1.6–3.1 s after the request arrived; full 117-piece answer at 1.75 s total.
**Findings to resolve by step 16 (not changed here; they touch the approved TRD prompt and retrieval design):**
1. **Cross-document answers can fail (PRD G2 / FR-12).** A question joining two unrelated topics ("How does the MIME database weight glob patterns, and what does Banker's algorithm do?") retrieved 4/4, and even 8/8, passages from the larger 70-chunk PDF. Each half on its own retrieves correctly. The model then refused the whole question instead of answering the half it had sources for.
2. The model writes Markdown (`**bold**`, numbered lists) despite "Plain text" in the prompt.
3. It cites once at the end (`[1]`) rather than after every claim.
4. A DOCX Title with no body becomes a chunk containing only the title.
**Frontend note (step 13):** citation markers arrive split across pieces (`[`, `1`, `]`), so parse citations on the accumulated text, not per piece.
**Affects:** `backend/app/main.py`, `backend/app/schemas.py`, `backend/app/llm.py` (return type), `backend/tests/test_ask_api.py`.

## 2026-09-27 — Cross-document fix (owner approved)
**Context:** Step 10 found a two-topic question answered from only the larger document, then refused outright (PRD G2 / FR-12).
**Diagnosis (measured):** The small document's passage *was* a candidate (BM25 rank 8), but ColBERT scores are tightly bunched: it scored 24.6 against the leader's 25.3, and about 20 passages from the 70-chunk PDF sat in between, so `limit=k` dropped it. Dense ranked it 66th of 73. Re-scoring more candidates alone would not help; the ranking itself squeezes it out.
**Decision:**
1. **Retrieval (`hybrid_rerank` only):** re-rank the whole prefetch union (`limit=2×PREFETCH_K`), take the top k, and if all k are from one document while another document's best passage scores ≥ `SECOND_DOC_RATIO` (0.95) × the leader, that passage takes the last slot. Slots 1..k−1 never change, so hit@1..k−1 can't get worse. `dense` / `hybrid` stay unchanged as clean eval baselines.
2. **Threshold data (5 questions, tiny sample):** the second document's best/leader ratio was 0.97–0.98 when it was relevant and 0.90–0.93 when it wasn't. 0.95 splits them and is a constant (`config.SECOND_DOC_RATIO`) to tune in step 16.
3. **Prompt:** "If the sources answer only part of the question, answer that part and say which part your notes don't cover. If the sources contain nothing that answers the question, reply exactly: …" (replaces the all-or-nothing sentence).
4. **Step 16:** `qa.json` gets at least 3 two-document questions, and the eval reports how often both documents reach the top k.
**Verified live (real server, OS notes DOCX + 70-chunk MIME PDF):**
- Two-topic question → sources include `OS_Unit3_Deadlocks.docx § Handling deadlocks` at [4], and the answer cites [2] (PDF) and [4] (DOCX).
- Half-covered question → answers the covered half with [1] and says TCP isn't in the notes, `refused: false`.
- Out-of-scope → exact refusal, `refused: true`.
- Single-topic "magic rule format" → 4/4 PDF sources (no noise added).
- A live test (`test_two_topic_question_gets_passages_from_both_documents`) fails with the rule disabled and passes with it.
**New observation:** the model sometimes cites with full-width brackets `【3】` instead of `[3]`. The step 13 citation parser must accept both.
**Affects:** `backend/app/store.py`, `config.py`, `llm.py`, tests; TRD §8.2–8.3; IMPLEMENTATION_PLAN step 16.

## 2026-09-27 — Frontend shell (step 11)
**Decision:**
- **Scaffold:** `create-next-app` 16.3.6 (TypeScript strict, App Router, Tailwind v4, ESLint, no `src/`). It also added `frontend/AGENTS.md` + `frontend/CLAUDE.md` (Next's own "read the bundled docs" note; `next dev` re-adds them, so they stay). `output: "export"`, `images.unoptimized`.
- **shadcn:** `init` with the Base UI base, `base-nova` style, and Phosphor icons. The preset was passed as a full `ui.shadcn.com/init?...` URL; partial URLs return 400. Added the UI_UX_BRIEF §6 component map, including chat primitives (`message-scroller`, `message`, `bubble`), `item`, `empty`, `input-group`, `field`, `sheet`, `alert-dialog`, `collapsible`, `toast`. New runtime deps come from shadcn: `@base-ui/react`, `@phosphor-icons/react`, `@shadcn/react`, `class-variance-authority`, `cn`, `shadcn`, `tw-animate-css`.
- **Tokens (§3):**
  - Every shadcn token is replaced with the brief's hex values, and `--evidence*` / `--success` are added.
  - Dark mode uses `@media (prefers-color-scheme: dark)`, both for the variables and via `@custom-variant dark`, so the components' `dark:` classes follow the OS. There is no toggle.
  - Type: `text-xs` becomes the 13/18 caption, plus a `text-reading` 17/27 step.
  - Radius scale: sm 4 px, md/lg 8 px, xl+ 12 px, matching the 4/8/12 rule. `shadow-lg` maps to the overlay shadow only.
  - A global reduced-motion rule is in place.
- **Fonts:** Atkinson Hyperlegible Next + Mono via `next/font/google` (variable). The build warns that Next can't compute fallback metrics for them, a small layout-shift risk while fonts load; measure with Lighthouse in step 14.
- **Owned-component edits:**
  - `Button`: new `evidence` variant, kept at 4 px via a compound variant; press scales to 0.98; `transition-all` replaced with named properties.
  - `Badge`: 4 px radius, no `transition-all`.
  - `Spinner`: `CircleNotch`, `aria-hidden` because status text always sits beside it; imported from `@phosphor-icons/react/ssr`, since the client build breaks server rendering.
  - `InputGroup`: the disabled look now triggers only when its text control is disabled. The shadcn default greyed the whole box whenever the send button was disabled, i.e. whenever the box was empty. Both the light and dark variants were fixed.
- **Server components:** server components import icons from `@phosphor-icons/react/ssr`.
- **Layout check:** a `/preview` route renders the §4.1 layout with placeholder data, because the real app has no data until steps 12–13. It is `noindex` and marked for deletion in step 13 (`ponytail:` comment).
- **Deferred to step 14 (accessibility pass):**
  - The brief's focus ring (2 px `--ring`, 2 px offset) vs shadcn's 3 px translucent ring.
  - 44 px touch targets.
  - Focus return after closing the sheet (a check right after Esc found focus on "Add files", not the trigger; may have run mid-animation).
**Verified:** `npm run build` → `out/` with `/`, `/preview`, `/404`. `tsc --noEmit` and `eslint` are clean. Checked in the browser pane at 1440 (light + dark), 1024 (dark), 768 (light) and 320 px (light + dark, sheet open): the layouts follow §4.1, §4.2 and §4.5. Computed styles confirm the token values, fonts (Atkinson 17/27 px answers), 4/8/12 px radii and the evidence colours. The page is 320 px wide at 320 px (no horizontal scroll). The sheet is 88vw, titled, moves focus inside, and closes on Esc.
**Affects:** `frontend/` (new), `.claude/launch.json`, ARCHITECTURE.

## 2026-09-27 — Library wired to the API (step 12)
**Decision:**
- **One client provider:** `components/workspace-provider.tsx` holds all live state behind a React context. That covers server health, the document list, local upload rows, polling, delete, drag and drop and screen-reader announcements. No state library was added.
- **Server status (APP_FLOW §2):**
  - `GET /health` every 3 s until it answers; "Unreachable" after 90 s of failures; "Try again" restarts the clock.
  - A network error or a 503 `unavailable` from any call drops the app back to "Starting" and resumes checks, so the header, banner and locked controls stay honest.
  - The banner is hidden during the very first check, so a normal load shows no flash.
- **Uploads (APP_FLOW J3):**
  - The browser rejects wrong type, legacy `.doc`/`.ppt` and files over 25 MB instantly. Only the first 10 files of a batch are kept, with a toast.
  - Two uploads run at once; the rest show "Waiting…".
  - An accepted file replaces its local row with the server record. A duplicate (HTTP 200) triggers a toast and a 1.2 s flash of the existing row.
  - Only network failures offer Retry.
  - Copy comes from `lib/copy.ts` (APP_FLOW §5 verbatim), falling back to the server `message` for unknown codes.
- **Polling:** every 2 s while any document is queued or processing. A failed poll keeps the list on screen; only a failed first load shows "Couldn't load your documents." with Try again. Finished documents are announced once in an `aria-live="polite"` region ("X is ready." / "X failed: …").
- **Delete:** confirmed through an `AlertDialog` with the brief's copy; the toast is "X deleted.", and a 404 counts as already deleted. "Remove" on a server-side failed row calls DELETE with no dialog, since nothing usable is lost.
- **Buttons with a reason:** "Add files", "Try sample documents" and delete-while-processing use `aria-disabled` plus a tooltip (`GuardedButton`), so the reason stays reachable by hover and focus.
- **Question box:** locked with the reason as placeholder: waiting for the server / "Add a document to ask questions." / "Your documents are still processing…".
- **`/preview` route and placeholder data deleted now** rather than in step 13: the workspace became state-driven and the layout check was done.
- **UI fixes found in the browser:** "1 passages" → `Intl.PluralRules` ("1 passage"). The sheet and dialog backdrops no longer blur (UI_UX_BRIEF §3.4: no blur).
- **`frontend/.gitignore`:** the scaffold's `.env*` also hid `.env.example`; `!.env.example` added so it gets committed.
- **Deleted (owner approved):** create-next-app's unused `public/*.svg`; the default favicon is kept.
**Verified (real backend on :8000 + cluster, static build on :3000, browser pane):**
- **Backend down on load:** "Starting server…", banner, controls locked with the reason. Backend started: "Connected" with no reload.
- **Six files in one pick:** 2 uploading and the rest waiting. `.txt` and `.ppt` rejected in the browser, fake PDF rejected by the server (415). PDF/DOCX/PPTX went Queued → Ready; question box unlocked; "Scheduling.pptx is ready." announced.
- **Reload:** the library persisted.
- **Drop path:** overlay shown; new file queued. The blank PDF became a server-side failed row with the no-text copy. The same bytes again gave the toast plus a flash and no new row.
- **Delete:** confirmed through the dialog with real clicks at native pane size → row gone, "X deleted." toast. Remove on the failed row deleted it on the server too.
- **Backend stopped, then a drop:** row "Upload didn't finish. Check your connection." with Retry, failure announced, status back to "Starting". Backend restarted, then Retry → uploaded → Ready.
- **11 files:** 10 rows plus the batch toast.
- **Backend down for 90 s:** "Can't reach the server" and the banner with Try again. Try again → "Connected".
- **Dark mode:** checked. Clean-up left the cluster at 0 records.
- (Clicks in a *scaled* emulated viewport, 1280 px in a 961 px pane, missed Base UI dialog buttons; the same flow passed with native-size clicks and via DOM click. This is a tooling artefact, not an app bug.)
**Affects:** `frontend/components/*`, `frontend/lib/{api,workspace,copy,format}.ts`, `frontend/app/*`, `frontend/.gitignore`, `frontend/.env.example`, `.claude/launch.json`.

## 2026-09-27 — Qdrant cluster moved to Oregon; Render region Oregon (owner decision)
**Context:** The step 5 cluster was in AWS `sa-east-1` (São Paulo), and Render has no South American region.
**Decision (owner):** Recreate the Qdrant free cluster in AWS `us-west-2` (Oregon) and deploy the Render service in Oregon, so backend and vector store share a region.
**Re-measured (spike from India → Oregon; single run):** round trip 263 ms (was 335–408). `hybrid_rerank` median 294 ms (was 717–774), `dense` 287 ms, `hybrid` 284 ms. 50-page ingest 8.8 s (was ~23 s). The gate passes. The query time is almost all network from India, so the same-region Render→Qdrant time should be far lower; measure from Render in step 17.
**Verified:** `pytest -q` → 102 passed on the new cluster (51 s, was ~74 s). Collections and indexes were created by `ensure_collections()`, and the cluster was left empty.
**Affects:** `backend/.env` (owner), ARCHITECTURE (external services).

## 2026-09-27 — Thread and streaming answers (step 13)
**Decision:**
- **`api.ask()`:** reads the `fetch` body with `TextDecoderStream` and splits on blank lines into typed `AskEvent`s. `EventSource` can't POST.
  - Aborting (Stop) rethrows the `AbortError`; a dropped connection becomes `ApiError("network")`.
  - A stream that ends without `done`/`error` is treated as "Connection lost".
- **`thread-provider.tsx`:** keeps turns in memory only.
  - Asking a new question stops a running answer first; that answer shows "Stopped.". Retry re-runs the same turn in place.
  - Pre-stream errors: `no_ready_documents` → "Add a document before asking." + Add files. `ask_rate_limited` → message without Retry, and the question goes back into the box. Network or `unavailable` → "Connection lost…" + Retry, and a server re-check.
  - Stream errors map per APP_FLOW J4 (`llm_busy` and `llm_error` offer Retry, `daily_limit` doesn't).
  - The question draft lives in the provider, so a rate-limited question can be restored.
- **`lib/answer-text.ts`:** parses the *accumulated* text on every update, since markers arrive split across pieces.
  - Citations: `[n]`, `【n】` and `[1, 2]`, and only numbers that match a received source.
  - Formatting: paragraphs; `-`/`*`/`•`/`1.` lists, with indented lines continuing the item; `**bold**` and `*emphasis*`, both rendered as weight 700 per the brief; `#` headings as a bold line. An unclosed `**` stays literal while streaming.
  - `ponytail:` a small Markdown subset; a library if answers need more.
- **Tests without a new dependency:** `npm test` runs `node --test` on `lib/*.test.ts` (Node 26 strips types natively). `tsconfig` gains `allowImportingTsExtensions` (valid because `noEmit`). 8 tests.
- **Answer block (UI_UX_BRIEF §4.3):**
  - Progress line "Searching N documents…" → "Found K passages. Writing answer…", then gone when done. A caret blinks while writing (it ends visible, so reduced motion leaves it still). Source rows fade in 40 ms apart (max 6).
  - Refusal: the text plus the hint, no sources, no yellow.
  - Citations toggle their controlled source row, scroll it into view only if off screen, and keep focus. The row id `source-{turn}-{n}` is unique per turn. A "since removed" note appears when the document has left the library.
  - `aria-busy` while streaming, and one polite "Answer ready." per answer.
- **Question box:** controlled; Enter sends (not during IME composition) and Shift+Enter adds a line; "Type at least 3 characters." under 3; counter from 450; `maxLength` 500; grows to about 6 lines; send becomes Stop while streaming.
**Verified live (real backend, Oregon cluster, Groq, browser pane):**
- **Two-topic question:** the progress states appeared in order, and the answer cited both `shared-mime-info-…, p. 13` and `OS_Unit3_Deadlocks, § Handling deadlocks`, with no raw markers left.
- **Citation:** opens its passage in view, turns active, and keeps focus.
- **Stop:** mid-answer the partial text stays with "Stopped." + Retry, and the backend logged `ask: disconnected … 61 pieces`. Retry completes in place.
- **Other answer states:**
  - Out of scope → refusal with the hint and no sources.
  - Documents deleted behind the page → "Add a document before asking." + Add files.
  - Rate limit → message, and the question restored to the box.
  - Backend stopped → "Connection lost…" + Retry, banner, box locked.
- **Question box:** "ab" blocked with the hint; Shift+Enter adds a line; 536 typed characters stop at 500 with "500 / 500".
- **Mobile:** 375 px with no horizontal scroll. Cluster left empty.
**Observed model behaviour (for step 16, not changed here):**
- A broad "explain every section … in detail" question was refused although the notes cover the topic.
- A long answer claimed most OSes use detection and recovery, which the notes don't say.
**Affects:** `frontend/lib/{api,answer-text,copy,types}.ts`, `frontend/components/{thread-provider,thread,answer,question-box,workspace}.tsx`, `frontend/app/globals.css`, `frontend/package.json`, `frontend/tsconfig.json`.

## 2026-09-27 — States, accessibility, mobile (step 14) — Milestone B
**Decision:**
- **Focus ring:** one unlayered `:focus-visible` rule in `globals.css` (2 px `--ring`, 2 px offset, `box-shadow: none`) replaces shadcn's 3 px translucent ring everywhere. Unlayered CSS outranks Tailwind's layered utilities (`outline-none`, `ring-*`), so no component needed editing. The question box draws the ring on the whole input group, not the textarea.
- **Touch targets:** `Button` gets `pointer-coarse:min-h-11 min-w-11` (44 px); inline citations keep 24 px via the `evidence` compound variant. Source-row triggers and the "How it works" link get 44 px on touch too.
- **Reduced motion:** `Spinner` renders `CircleNotch` with `motion-reduce:hidden` and a static `Clock` with `motion-safe:hidden` (UI_UX_BRIEF §3.6). Other motion was already instant via the global rule.
- **Overlays:** `bg-black/10` → `bg-scrim` (new `--scrim` token, light and dark), per "no raw colours".
- **Icons:** decorative icons in shadcn's sheet close and scroll button get `aria-hidden`.
- **Focus after a row disappears** (delete, Remove): moves to the visible "Add files" instead of `<body>`.
- **404 page:** `app/not-found.tsx` (S13) → `404.html` in the static export.
- **LCP (measured, then fixed):**
  - Lighthouse named the first-visit description as the LCP element. It rendered only after hydration, so mobile LCP was 7.2 s from the uncompressed local server and 3.0 s gzipped.
  - Fix: the static HTML is prerendered as a first visit (`useSyncExternalStore` server snapshot `true`). A first visit (no stored workspace) keeps it; the value is read once at module load.
  - A returning visit fetches `/documents` alongside `/health`, not after it. An inline `<head>` script sets `data-returning` before first paint, and CSS hides `[data-first-visit]` parts, so returning visitors never glimpse the empty state. `suppressHydrationWarning` is on `<html>` for that attribute.
**Measured (Lighthouse 13.5, gzip-serving static build as Netlify would, local backend with the page origin allowed):**

| | Performance | Accessibility | Best practices | LCP | CLS | TBT |
|---|---|---|---|---|---|---|
| Mobile (simulated slow 4G, 4× CPU) | 98 | 100 | 100 | 2.3 s | 0.001 | 50 ms |
| Desktop | 100 | 100 | 100 | 0.6 s | 0 | 0 ms |
| Dark mode (`--force-dark-mode`), accessibility only | — | 100 (contrast pass) | — | — | — | — |

Before the fix, mobile gzip was 94 with LCP 3.0 s. The uncompressed python server gave 76–77 with LCP 6.6–7.2 s, because the 797 KB of JS is 245 KB gzipped. Runs where the page origin wasn't allowed by CORS showed Best practices 96 and CLS 0.054 (server banner); those are test-setup artefacts, re-run clean.

**UI_UX_BRIEF §9 checklist (verified):**
- **Contrast:** Lighthouse contrast passes in both modes.
- **Focus ring:** 2 px, 2 px offset, measured on every Tab stop.
- **Skip link:** first Tab stop.
- **Status:** icon + text.
- **Icon-only buttons:** named ("Delete X", "Remove X", "Retry X", "Stop answer", "Send question").
- **Live regions:** library events, "Answer ready.", `aria-busy` while streaming.
- **Dialog:** focus starts on Cancel, Tab is trapped, Esc closes, focus returns to the trigger.
- **Sheet:** titled, focus inside, Esc closes and returns focus to Documents, `overscroll-behavior: contain`.
- **Touch targets:** 44 px under a coarse pointer (mobile preset reports `pointer: coarse`), citations 24 px.
- **Other items:**
  - The file picker is the alternative to drag and drop.
  - At 320 px: no horizontal scroll (the 200% zoom equivalent), and zoom isn't disabled.
  - `prefers-reduced-motion` verified with headless Chrome `--force-prefers-reduced-motion` (spinner → clock).
  - `translate="no"` on names and the wordmark; `lang="en"`.
  - Buttons are `<button>`, links are `<a>`.
  - The question box has a label, `name`, and `autocomplete=off`.
  - No `transition-all`.
  - Long names truncate with the extension kept; errors wrap.
  - Numbers use `Intl`.
  - `color-scheme` and `theme-color` are set.
  - Yellow appears only on evidence.
  - The 4/8/12 radius rule holds.
  - One icon family and one font family.
  - No raw hex in components.
  - Checked in light, dark, desktop and mobile.

**APP_FLOW §5 states verified live:** all library row states, including new this step `unreadable`, over 25 MB (client) and `interrupted` (backend stopped mid-ingest, then swept); server starting / unreachable; answer states (step 13); 404.
**Not verified live:** "Couldn't load your documents." (needs `/documents` to fail while `/health` succeeds; the logic is covered by reading, not triggered); `workspace_full` / `storage_full` rows (backend tests cover the codes; the UI uses the copy table); "delete failed" toast.
**Affects:** `frontend/app/{globals.css,layout.tsx,not-found.tsx}`, `frontend/components/{workspace-provider,library,first-visit,answer,app-header}.tsx`, `frontend/components/ui/{button,spinner,sheet,alert-dialog,message-scroller}.tsx`, `frontend/lib/workspace.ts`.

## 2026-09-27 — Sample documents and suggested questions (step 15)
**Decision:**
- `POST /documents/samples` registers the 3 files in `backend/samples/` with the same id rule as uploads (`uuid5(workspace:sha256)`), so a second click adds nothing and returns 200 ("Sample documents are already in your library."). A failed sample is re-queued. Limits: `workspace_full` counts only the missing samples; `storage_full` and the upload rate limit apply (one upload per call).
- The ingest worker deletes the file it processes, so each sample is enqueued as a temp copy; `backend/samples/` is never touched.
- "Try sample documents" is disabled at 28+ documents with "Your library is almost full (30 documents max).", and while the server isn't ready. It shows a spinner during the request; repeat clicks are ignored.
- Suggested questions (`frontend/lib/samples.ts`) appear under "Ask a question about your documents." while every document is a sample, none is uploading, and at least one is Ready. Each one is sent exactly like a typed question; once the thread has a turn they're gone. They're GuardedButtons, so they carry the question-box lock reason if the server drops.
  1. "What is the difference between git revert and git reset --hard?" (all three files cover it)
  2. "How do Git-Flow and GitHub Flow branching strategies differ?" (DOCX §6.2 table)
  3. "How do I save unfinished work with git stash, and how can git reflog recover a lost commit?" (needs two documents: stash is in all three, the reflog recovery is only in the DOCX §7) — **corrected in step 16:** the DOCX alone answers both halves (§5 and §7), so this never needed two documents; replaced by eval q15.
- Answers now render `inline code` in the mono face (UI_UX_BRIEF §3.2 already specified it; the Git samples made it visible). Brackets inside code stay code, not citations.

**Why:** APP_FLOW J2 and BACKEND_SCHEMA §7. Re-adding rows in place (not moving them to the top) keeps the list still when the samples were already there.
**Alternatives:** Copying samples into the workspace as normal uploads from the frontend (needs the files in the static build, and loses `is_sample`). A Markdown library for inline code (a regex covers the one missing case).

**Verified in a real browser against the Oregon cluster and Groq:**
- Fresh workspace, then "Try sample documents": toast "Sample documents added.", 3 Sample rows went Queued, Processing, Ready (10 / 25 / 11 passages), and focus moved to "Add files". The suggestions appeared as soon as the first file was Ready.
- A second click: 200, toast "Sample documents are already in your library.", no duplicate rows, order kept.
- The stash/reflog suggestion streamed a cited answer from the DOCX (§5, §7) and the PPTX (slide 6) (not a true two-document question; see step 16). The revert/reset suggestion cited all three files, with code in mono.
- At 375 px: no horizontal scroll, and the suggestion labels wrap at 52 px tall.
- Backend logs carry ids, counts and timings only. Test documents deleted afterwards; the cluster is left empty.
- Tests: `npm test` 9/9, `tsc`, `eslint` and the build are clean. Backend `pytest -m "not live"` gives 98 passed (5 new sample tests, including one that parses the committed sample files).

**Not verified live:** the 28+ disabled state (needs 28 documents; the rule is one comparison), and `workspace_full` / `storage_full` / rate limit on samples (covered by backend tests).
**Affects:**
- `backend/app/main.py`, `backend/tests/{test_documents_api,test_parsing,files}.py`
- `frontend/lib/{api,copy,limits,samples,answer-text,answer-text.test}.ts`
- `frontend/components/{workspace-provider,library,workspace,answer}.tsx`

## 2026-09-27 — Evaluation and tuning (step 16)
> **Partly superseded the same day** by "Step 16 follow-up" below. The eval scored location only, which favoured 400-character chunks. The defaults are now `hybrid` / 700 / 4.
**Decision:** Defaults are now `RETRIEVAL_MODE=hybrid`, `CHUNK_SIZE=400` and `TOP_K=4` (overlap stays 100). `SECOND_DOC_RATIO` stays 0.95. The rule is kept for `hybrid_rerank` but isn't used by the default mode.

**How the eval was built:**
- `backend/eval/qa.json` has 15 questions (12 single-answer, 3 two-document) and 3 out-of-scope. Each two-document question lists `parts`, and each part is answered by a different file, so no single file answers the whole question. Locations are drafted by Claude from the parsed text; **the owner still needs to check them.**
- The first draft copied the documents' own wording. That run was saturated: nearly every question ranked 1st in every mode, and the ratio sweep changed nothing. The questions were rewritten the way a student asks: 10 paraphrased without the command name, and 2 naming commands (the app's suggested questions). Only the rewritten set's results are reported.
- `backend/eval/run_eval.py` (TRD §11) builds `eval_400` / `eval_700` / `eval_1000`, asks each question once per mode, and scores every k and ratio from the same ranked candidates. `--refusal` adds 3 Groq calls. It writes `eval/results.md`. About 1 minute; temporary collections are deleted.

**Results (final run, `eval/results.md`):**

| Size | Mode | hit@4 | MRR@6 | Both@4 |
|---|---|---|---|---|
| 400 | dense | 15/15 | 0.967 | 2/3 |
| 400 | hybrid | 15/15 | 0.956 | 3/3 |
| 400 | hybrid_rerank | 15/15 | 0.956 | 3/3 |
| 700 | hybrid | 15/15 | 0.889 | 3/3 |
| 700 | hybrid_rerank | 14/15 | 0.911 | 3/3 |
| 1000 | hybrid | 15/15 | 0.956 | 3/3 |
| 1000 | hybrid_rerank | 14/15 | 0.889 | 2/3 |

- **Refusal check:** 3/3 refused (`openai/gpt-oss-20b`, 400 / hybrid / k 4).
- **Latency:** mean retrieval 260–370 ms in every row, measured from the developer machine to us-west-2. Differences between modes are smaller than the run-to-run variation.
- **Run-to-run noise:** collections are rebuilt each run, and near-equal scores can swap. In three identical runs, only `1000 hybrid` q11 moved (rank 1 to 2, MRR 0.956 to 0.922, then back). One question of difference is noise.

**Crowding check (one-off, files not in the repo):**
- Setup: the step 10 case, the 70-page shared-mime-info spec PDF (123 / 70 / 50 chunks) plus the 3-section OS notes .docx, with 3 two-topic questions.
- "Both documents in the top 4":
  - `dense`: 1/3, 1/3, 2/3 (sizes 400 / 700 / 1000);
  - `hybrid`: 3/3 at every size;
  - `hybrid_rerank`: 2/3 with the rule off and 3/3 with any ratio from 0.90 to 0.97.
- The small document's best re-ranked passage scored 0.976–0.978 of the leader, or was itself the leader.

**Why:**
- **Mode.** The rule is hit@4, then Both@4 (PRD FR-12), then MRR@6; a tie goes to the smaller k and the cheaper mode. `dense` fails the two-document questions (Both@4 2/3). `hybrid_rerank` never beats `hybrid`: it ties at 400 and is one question worse at 700 and 1000.
  - ColBERT scores are nearly flat on these short technical passages; the top 6 sit within 1% (for example 24.90 down to 24.76). So it barely separates passages, and it dropped the cherry-pick section (q12) at 700 and 1000.
  - `hybrid` also keeps both documents in the crowding case without the second-document rule.
  - Latency is equal, so the cheaper mode wins.
- **Chunk size.** `400 hybrid` and `1000 hybrid` tie on every quality column. 400 wins on cost:
  - 4 passages of 400 characters are about 400 prompt tokens against about 1,000 at 1000, and Groq's daily token cap is the demo's scarcest limit (TRD §16);
  - 1000 is also at MiniLM's ~256-token input limit.
  - The price: about 60% more stored chunks than 1000 (65 vs 40 for the samples) against the 30,000-chunk cap.
- **TOP_K.** 4, not 2: hit@2 is 14/15 and the two-document questions need 4 slots.
- **Ratio.** 0.95 stays: every ratio from 0.90 to 0.97 gave identical results in both checks.

**Alternatives:**
- Keep `hybrid_rerank` as designed (TRD §8.2). It isn't better on any measurement here, and the default can be switched back with one env var if a larger eval shows it helps.
- A chunk size of 1000: equal quality, more Groq tokens per question.
- Growing the eval with unrelated documents: that would change the TRD §11 design, so it wasn't done without asking.

**Also changed:**
- `store.py`, refactor inside the module; routes and the `retrieve` call used by `/ask` are unchanged:
  - `create_chunks_collection(name)`;
  - `upsert_chunks(collection, …)`;
  - `search()` returns the ranked candidates;
  - `with_second_document(points, k, ratio)` (was `_with_second_document`);
  - `retrieve(…, collection=CHUNKS)`.
- Suggested question 3 is now eval q15 (.gitignore in subfolders + keeping `.env` out), a real two-document question. Checked in the browser on the new defaults: 3 samples Ready (17 / 37 / 11 = 65 passages); the answer cited DOCX § 11 and PDF p. 2.
- Answer parser:
  - Code spans are set aside before emphasis and citations, so `` `*.swp` `` stays code.
  - Fenced ``` blocks render as code blocks (monospace, scrolling inside the block; the page doesn't widen).
  - Both bugs were found in that answer.

**Observed, not fixed:** that answer also suggested an uncited pattern (`*/.env`) and a rule-override remark that the sources don't contain. This is a claim beyond the sources. Fixing it means changing the TRD §8.3 prompt, so it is for the owner.

**Verified:**
- Tests:
  - `pytest -m "not live"`: 98 passed.
  - Live Qdrant tests (`test_store_live`, `test_ingest_live`): 8 passed.
  - `npm test`: 10/10; `tsc`, `eslint` and the build are clean.
- The cluster is left with only `chunks` and `documents`, 0 chunks.

**Affects:**
- `backend/app/{store,config}.py`, `backend/.env.example`
- `backend/eval/{qa.json,run_eval.py,results.md}`, `backend/tests/test_store.py`
- `frontend/lib/{samples,answer-text,answer-text.test}.ts`, `frontend/components/answer.tsx`

## 2026-09-27 — Step 16 follow-up: evidence scoring, prompt sentence, PRD FR-11 (owner approved)
**Context:**
- The owner approved adding the prompt sentence and updating the TRD.
- Checking the prompt showed the `.gitignore` question answered "the notes don't cover `.env`", although DOCX § 11 does.
- At 400 characters, § 11 splits into two chunks, and the retrieved one lacks `.env`. The eval still scored a hit, because it matched the location label only.
- That scoring favours small chunks (any chunk of the right page or section counts), so the step 16 choice of 400 was an artefact.

**Decision:**
1. **Evidence scoring.**
   - `qa.json` locations can carry `has` phrases. A hit needs the location and one phrase in the passage, ignoring case and whitespace. Phrases were added where other chunks of the location hold unrelated text: PDF pages and long sections.
   - Two-document `parts` are objects `{expect, has}`.
   - Every phrase is checked to occur in its location's text. `tests/test_eval.py` covers the matching (offline).
2. **Defaults** (owner choice among the options offered): `RETRIEVAL_MODE=hybrid`, `CHUNK_SIZE=700`, `TOP_K=4`.
   - With evidence scoring, `400 hybrid` misses a two-document question (Both@4 2/3).
   - `700 hybrid` and `1000 hybrid` both reach hit@4 15/15 and Both@4 3/3. Their MRR@6 is 0.889 vs 0.889 in one run and 0.889 vs 0.922 in the next; the only difference is q11 at 1000 flipping between rank 1 and 2.
   - Treated as a tie; 700 uses fewer Groq tokens per question.
   - `hybrid_rerank` at 700: hit@4 14/15 (q12 at rank 6), Both@4 3/3.
3. **PRD FR-11 amended.** Re-ranking is a retrieval mode measured in the eval, not a requirement; the default is whatever the eval supports.
   - TRD §1, §3, §5, §8.2, §11 and §17 were updated to match: default mode, the evidence metric and ranking rule, and a resume bullet without a re-rank claim.
4. **Prompt (TRD §8.3, `llm.py`):** "Don't add facts, commands, or examples that aren't in the sources." (in commit `197071d`).

**Results (final run, `eval/results.md`):**

| Size | Mode | hit@4 | MRR@6 | Both@4 |
|---|---|---|---|---|
| 400 | hybrid | 15/15 | 0.878 | 2/3 |
| 700 | dense | 15/15 | 0.911 | 2/3 |
| 700 | **hybrid** | 15/15 | 0.889 | 3/3 |
| 700 | hybrid_rerank | 14/15 | 0.911 | 3/3 |
| 1000 | hybrid | 15/15 | 0.922 | 3/3 |

- Refusal check: 3/3 on 700 / hybrid / 4.

**Prompt check** (same sources, old vs new prompt, `gpt-oss-20b`, 400-character chunks before the switch):
- q01 and q13: equivalent answers.
- q15: both prompts said `.env` isn't covered (the passage lacked it).
- 3 out-of-scope questions: all refused.
- Neither prompt repeated the earlier `*/.env` invention.
- On 700 / hybrid, q15 now retrieves the § 11 passage with `.env` and answers both parts, citing DOCX § 11 and PDF p. 2.
- It still added one uncited aside ("unless another .gitignore overrides it in a deeper folder"). The sentence reduces such asides but doesn't remove them, so this remains a known limitation of the 20B model.

**Alternatives:**
- Keep `hybrid_rerank` to satisfy FR-11 as written (one question lower on hit@4).
- `hybrid_rerank` at 400 (highest re-rank hit@4, but misses the two-document question).

**APP_FLOW (owner approved):** the traceability row for FR-11 now reads "Hybrid search (re-rank as a measured mode)".
**Not changed:** IMPLEMENTATION_PLAN step 2's `.env` block shows `RETRIEVAL_MODE=hybrid_rerank` (historical: what step 2 set up).

**One eval run failed without output** (stdout and stderr had been suppressed); the rerun succeeded. The cause wasn't captured.

**Verified:**
- `pytest -m "not live"`: 101 passed.
- Sample `qa.json` phrases are validated against the parsed text.
- The cluster holds only `chunks` and `documents`.

**Affects:**
- `backend/app/config.py`, `backend/.env.example`
- `backend/eval/{qa.json,run_eval.py,results.md}`, `backend/tests/test_eval.py`
- `docs/app/{PRD,TRD,APP_FLOW}.md`

## 2026-09-27 — Deploy setup (step 17)
**Decision:**
- **Render via a Blueprint (`render.yaml` at the repo root)**, applied by the owner from the dashboard.
  - The Render MCP tool can't set a root directory or health check path. The Blueprint keeps every setting in the repo.
  - Secrets (`GROQ_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`) are `sync: false`: the dashboard asks the owner for them, so they never pass through code, chat or tool calls.
- **`PYTHON_VERSION=3.12.3`**, the local version. Render reads `.python-version` only from the repo root; without this, a new service would get Python 3.14.3.
- **`netlify.toml` at the repo root** with `base = "frontend"`, not in `frontend/` as TRD §4 shows. Netlify reads the file from the root, and `base` points the build at `frontend`. Settings: `npm run build`, publish `out` (Netlify's setting for a static Next.js export), Node 24 LTS.
- **Names:**
  - Netlify project `coursemind-app` (`coursemind` was taken; created by Claude, renamed from `coursemind-2jow`).
  - Render service `coursemind-api`.
  - `ALLOWED_ORIGINS=https://coursemind-app.netlify.app,http://localhost:3000`.
  - `NEXT_PUBLIC_API_URL=https://coursemind-api.onrender.com` is a Netlify environment variable (builds only), so it can change without a commit.
- **Render free hours (owner decision):** keep WhatHotel and attendify-backend running and keep CourseMind awake with UptimeRobot every 5 minutes. **Accepted risk:** CourseMind alone uses about 744 of the workspace's 750 free hours a month. If the other two are woken for more than about 6 hours in a month, Render suspends every free service in the workspace until the next month. Alternatives offered: suspend the other two; no 24/7 keep-alive (about 1 minute cold start).
- **`X-Forwarded-For`:**
  - `client_ip` uses the first entry.
  - Render staff say they set the first entry to the real client IP, while an older user report says Render only appends.
  - To be verified live: 6 `/ask` calls from one machine, each with a different forged `X-Forwarded-For`, must still hit the 5-per-minute limit. A fresh workspace answers 409 before any LLM call, so the test costs nothing.

**Checked before deploy:**
- No `.env` file, private plan or real key value anywhere in git history. The history was scanned for the actual `.env` values; only key names were printed.
- The repo is public, and `main` matches `origin`.
- No `~/.claude/DEPLOY_CHECKLIST.md` exists, so TRD §12 and §13 served as the checklist.

