# CourseMind — Product Requirements Document

**Owner:** Akash Shrivastav · **Status:** Approved v2 · **Date:** 2026-09-27

### 1. Summary
CourseMind is a study assistant for course material. A student uploads their documents — PDFs, Word files, and PowerPoint decks, many at once — and asks questions in plain English. CourseMind searches all of the documents, then writes a short answer grounded only in them. Every claim cites the document and location (page, slide, or section), and the student can click a citation to see the source text. If the documents do not contain the answer, CourseMind says so instead of guessing.

### 2. Problem
Course material is spread across lecture PDFs, slide decks, and Word notes. Finding one definition means opening several files and searching each one, and Ctrl+F only works if you know the exact word. General chatbots answer from the internet, not from *this* course, and they invent facts. Students need answers from their own material, drawn from all of it at once, with proof.

### 3. Goals
- G1. Answer questions using only the student's uploaded documents (PDF, Word, PowerPoint).
- G2. Search across all of the student's documents in one question, and combine information from several documents when needed.
- G3. Cite every claim with document name + location, verifiable in one click.
- G4. Refuse clearly when the answer is not in the documents.
- G5. Prove retrieval quality with a repeatable evaluation, including what hybrid search and re-ranking add.
- G6. Run live at $0/month with no cold-start wait during normal use, from a public repo a reviewer can read in 10 minutes.

### 4. Non-goals (v1)
- User accounts, login, or history across devices (documents belong to an anonymous browser workspace).
- Multi-turn conversation memory (each question is answered on its own).
- Legacy `.doc` / `.ppt` files (user is asked to save as `.docx` / `.pptx`).

### 5. Users
- **Primary — Student:** has a folder of course files; wants fast, trustworthy answers while revising.
- **Secondary — Reviewer (recruiter / interviewer):** opens the live link for 1–2 minutes, may not have files handy, then reads the README and code.

### 6. User stories and acceptance criteria
| ID | Story | Acceptance criteria |
|---|---|---|
| US-1 | As a student, I upload several course files at once. | I can select or drag up to 10 files (`.pdf`, `.docx`, `.pptx`, each ≤ 25 MB). Each file shows its own status: Queued → Processing → Ready (N passages) or Failed (reason). Invalid files are rejected individually; valid ones still go through. |
| US-2 | As a student, I ask a question and get an answer drawn from all my documents. | The answer uses passages from any Ready document. When the answer needs two documents, it cites both. |
| US-3 | As a student, I see the answer as it is written. | Answer text streams in word by word; the first words appear within ~4 s when the server is warm. |
| US-4 | As a student, I verify an answer. | Each claim carries a citation shown as document + location, e.g. `OS_Lecture3.pdf · p. 12`, `DBMS.pptx · slide 4`, `Notes.docx · § Normalization`. Clicking a citation shows the exact passage. |
| US-5 | As a student, I ask something my documents do not cover. | CourseMind replies "I couldn't find that in your notes." and invents nothing. |
| US-6 | As a student, I manage my document library. | I see every document with type, status, and passage count. I can delete a document; later answers no longer use it. Re-uploading an identical file does not create duplicates. |
| US-7 | As a student, I come back later. | My documents are still there (same browser), even if the server restarted or was redeployed. |
| US-8 | As a reviewer, I open the live link. | The app responds immediately (no "server waking up" wait during normal use). A "Try sample documents" button loads a sample PDF, deck, and Word file. |
| US-9 | As a reviewer, I judge retrieval quality. | README shows an evaluation table: hit@k and MRR for semantic-only vs. hybrid vs. hybrid + re-rank, across chunk sizes and k, with the chosen configuration. |

