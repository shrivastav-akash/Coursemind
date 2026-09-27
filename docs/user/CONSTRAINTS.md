# CourseMind — Constraints

Rules for anyone (human or AI) working on this repo. **"Ask first"** means: stop, explain the change and why, and wait for the owner's yes. Record approved changes in [DECISIONS.md](DECISIONS.md).

## Never (no exceptions)
- Commit secrets. `.env` stays git-ignored; keys never go in code, docs, logs, or chat.
- Make `docs/user/CourseMind_build_plan.md` public (it holds private application strategy; it is git-ignored).
- Log document text or question text. Log ids, counts, and timings only.
- Publish made-up numbers. Eval results, latency, and resume figures come from real runs only.
- Create accounts, enter credentials, or spend money on the owner's behalf.

## Ask first
**Process**
- Starting the next implementation step (the owner reviews each step).
- `git commit`, `git push`, creating the GitHub repo, deploying, creating or changing cloud resources (Qdrant, Render, Netlify, UptimeRobot, Groq).
- Deleting any data in Qdrant outside test and eval collections.
- Adding a dependency not named in TRD §2 or IMPLEMENTATION_PLAN.
- Editing an approved doc: PRD, TRD, APP_FLOW, UI_UX_BRIEF, BACKEND_SCHEMA, IMPLEMENTATION_PLAN.

**Product and stack**
- Anything that costs money. Target is $0/month on free tiers.
- Swapping stack or hosting: FastAPI + Python 3.12, Next.js + TypeScript static export, Qdrant Cloud + Cloud Inference, Groq, Render (backend), Netlify (frontend).
- Adding accounts or login, conversation memory, OCR, or web search (all out of v1 scope).
- Changing limits: 25 MB per file, 10 files per batch, 30 documents per workspace, 3–500 character questions, rate limits, 30,000 total chunks.
- Changing the refusal sentence: "I couldn't find that in your notes."
- Using highlighter yellow for anything other than evidence from the student's documents.

**Contracts (changing these breaks stored data or the frontend)**
- `ID_NAMESPACE` and the id formulas in BACKEND_SCHEMA §2.
- Collection names, named vectors, embedding models, vector sizes, payload field names.
- Endpoint paths, request/response fields, error codes, SSE event names and order.
- Environment variable names.

**Security**
- Weakening upload checks (size, signature, ZIP-bomb guard), CORS origins, or the workspace filter on every query and delete.

## Free to do without asking
- Refactors inside a module that keep its contract.
- Adding or improving tests.
- Running code locally and against test/eval collections.
- Fixing typos in docs; updating HANDOVER.md and ARCHITECTURE.md to match reality.
