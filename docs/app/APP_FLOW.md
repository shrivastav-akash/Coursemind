# CourseMind — App Flow

**Status:** Draft v1 · **Date:** 2026-09-27 · **Based on:** PRD v2, TRD v1 · **Visual spec:** [UI_UX_BRIEF.md](UI_UX_BRIEF.md)

How people move through CourseMind: every screen, every journey step by step, what happens on errors and empty states, and who can see what.

**Conventions**
- CourseMind is one page (`/`). "Screens" below are the views and states of that page, plus one 404 page.
- Journeys are numbered `J1`–`J13`. Error and empty cases are written inline as **If…** lines and collected in §5.
- UI copy in quotes is the source of truth for on-screen strings. It follows the brief's voice rules (sentence case, no em dashes), so a few strings differ slightly from PRD/TRD wording on purpose.
- There is no sign-up or login (PRD non-goal). A visitor's documents belong to an anonymous **workspace** stored in their browser.

---

## 1. Screens and views

| # | Screen / view | One line |
|---|---|---|
| S1 | **Workspace, desktop** | Two panes: document library on the left, question and answer thread on the right. |
| S2 | **Workspace, mobile** | Thread fills the screen; the library opens from a "Documents" button in the header. |
| S3 | **Library panel** | Add files, try sample documents, see each document's status, delete documents. |
| S4 | **Library sheet (mobile)** | The same library panel, shown as a side sheet over the thread. |
| S5 | **First-visit empty state** | Shown in the thread area when the workspace has no documents; offers "Add files" and "Try sample documents". |
| S6 | **Waiting-for-ready state** | Shown when documents exist but none is Ready yet; the question box explains why it is locked. |
| S7 | **Thread** | Questions and streamed answers, newest at the bottom, with a jump-to-latest button. |
| S8 | **Answer block** | One answer: progress line, streamed text with inline citations, numbered source list, and a stop/retry control. |
| S9 | **Source passage (expanded)** | The exact passage behind a citation, opened inline under the answer. |
| S10 | **Delete confirmation** | Modal dialog that confirms removing one document. |
| S11 | **Drop overlay** | Covers the library while files are dragged over the window. |
| S12 | **Server status banner** | Appears at the top of the thread only when the backend is starting or unreachable. |
| S13 | **Not found page** | Static 404 with one link back to CourseMind. |

---

## 2. Global states

These run underneath every journey.

**Workspace id.** On first load the app creates a random id, saves it in browser storage, and sends it with every request. Same browser = same library. Clearing site data = new, empty workspace.

**Server status** (header indicator + S12 banner):

| State | Trigger | What the user sees |
|---|---|---|
| Ready | `GET /health` returns 200 | Header shows "Connected". No banner. |
| Starting | `/health` fails or times out | Header shows "Starting server…". Banner: "The server is starting. This can take up to a minute." App retries every 3 s. Upload and ask are disabled with that reason. |
| Unreachable | Still failing after 90 s | Banner: "Can't reach the server. Check your connection, then try again." Button: "Try again". |

The keep-alive monitor (TRD §12) means "Starting" should only appear right after a redeploy.

**Document polling.** While any document is Queued or Processing, the library refreshes every 2 s. Polling stops when all documents are Ready or Failed.

**Chat is not saved.** Reloading the page clears the thread. Documents stay. (PRD non-goal: no conversation memory.)

---

## 3. Journeys

### J1 — First visit (student)

1. Student opens the site. Header shows "Starting server…" briefly, then "Connected".
2. Library panel (S3) is empty: "No documents yet."
3. Thread area shows the first-visit empty state (S5):
   - Heading: "Add your course files to start"
   - Body: "CourseMind answers questions from your PDFs, slides, and Word notes, and shows the page each answer came from."
   - Buttons: **Add files** (primary), **Try sample documents** (secondary).
   - Hint under buttons: "PDF, .docx, .pptx, up to 25 MB"
4. Question box is visible but locked, with helper text "Add a document to ask questions."
5. Student continues to **J3** (own files) or **J2** (samples).

- **If** the server is starting: S12 banner shows; both buttons are disabled with tooltip "Waiting for the server…".

### J2 — Reviewer tour with sample documents