### 7. Functional requirements
**Upload and processing**
- FR-1 Accept `.pdf`, `.docx`, `.pptx`. Validate each file by extension **and** content signature. Max 25 MB per file, max 10 files per upload, max 30 documents per workspace.
- FR-2 Process uploads in the background. Report per-file status (Queued, Processing, Ready, Failed + reason). Questions can be asked while other files are still processing; only Ready documents are searched.
- FR-3 Extract text with its location: PDF → page number (1-based, as shown by the PDF viewer); PowerPoint → slide number (slide text, tables, speaker notes); Word → nearest section heading (paragraphs and tables).
- FR-4 Split text into overlapping passages; each passage keeps document name, file type, and location.
- FR-5 Fail a file with a clear reason when it has no selectable text ("No selectable text found — scanned documents are not supported yet").
- FR-6 Detect an identical file already in the workspace and skip re-indexing it.

**Library**
- FR-7 List documents in the workspace with name, type, status, passage count.
- FR-8 Delete a document and all of its passages.
- FR-9 "Try sample documents" loads a bundled sample set (one PDF, one deck, one Word file) into the workspace.

**Question answering**
- FR-10 Accept a question of 3–500 characters. Search across all Ready documents in the workspace.
- FR-11 Retrieval combines keyword search and semantic search, then re-ranks the candidates; the top-k passages go to the model.
- FR-12 The answer uses only those passages, cites document + location for each claim, and combines passages from different documents when relevant.
- FR-13 Stream the answer to the UI as it is generated; return the list of source passages with it.
- FR-14 Refusal: if the passages do not contain the answer, reply with the fixed sentence "I couldn't find that in your notes." If the workspace has no Ready documents, prompt the user to upload instead of calling the model.

**Operations and evaluation**
- FR-15 Health endpoint for uptime monitoring.
- FR-16 Offline evaluation script: 15 hand-written questions over the sample documents (at least one answer in each format, at least two needing two documents), plus 3 out-of-scope questions. Reports hit@k and MRR for {semantic, hybrid, hybrid + re-rank} × chunk size {400, 700, 1000} × k {2, 4, 6}, and the refusal rate on out-of-scope questions.

### 8. Non-functional requirements
- NFR-1 **Cost:** $0/month. Render free (backend), Netlify free (frontend), Groq free (LLM), Qdrant Cloud free (documents and search).
- NFR-2 **No cold start in normal use:** an uptime monitor pings the health endpoint every 5 min so the Render service never idles out. This uses ~744 of Render's 750 free hours per month, so the backend must be the only free Render service in the workspace. After a redeploy, the first request may take up to ~1 min; the UI shows a status indicator if the server is not ready.
- NFR-3 **Durability:** uploaded documents survive server restarts and redeploys (stored outside Render).
- NFR-4 **Resources:** the backend runs within Render free limits (512 MB RAM, 0.1 CPU); embedding and re-ranking do not run on the web server.
- NFR-5 **Latency (warm):** first streamed words p50 < 4 s; full answer p50 < 10 s; a 50-page document reaches Ready in < 60 s. Real measurements go in the README.
- NFR-6 **Scale:** demo scale — up to 30 documents per workspace and a handful of concurrent users.
- NFR-7 **Security and privacy:** API keys only on the server; every file validated at upload; workspace ids random and unguessable; one workspace can never read another's documents; CORS allows only the Netlify domain in production; README warns not to upload private documents to the demo.
- NFR-8 **Accessibility:** keyboard-usable upload, chat, and citations; labelled controls; streamed answers announced to screen readers.
- NFR-9 **Maintainability:** small codebase, one clear job per module, nothing the owner cannot explain line by line in an interview.

### 9. UX flow (single page)
1. **Header:** "CourseMind" + one-line pitch + server status dot (ready / starting).
2. **Library panel (left; top on mobile):** drop zone / file picker, "Try sample documents" button, document list with type icon, status, passage count, delete button.
3. **Chat panel (right):** streamed answers with inline citations; source chips under each answer expand to the passage. Input disabled until at least one document is Ready.
4. **Errors inline, in plain words:** unsupported type, too large, no selectable text, rate limit reached ("Too many questions right now — try again in a minute").

