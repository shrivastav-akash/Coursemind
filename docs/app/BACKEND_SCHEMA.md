# CourseMind — Backend Schema

**Status:** Draft v1 · **Date:** 2026-09-27 · **Based on:** TRD v1.1, APP_FLOW v1

The data model and API contract. Where this file and the TRD differ on a field, type, or code, **this file wins**; update the TRD to match.

---

## 1. Where data lives

| Store | What | Lifetime |
|---|---|---|
| Qdrant collection `documents` | One record per uploaded file (the library) | Durable |
| Qdrant collection `chunks` | Passages with their vectors | Durable; deleted with their document |
| Qdrant collections `eval_400`, `eval_700`, `eval_1000` | Evaluation copies of the sample files | Created and deleted by `eval/run_eval.py` |
| Backend memory | Job queue, rate-limit counters, daily-limit flags (§6) | Lost on restart (by design) |
| Backend temp disk `/tmp/coursemind/` | Uploaded file while it waits for / goes through processing | Deleted after processing, always |
| Backend repo `backend/samples/` | The 3 sample files | Static, in git |
| Browser `localStorage` | Workspace id | Until the visitor clears site data |
| Browser memory | Current thread (questions, answers, sources) | Lost on reload (by design) |
| Frontend code `lib/samples.ts` | 3 suggested questions for the sample files | Static, in git |

There is no SQL database. Qdrant payloads hold all structured data.

---

## 2. Entities and relationships

```
Workspace  (not stored as a record: a UUID v4 held by the browser)
   │ 1
   │
   │ N   documents.workspace_id
Document   (collection "documents", point id = doc_id)
   │ 1
   │
   │ N   chunks.doc_id
Chunk      (collection "chunks", point id = chunk id)
```