1. Reviewer opens the live link (no wake-up wait under normal operation).
2. Selects **Try sample documents**.
3. Three rows appear in the library (sample PDF, deck, Word file), each "Queued", then "Processing…", then "Ready, N passages". Toast: "Sample documents added."
4. As soon as one sample is Ready, the question box unlocks and the thread shows three **suggested questions** as buttons (drawn from the evaluation set, including one that needs two documents).
5. Reviewer selects a suggested question. It is sent exactly like a typed question (continue at **J4** step 3).
6. Reviewer opens a citation (**J5**), then follows the header link "How it works" to the GitHub README with the architecture diagram and evaluation table (PRD US-9).

- **If** samples were already added in this workspace: rows are not duplicated; toast "Sample documents are already in your library."
- **If** the workspace has 28 or more documents: button is disabled with "Your library is almost full (30 documents max)."
- Suggested questions only appear while the library contains only sample documents.

### J3 — Upload own files (mixed valid and invalid)

1. Student selects **Add files** (file picker, multi-select) or drags files onto the window (S11 overlay: "Drop to add files").
2. The browser checks each file before sending:
   - Type is `.pdf`, `.docx`, or `.pptx`.
   - Size is 25 MB or less.
   - At most 10 files in this batch.
3. Each valid file gets a row immediately: "Uploading…". Two uploads run at a time; the rest wait in line with "Waiting…".
4. Server accepts the file: row changes to "Queued". Processing starts (one file at a time across the server): "Processing…".
5. File finishes: row shows "Ready, 128 passages" with a success icon. Question box unlocks if this is the first Ready document.
6. The student can ask questions while other files are still processing (**J4**). Only Ready documents are searched.

- **If** a file has the wrong type: its row appears as Failed right away: "This file type isn't supported. Use PDF, .docx, or .pptx." Other files continue.
- **If** it is a legacy `.doc` or `.ppt`: "Old Word and PowerPoint formats aren't supported. Save it as .docx or .pptx and add it again."
- **If** a file is over 25 MB: "This file is larger than 25 MB."
- **If** more than 10 files are selected: the first 10 are added; toast "You can add up to 10 files at a time. Add the rest in another batch."
- **If** the name ends in `.pdf` but the content isn't a PDF (server signature check, 415): "This file doesn't look like a real PDF, Word, or PowerPoint file."
- **If** the file has no selectable text: row Failed: "No selectable text found. Scanned documents aren't supported yet."
- **If** the file can't be parsed (corrupt, password-protected): "Couldn't read this file. Check that it opens on your computer and isn't password-protected."
- **If** the workspace already has 30 documents (409): row Failed: "Your library is full (30 documents). Delete a document to add another."
- **If** the demo's shared storage is full (503): "The demo's storage is full right now. Try again later."
- **If** the upload rate limit is hit (429): "Too many uploads in the last hour. Try again later."
- **If** the network drops during upload: row Failed: "Upload didn't finish. Check your connection." with a **Retry** button.
- **If** the same file is already in the workspace: no new row; the existing row briefly highlights and a toast says "OS_Lecture3.pdf is already in your library."
- Failed rows keep a **Remove** button; failed files never block other files.

### J4 — Ask a question across documents (core action)

Precondition: at least one Ready document.

1. Student types in the question box (label: "Ask a question about your documents", placeholder "Ask about your notes…"). Enter sends; Shift+Enter adds a line.
2. Student sends. The question appears in the thread (S7). The send button turns into **Stop**.
3. Answer block (S8) shows a progress line: "Searching 3 documents…".
4. Sources arrive first: progress line becomes "Found 4 passages. Writing answer…" and the numbered source list appears collapsed under the answer area.
5. Answer text streams in. Each claim carries an inline citation showing document and location (e.g. `OS_Lecture3, p. 12`, `DBMS, slide 4`, `Notes, § Normalization`). When the answer uses two documents, citations point to both.
6. Stream ends: progress line disappears, **Stop** turns back into send, screen readers hear "Answer ready."
7. Student can ask the next question immediately. Each question is answered on its own (no memory of earlier questions).