### 10. Success metrics
- Retrieval: hit@4 of the chosen configuration on the 15-question set. Target ≥ 13/15. **Report the real number, whatever it is**, plus the gain from hybrid and from re-ranking.
- Grounding: 3/3 out-of-scope questions get the refusal sentence.
- Latency: measured first-token and full-answer p50 in README.
- Live: link works in an incognito window with no wake-up wait; README has screenshot/GIF, architecture diagram, and evaluation table.

### 11. Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Groq retires the model again (it retired `llama-3.1-8b-instant` on 2026-08-16) | Answers fail | Model names are configuration, with a fallback model. |
| Render free is small (512 MB, 0.1 CPU) | Slow or crashing backend | No ML on the web server; one upload processed at a time. |
| Render disk is wiped on restart | Documents lost | Documents stored in Qdrant Cloud. |
| Keep-alive pings use nearly all free hours | A second free Render service would suspend everything | Only one free Render service in the workspace. |
| Qdrant free cluster suspends after 1 week idle | Search unavailable | Health check pings Qdrant every 5 min. |
| Public demo exhausts Groq free quota | Rate-limit errors | Per-IP limits, fallback model, friendly retry message. |
| Word has no fixed pages; slide text order can be odd | Citations less precise | Section heading for Word, slide number for decks; stated in README. |

### 12. Decisions
1. **Frontend:** Next.js + TypeScript.
2. **Sample documents:** one PDF, one deck, one Word file you may publish (e.g., your own OS/DBMS notes); they are also the evaluation set. *You provide these.*
3. **`CourseMind_build_plan.md`** contains resume/application strategy — keep it out of the public repo.
4. **Resume bullets:** reword after evaluation to match the final build (see TRD §17).

### 13. Future work (after v1)
- **Internet / general-LLM fallback** when the notes do not contain the answer — clearly labelled "Not from your notes", with web sources cited separately.
- OCR for scanned PDFs and images inside slides.
- Conversation memory for follow-up questions.
- Accounts and cross-device libraries.
- Legacy `.doc` / `.ppt` support.
- Relevance-score threshold for refusals; LLM-judged answer faithfulness evaluation.
- Durable job queue for large uploads.

### 14. Milestones (≈ 7.5 h)
| # | Milestone | Time |
|---|---|---|
| S0 | Spike: Qdrant Cloud Inference speed + API details | 30 min |
| M1 | Repo + accounts (Groq, Qdrant, Render, Netlify, UptimeRobot) | 30 min |
| M2 | Parsers for PDF / Word / PowerPoint with locations + chunking | 60 min |
| M3 | Indexing, hybrid retrieval, re-ranking | 60 min |
| M4 | API: background upload + status, library, streaming ask | 60 min |
| M5 | Frontend: library panel, streaming chat, citations | 90 min |
| M6 | Sample docs, 15 + 3 eval questions, run evaluation, pick config | 60 min |
| M7 | Deploy, keep-alive, README | 45 min |

### Appendix A — Hosting options explored (2026-09-27)
| Option | Cost | Cold start | Disk | Verdict |
|---|---|---|---|---|
| **Render free** (backend) | $0 | Sleeps after 15 min idle, ~1 min wake — avoided by keep-alive (750 free h/month ≥ 744 h) | Wiped on restart | **Chosen**, with keep-alive + Qdrant Cloud for storage |
| Railway Free | $0 ($1/month credit, 0.5 GB RAM) | None, but always-on usage (~$3–4/month) exceeds the credit, so the service stops | 0.5 GB volume | Not viable at $0 |
| Railway Hobby | $5/month (includes $5 usage) | None | Persistent volume | Best paid fallback |
| **Netlify** (frontend) | $0 | None (static CDN) | — | **Chosen** for frontend |
| Netlify Functions (backend) | $0 | Yes | — | Not viable: no Python runtime, 10–26 s limit |
| Hugging Face Spaces | Docker/Gradio Spaces need a paid plan | — | — | Not viable at $0 |