- **Workspace → Document:** one-to-many via `documents.workspace_id`. Max 30 documents per workspace.
- **Document → Chunk:** one-to-many via `chunks.doc_id`. `chunks.workspace_id`, `doc_name`, and `doc_type` are copied from the document at ingest (a document's name and type never change), so retrieval needs no join.
- **Cascade delete (application-enforced, Qdrant has no foreign keys):** delete the document record first, then its chunks by filter `workspace_id AND doc_id`. If the second step fails, the leftover chunks are harmless: retrieval only searches doc ids that are `ready` in `documents` (TRD §8.1).
- **Re-ingest is idempotent:** before upserting, the worker deletes any existing chunks with the same `doc_id`, so a re-processed file never mixes old and new passages.

### Deterministic ids

| Id | Formula | Why |
|---|---|---|
| `doc_id` | `uuid5(ID_NAMESPACE, f"{workspace_id}:{sha256}")` | Same file in the same workspace → same id → duplicate detection for free (PRD FR-6). |
| chunk id | `uuid5(ID_NAMESPACE, f"{doc_id}:{chunk_index}")` | Retries overwrite instead of duplicating. |
| `ID_NAMESPACE` | `UUID("ed1bef70-990c-4c4f-b76f-28c158ed0c8f")` | Fixed constant in `config.py`. **Never change it**: every existing id depends on it. |
| Eval workspace id | `UUID("860e1106-bd9b-47f8-9f4d-37eb144b909d")` | Fixed id used only by `run_eval.py`. |

---

## 3. Collection `documents`

Payload-only registry: `vectors_config={}` (no vectors).

| Field | Type | Required | Rules / example |
|---|---|---|---|
| *(point id)* | UUID | yes | `doc_id` (§2) |
| `workspace_id` | keyword (UUID v4 string) | yes | `"3f6c…"` |
| `name` | string | yes | Original file name, path stripped, 1–200 chars. `"OS_Lecture3.pdf"` |
| `type` | keyword | yes | `pdf` \| `docx` \| `pptx` |
| `size_bytes` | integer | yes | 1 – 26,214,400 (25 MB) |
| `sha256` | keyword | yes | 64 lowercase hex chars |
| `is_sample` | bool | yes | `true` only for files added by `POST /documents/samples` |
| `status` | keyword | yes | `queued` \| `processing` \| `ready` \| `failed` |
| `error_code` | keyword \| null | yes (null allowed) | Non-null **only** when `status = failed`; one of the document codes in §5 |
| `chunks` | integer | yes | `0` until ready; `> 0` when ready |
| `created_at` | string (RFC 3339, UTC) | yes | `"2026-09-27T10:15:02Z"` |
| `updated_at` | string (RFC 3339, UTC) | yes | Changes on every status change |

**Indexes:** `workspace_id` (keyword, `is_tenant=true`), `status` (keyword; used by the startup sweep).

**Status lifecycle**

```
            upload accepted
                  │
                  ▼
   ┌──────────► queued ──► processing ──► ready
   │              │            │
   │              └────┬───────┘
   │                   ▼
   │                failed (error_code)
   │                   │
   └───────────────────┘  same file uploaded again
```
- Server start: every `queued` / `processing` record → `failed` with `error_code = interrupted`.
- `ready` and `failed` are the only states a visitor can delete; `queued` / `processing` → 409 `still_processing`.

---

## 4. Collection `chunks`

| Named vector | Source text → model (Qdrant Cloud Inference) | Config |
|---|---|---|
| `dense` | `sentence-transformers/all-MiniLM-L6-v2` | 384 dims, cosine, HNSW on |
| `sparse` | `qdrant/bm25` | sparse, `modifier=IDF` |
| `colbert` | `answerdotai/answerai-colbert-small-v1` | multivector 96 dims, `MAX_SIM`, HNSW off (`m=0`), `on_disk=true`, `float16` |

| Field | Type | Required | Rules / example |
|---|---|---|---|
| *(point id)* | UUID | yes | chunk id (§2) |
| `workspace_id` | keyword | yes | Copied from document |
| `doc_id` | keyword (UUID string) | yes | Parent document |
| `doc_name` | string | yes | Copied from document, `"DBMS.pptx"` |
| `doc_type` | keyword | yes | `pdf` \| `docx` \| `pptx` |
| `location` | string | yes | Display label, 1–120 chars: `"p. 12"`, `"slide 4"`, `"§ Normal forms"`, `"§ (start)"` |
| `order` | integer | yes | Page number, slide number, or section index (1-based); for sorting |
| `chunk_index` | integer | yes | 0-based position within the document |
| `text` | string | yes | 1 – `CHUNK_SIZE + CHUNK_OVERLAP` chars, never whitespace-only |

**Indexes:** `workspace_id` (keyword, `is_tenant=true`), `doc_id` (keyword).

**Eval collections** `eval_{size}` use exactly this schema, with `workspace_id` = the eval workspace id.

---

## 5. Error codes

Every HTTP error body is:

```json
{ "code": "workspace_full", "message": "Your library is full (30 documents)." }
```

`code` is stable and machine-readable; the frontend shows the APP_FLOW §5 copy for it. `message` is a plain fallback for unknown codes and for curl users.

| Code | Where | HTTP / channel | APP_FLOW copy (summary) |
|---|---|---|---|
| `invalid_workspace` | any workspace route | 400 | (never shown; frontend regenerates the id) |
| `validation_error` | any route | 422 | "Type at least 3 characters." / field-level text |
| `not_found` | `DELETE /documents/{id}` | 404 | "Couldn't delete …. Try again." |
| `still_processing` | `DELETE /documents/{id}` | 409 | "Wait until processing finishes." |
| `workspace_full` | upload, samples | 409 | "Your library is full (30 documents)…" |
| `file_too_large` | upload | 413 | "This file is larger than 25 MB." |
| `unsupported_type` | upload | 415 | "This file type isn't supported…" |
| `legacy_format` | upload | 415 | "Old Word and PowerPoint formats aren't supported…" |
| `bad_signature` | upload | 415 | "This file doesn't look like a real PDF, Word, or PowerPoint file." |
| `upload_rate_limited` | upload, samples | 429 + `Retry-After` | "Too many uploads in the last hour…" |
| `storage_full` | upload, samples | 503 | "The demo's storage is full right now…" |
| `no_ready_documents` | `POST /ask` | 409 | "Add a document before asking." |
| `ask_rate_limited` | `POST /ask` | 429 + `Retry-After` | "Too many questions in a minute…" |
| `unavailable` | `GET /health` | 503 | Server banner |
| `no_text` | document `error_code` | — | "No selectable text found…" |
| `unreadable` | document `error_code` | — | "Couldn't read this file…" |
| `interrupted` | document `error_code` | — | "Processing was interrupted by a server restart…" |
| `llm_busy` | `/ask` stream `error` event | SSE | "CourseMind is busy right now…" |
| `daily_limit` | `/ask` stream `error` event | SSE | "The demo has reached today's question limit…" |
| `llm_error` | `/ask` stream `error` event | SSE | "The answer was interrupted." |

Client-only failures (no server code): network drop during upload or stream, user **Stop**.

---

## 6. In-memory backend state

| Name | Shape | Rule |
|---|---|---|
| Job queue | `ThreadPoolExecutor(max_workers=1)`; job = `(doc_id, workspace_id, temp_path, type)` | One file parsed at a time. Worker re-reads the document record first and skips if it was deleted. |
| Rate limiter | `dict[(ip, bucket)] → deque[timestamp]` | `ask`: 5 per 60 s. `upload`: 30 per 3,600 s (samples call counts as 1). IP = first entry of `X-Forwarded-For`, else socket address. |
| Daily-limit flags | `dict[model] → exhausted_until (epoch s)` | Set on a daily Groq 429 (TRD §8.4); model skipped until then. |

All three reset on restart. `ponytail:` single process only; move to Redis if the backend ever runs more than one instance.

---

## 7. API

**Base URL:** `NEXT_PUBLIC_API_URL` (Render service URL). JSON uses UTF-8.

**Auth.** There are no user accounts. Routes marked **Workspace** require header `X-Workspace-Id: <UUID v4>`; it acts as a bearer capability, and every read or write is filtered by it. Missing or malformed → 400 `invalid_workspace`. **None** = open.

**CORS.** Origins from `ALLOWED_ORIGINS`; methods `GET, POST, DELETE`; headers `Content-Type, X-Workspace-Id`; exposes `Retry-After`.

### Summary

| Method | Path | Auth | Input | Success output |
|---|---|---|---|---|
| GET | `/health` | None | — | 200 `Health` |
| GET | `/documents` | Workspace | — | 200 `Document[]` |
| POST | `/documents` | Workspace | multipart `file` | 202 `Document` (new or re-queued) · 200 `Document` (already present) |
| DELETE | `/documents/{doc_id}` | Workspace | path `doc_id` | 204 (no body) |
| POST | `/documents/samples` | Workspace | — | 202 `Document[]` (any new) · 200 `Document[]` (all already present) |
| POST | `/ask` | Workspace | JSON `AskRequest` | 200 `text/event-stream` |

### `GET /health`
- Pings Qdrant (cheap collection lookup).
- 200 `{"status": "ok"}`; 503 `{"code": "unavailable", "message": "…"}`.
- Used by: header status, server banner, UptimeRobot.

### `GET /documents`
- Returns every document in the workspace, newest first (`created_at` desc; sorted in Python, ≤ 30 items).
- Errors: 400 `invalid_workspace`.

### `POST /documents`
- Body: `multipart/form-data`, one field `file` (one file per request; the browser sends up to 2 in parallel).
- Server checks, in order: workspace id → rate limit → size while streaming to disk (≤ 25 MB) → extension + content signature (+ ZIP uncompressed size ≤ 200 MB) → `sha256` → existing record → workspace count → global chunk count.
- Existing record `queued` / `processing` / `ready` → 200 with it. Existing `failed` → re-queued, 202.
- New → record written as `queued`, job queued, 202.
- Errors: 400 `invalid_workspace` · 409 `workspace_full` · 413 `file_too_large` · 415 `unsupported_type` / `legacy_format` / `bad_signature` · 422 `validation_error` (no `file` field) · 429 `upload_rate_limited` · 503 `storage_full`.

### `DELETE /documents/{doc_id}`
- Deletes the record, then its chunks (§2).
- Errors: 400 `invalid_workspace` · 404 `not_found` (unknown id **or** belongs to another workspace; same answer so ids can't be probed) · 409 `still_processing`.

### `POST /documents/samples`
- Adds every file in `backend/samples/` with `is_sample = true`, using the same pipeline as upload (from the signature check on). Counts as one upload for rate limiting.
- 202 if at least one sample was new or re-queued; 200 if all three were already present (APP_FLOW J2 toast).
- Errors: 400 · 409 `workspace_full` (not enough room for the missing samples) · 429 `upload_rate_limited` · 503 `storage_full`.

### `POST /ask`
- Body: `{"question": "What is 3NF?"}`; trimmed, 3–500 characters.
- Pre-stream errors (normal JSON body): 400 `invalid_workspace` · 409 `no_ready_documents` · 422 `validation_error` · 429 `ask_rate_limited`.
- Stream: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`.

**Event order:** exactly one `sources` → zero or more `token` → exactly one of `done` or `error`.

| Event | `data` | Notes |
|---|---|---|
| `sources` | `Source[]` | Sent before any text. `[]` when retrieval found nothing (answer will be the refusal). |
| `token` | `{"t": string}` | Text to append. |
| `done` | `{"refused": bool, "model": string \| null}` | `model` is `null` when no LLM was called. |
| `error` | `{"code": "llm_busy" \| "daily_limit" \| "llm_error"}` | Partial text already sent stays on screen. |

Example:
```
event: sources
data: [{"n":1,"doc_id":"a1…","doc_name":"DBMS.pptx","doc_type":"pptx","location":"slide 14","text":"Third normal form: …"}]

event: token
data: {"t":"3NF adds one rule: "}

event: done
data: {"refused":false,"model":"openai/gpt-oss-20b"}
```

If the client disconnects (user presses **Stop**), the server stops generating.

---

## 8. Types

### Backend (`app/schemas.py`, Pydantic v2)

```python
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

DocType = Literal["pdf", "docx", "pptx"]
Status = Literal["queued", "processing", "ready", "failed"]
DocErrorCode = Literal["no_text", "unreadable", "interrupted"]
ErrorCode = Literal[
    "invalid_workspace", "validation_error", "not_found", "still_processing",
    "workspace_full", "file_too_large", "unsupported_type", "legacy_format",
    "bad_signature", "upload_rate_limited", "storage_full", "no_ready_documents",
    "ask_rate_limited", "unavailable",
]
StreamErrorCode = Literal["llm_busy", "daily_limit", "llm_error"]

class Document(BaseModel):
    id: UUID
    name: str
    type: DocType
    size_bytes: int
    is_sample: bool
    status: Status
    error_code: DocErrorCode | None
    chunks: int
    created_at: datetime

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)  # stripped before validation

class Source(BaseModel):
    n: int                    # 1-based, matches [n] in the answer
    doc_id: UUID
    doc_name: str
    doc_type: DocType
    location: str
    text: str

class ErrorBody(BaseModel):
    code: ErrorCode
    message: str

class Health(BaseModel):
    status: Literal["ok"]
```

### Frontend (`lib/types.ts`, hand-kept mirror)

```ts
export type DocType = "pdf" | "docx" | "pptx";
export type Status = "queued" | "processing" | "ready" | "failed";
export type DocErrorCode = "no_text" | "unreadable" | "interrupted";
export type StreamErrorCode = "llm_busy" | "daily_limit" | "llm_error";

export interface Document {
  id: string; name: string; type: DocType; size_bytes: number; is_sample: boolean;
  status: Status; error_code: DocErrorCode | null; chunks: number; created_at: string;
}
export interface Source {
  n: number; doc_id: string; doc_name: string; doc_type: DocType; location: string; text: string;
}
export type AskEvent =
  | { event: "sources"; data: Source[] }
  | { event: "token"; data: { t: string } }
  | { event: "done"; data: { refused: boolean; model: string | null } }
  | { event: "error"; data: { code: StreamErrorCode } };
export interface ErrorBody { code: string; message: string }
```

Client-side upload rows also need states the server never stores: `uploading`, `waiting`, and client-rejected files (`unsupported_type`, `legacy_format`, `file_too_large`, network failure). Keep them in UI state only.

---

## 9. Limits (single list)

| Limit | Value | Enforced in | Mirrored in frontend (`lib/limits.ts`) |
|---|---|---|---|
| File size | 25 MB | `POST /documents` | yes (pre-check) |
| Files per batch | 10 | frontend only | yes |
| Documents per workspace | 30 | `POST /documents`, samples | yes (header "3 of 30") |
| Total chunks (all workspaces) | 30,000 | `POST /documents`, samples | no |
| ZIP uncompressed size | 200 MB | `POST /documents` | no |
| Question length | 3–500 chars | `AskRequest` | yes (counter from 450) |
| Asks per IP | 5 / min | `POST /ask` | no |
| Uploads per IP | 30 / hour | `POST /documents`, samples | no |

Frontend mirrors must match `config.py`; change both together.

---

## 10. Screen coverage

Every APP_FLOW screen has the data and endpoints it needs.

| Screen | Data it shows | Endpoint / source |
|---|---|---|
| S1 Workspace, desktop | Server status, library, thread | `GET /health`, `GET /documents`, `POST /ask` |
| S2 Workspace, mobile | Same as S1; count on "Documents (n)" | same as S1 |
| S3 Library panel | `Document[]` (name, type, status, `error_code`, chunks, `is_sample`), "n of 30" | `GET /documents` (polled every 2 s while any queued/processing), `POST /documents`, `DELETE /documents/{id}`, `POST /documents/samples`, `lib/limits.ts` |
| S4 Library sheet | Same as S3 | Same as S3 |
| S5 First-visit empty state | Empty `Document[]` | `GET /documents` → `[]` |
| S6 Waiting-for-ready | Documents exist, none `ready` | `GET /documents` |
| S7 Thread | Messages in browser memory; suggested questions when every document `is_sample` | `POST /ask` stream; `lib/samples.ts` |
| S8 Answer block | Progress line (count of ready docs, then `sources.length`), tokens, `done.refused`, stream error codes | `POST /ask` events; `GET /documents` for "Searching 3 documents…" |
| S9 Source passage | `Source` (name, type, location, full text); "since removed" note when `doc_id` not in current library | `sources` event + `GET /documents` |
| S10 Delete confirmation | Document name | `DELETE /documents/{id}` |
| S11 Drop overlay | None | Client only, then `POST /documents` |
| S12 Server status banner | Health result, retry timer | `GET /health` |
| S13 Not found page | None | Static `404.html` from Next.js export |
| Toasts (J2, J3, J7) | Duplicate / samples-present / deleted | `POST /documents` 200, `POST /documents/samples` 200, `DELETE` 204 |