- **If** the question is under 3 characters: send button stays disabled; helper text "Type at least 3 characters."
- **If** it passes 450 characters: counter appears "480 / 500"; at 500 the box stops accepting input.
- **If** the student selects **Stop**: streaming ends; the partial answer stays with the note "Stopped." and a **Retry** button.
- **If** a document was deleted or the workspace has no Ready documents at send time (409): answer block shows "Add a document before asking." with **Add files**.
- **If** the ask rate limit is hit (429): "Too many questions in a minute. Try again shortly." Question stays in the box so nothing is retyped.
- **If** the model fails or times out mid-stream (`error` event): partial text stays; note "The answer was interrupted." with **Retry**.
- **If** the AI model is at its per-minute limit for everyone (`llm_busy`): "CourseMind is busy right now. Try again in a minute." with **Retry**.
- **If** the model's daily free limit is used up on both models (`daily_limit`): "The demo has reached today's question limit. Try again tomorrow."
- **If** the network drops: "Connection lost. Check your connection, then retry." with **Retry**.
- **If** a new question is sent while an answer is streaming: the running answer is stopped first (marked "Stopped.").

### J5 — Verify an answer with its source

1. Student selects an inline citation (or a row in the numbered source list).
2. The matching source row expands in place (S9): document name, file type icon, location, and the full passage text with a highlighter-tinted background.
3. The citation that opened it shows as active; other citations for the same source also show as active.
4. Selecting the citation again, or the row's collapse control, closes it. Several sources can be open at once.
5. Keyboard: citations are buttons in reading order; Enter/Space toggles; focus stays on the citation.

- **If** a source's document is deleted later: the passage still shows (it was delivered with the answer) with the note "This document has since been removed from your library."
- **If** the answer is a refusal (J6): no source list is shown, so nothing misleading can be opened.

### J6 — Ask something the documents don't cover

1. Student asks an out-of-scope question (e.g., "Who won the 2022 World Cup?").
2. Progress line: "Searching 3 documents…".
3. Answer shows exactly: "I couldn't find that in your notes."
4. No sources are listed. A muted hint under the refusal: "Try rephrasing with terms from your notes, or add the document that covers this."

- **If** retrieval returns nothing at all, the same refusal appears without calling the model (TRD §8.5); the user sees no difference.
- Future (PRD §13): a clearly labelled "Not from your notes" web answer may be offered here. Not in v1.

### J7 — Manage the library

**Delete a document**
1. Student selects the delete icon on a row (label: "Delete OS_Lecture3.pdf").
2. Confirmation dialog (S10): title "Delete OS_Lecture3.pdf?", body "It will no longer be used in answers. Answers already shown stay on screen." Buttons: **Cancel**, **Delete document**.
3. On confirm: row disappears; toast "OS_Lecture3.pdf deleted." Later answers never cite it.

- **If** the document is still processing: delete is disabled with tooltip "Wait until processing finishes."
- **If** delete fails: toast "Couldn't delete OS_Lecture3.pdf. Try again."
- **If** the last Ready document is deleted: the question box locks again (S6 or S5 wording, whichever applies).

**Re-upload the same file** — see J3: no duplicate, existing row highlights.

**Retry a failed file** — select **Remove** on the failed row, fix the file (e.g., save as .docx), then add it again.

**Library header** shows the count "3 of 30 documents" (tabular numerals) so the cap is never a surprise.

### J8 — Return visit

1. Student returns later in the same browser.
2. Library loads from the server with a skeleton for up to 3 rows, then shows all documents with their current status (PRD US-7: survives restarts and redeploys, because data lives in Qdrant).
3. Thread starts empty (chat not saved). If any document is Ready, the question box is unlocked.

- **If** a document was mid-processing when the server restarted: row shows Failed: "Processing was interrupted by a server restart. Add the file again."
- **If** browser data was cleared or it's a different browser: the student sees S5 (new empty workspace). Documents from the old workspace are not reachable. (Known limitation, TRD §16.)
- **If** the library request fails: library shows "Couldn't load your documents." with **Try again**.

### J9 — Server starting or unreachable

1. Right after a redeploy, the first visitor may see header "Starting server…" and the S12 banner.
2. Upload and ask controls are disabled with the reason on hover/focus.
3. The app retries `/health` every 3 s. When it succeeds, the banner disappears, header shows "Connected", and controls unlock without a reload.

- **If** it still fails after 90 s: banner switches to "Can't reach the server. Check your connection, then try again." with **Try again**.
- **If** the backend is up but the vector store is down (`/health` 503): same banner; asking and uploading stay disabled.

### J10 — Limits in one place

| Limit | Where it shows | Message |
|---|---|---|
| 25 MB per file | Library row | "This file is larger than 25 MB." |
| 10 files per batch | Toast | "You can add up to 10 files at a time. Add the rest in another batch." |
| 30 documents per workspace | Library header count + row | "Your library is full (30 documents). Delete a document to add another." |
| Shared demo storage | Library row | "The demo's storage is full right now. Try again later." |
| 5 questions per minute | Answer block | "Too many questions in a minute. Try again shortly." |
| 30 uploads per hour | Library row | "Too many uploads in the last hour. Try again later." |
| Model busy (per-minute, all visitors) | Answer block | "CourseMind is busy right now. Try again in a minute." |
| Daily model limit | Answer block | "The demo has reached today's question limit. Try again tomorrow." |
| Question length 3–500 | Question box helper/counter | "Type at least 3 characters." / "480 / 500" |

### J11 — Mobile

1. Header: wordmark, **Documents (3)** button, server status (icon + short text).
2. Thread (S2) fills the screen; question box is pinned to the bottom above the safe area.
3. **Documents** opens the library sheet (S4) from the left. Everything in S3 works the same; drag and drop is replaced by the file picker.
4. After adding files, the sheet stays open so the student can watch statuses; closing it (button, swipe, or Esc) returns focus to **Documents**.
5. First-visit empty state (S5) shows in the thread with the same two buttons; **Add files** opens the picker directly without opening the sheet.
6. Citations and source passages expand inline exactly as on desktop.

### J12 — Keyboard and screen reader

1. First Tab reaches "Skip to question box".
2. Order: header (How it works, status), library (Add files, Try sample documents, document rows and their actions), thread (citations and source rows in reading order), question box, send/stop.
3. Status changes are announced politely: "OS_Lecture3.pdf is ready." / "OS_Lecture3.pdf failed: No selectable text found."
4. While an answer streams, the answer region is marked busy; one announcement at the end: "Answer ready." (not every word).
5. Dialog and sheet trap focus, close on Esc, and return focus to the control that opened them.

### J13 — Owner: evaluation, deploy, and monitoring (outside the app)

1. Owner adds the three sample files to `backend/samples/` and writes `eval/qa.json` (15 questions + 3 out-of-scope).
2. Runs `eval/run_eval.py`; reads the hit@k / MRR / latency table; sets `CHUNK_SIZE`, `TOP_K`, `RETRIEVAL_MODE` defaults; copies the table into the README (PRD FR-16, US-9).
3. Runs the refusal check (3 model calls) and records the result.
4. Deploys: Qdrant cluster, Render service, Netlify site, UptimeRobot monitor on `/health` every 5 min (NFR-2).
5. Monitors: UptimeRobot emails on downtime; Render and Qdrant dashboards show logs and usage. None of this is visible to visitors.

---

## 4. Roles and permissions

There is **one in-app role**. Students and reviewers are the same kind of visitor.

| Who | How they're identified | Can see | Can do | Cannot |
|---|---|---|---|---|
| **Visitor** (student or reviewer) | Random workspace id in their browser | Only their own workspace's documents, statuses, and the answers they asked for | Add, delete, and ask about documents in their workspace, up to the limits in J10 | See or search any other workspace; see other visitors' questions; recover a workspace after clearing browser data |
| **Owner / operator** (outside the app) | Access to Render, Netlify, Qdrant, Groq, UptimeRobot accounts | Service logs (timings, counts, ids; never document or question text, TRD §13), storage usage | Deploy, change configuration, run the evaluation, purge data from the Qdrant console | Nothing extra inside the app itself: there is no admin screen in v1 |

Isolation rule: every read and delete on the server is filtered by workspace id (TRD §8.1, §13). A visitor who guessed a document id still cannot open or delete it without the matching workspace id.

---

## 5. Error and empty-state catalogue

| Situation | Where | Copy | Action offered |
|---|---|---|---|
| No documents yet | Thread (S5) | "Add your course files to start" + body from J1 | Add files · Try sample documents |
| No documents yet | Library | "No documents yet." | (buttons are right above) |
| Documents exist, none Ready | Question box helper | "Your documents are still processing. You can ask once one is ready." | — |
| Thread empty, docs Ready | Thread | "Ask a question about your documents." (+ suggested questions if samples only) | Suggested questions |
| Server starting | Banner (S12) | "The server is starting. This can take up to a minute." | Auto-retry |
| Server unreachable | Banner (S12) | "Can't reach the server. Check your connection, then try again." | Try again |
| Library failed to load | Library | "Couldn't load your documents." | Try again |
| Unsupported type | Library row | "This file type isn't supported. Use PDF, .docx, or .pptx." | Remove |
| Legacy .doc / .ppt | Library row | "Old Word and PowerPoint formats aren't supported. Save it as .docx or .pptx and add it again." | Remove |
| Signature mismatch | Library row | "This file doesn't look like a real PDF, Word, or PowerPoint file." | Remove |
| Over 25 MB | Library row | "This file is larger than 25 MB." | Remove |
| No selectable text | Library row | "No selectable text found. Scanned documents aren't supported yet." | Remove |
| Unreadable file | Library row | "Couldn't read this file. Check that it opens on your computer and isn't password-protected." | Remove |
| Interrupted by restart | Library row | "Processing was interrupted by a server restart. Add the file again." | Remove |
| Upload network failure | Library row | "Upload didn't finish. Check your connection." | Retry · Remove |
| Duplicate file | Toast + row highlight | "OS_Lecture3.pdf is already in your library." | — |
| Workspace full | Library row | "Your library is full (30 documents). Delete a document to add another." | Remove |
| Demo storage full | Library row | "The demo's storage is full right now. Try again later." | Remove |
| Refusal | Answer | "I couldn't find that in your notes." + hint from J6 | — |
| Stopped by user | Answer | "Stopped." | Retry |
| Stream interrupted | Answer | "The answer was interrupted." | Retry |
| No Ready docs at send | Answer | "Add a document before asking." | Add files |
| Rate limit (ask) | Answer | "Too many questions in a minute. Try again shortly." | — |
| Model busy (`llm_busy`) | Answer | "CourseMind is busy right now. Try again in a minute." | Retry |
| Daily model limit (`daily_limit`) | Answer | "The demo has reached today's question limit. Try again tomorrow." | — |
| Connection lost mid-answer | Answer | "Connection lost. Check your connection, then retry." | Retry |
| Delete failed | Toast | "Couldn't delete OS_Lecture3.pdf. Try again." | — |
| Unknown URL | 404 page (S13) | "This page doesn't exist." | Go to CourseMind |

Rules: errors say what happened and what to do next; they never apologize and are never vague ("Something went wrong" is not allowed). Each error appears next to the thing it's about (row, answer, banner), not in a generic alert.

---

## 6. PRD coverage check

Every PRD feature appears in at least one journey.

| PRD item | Journey(s) |
|---|---|
| US-1 Upload several files, per-file status | J3, J11 |
| US-2 Answer from all documents, cites both when needed | J4, J2 |
| US-3 Streamed answer, first words fast | J4 |
| US-4 Citation with document + location, click to see passage | J4, J5 |
| US-5 Refusal when not covered | J6 |
| US-6 Library: status, counts, delete, no duplicates | J3, J7 |
| US-7 Documents persist across restarts | J8 |
| US-8 Reviewer: instant load, sample documents | J2, J9 |
| US-9 Evaluation table in README | J2 (link), J13 |
| FR-1 Types, signature check, 25 MB, 10 per batch, 30 per workspace | J3, J10 |
| FR-2 Background processing, statuses, ask while processing | J3, J4 |
| FR-3 Page / slide / section locations | J4, J5 |
| FR-4 Passages keep name, type, location | J5 |
| FR-5 No selectable text failure | J3 |
| FR-6 Duplicate detection | J3, J7 |
| FR-7 Library list | J3, J8 |
| FR-8 Delete document and passages | J7 |
| FR-9 Try sample documents | J1, J2 |
| FR-10 Question 3–500 chars, all Ready docs | J4, J10 |
| FR-11 Hybrid search (re-rank as a measured mode) | J4 (step 3–4, invisible to user), J13 (measured) |
| FR-12 Grounded, cited, multi-document answers | J4, J5 |
| FR-13 Streaming + source list | J4 |
| FR-14 Refusal; prompt to upload when nothing Ready | J6, J4 |
| FR-15 Health endpoint | J9, J13 |
| FR-16 Offline evaluation | J13 |
| NFR-2 No cold start in normal use | J2, J9, J13 |
| NFR-3 Durability | J8 |
| NFR-7 Workspace isolation | §4 |
| NFR-8 Accessibility | J12 |
| PRD §13 Future: web/LLM fallback | J6 (noted, not in v1) |
