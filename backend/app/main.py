import hashlib
import json
import logging
import shutil
import tempfile
import threading
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from math import ceil
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid5

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import iterate_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from app import config, llm, store
from app.parsing import UploadError, detect_type
from app.schemas import AskRequest, Document, ErrorBody, ErrorCode, Health, Source

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

TMP_DIR = Path(tempfile.gettempdir()) / "coursemind"
SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
MAX_FILE_BYTES = config.MAX_FILE_MB * 1024 * 1024
FORM_OVERHEAD = 64 * 1024  # multipart boundary and part headers around the file
MAX_NAME_CHARS = 200  # BACKEND_SCHEMA §3

# One table for every HTTP error: status + fallback message (the frontend shows APP_FLOW copy by code).
ERRORS: dict[ErrorCode, tuple[int, str]] = {
    "invalid_workspace": (400, "Missing or invalid X-Workspace-Id header."),
    "validation_error": (422, "Invalid request."),
    "not_found": (404, "Document not found."),
    "still_processing": (409, "Wait until processing finishes."),
    "workspace_full": (409, f"Your library is full ({config.MAX_DOCS_PER_WORKSPACE} documents). "
                            "Delete a document to add another."),
    "file_too_large": (413, f"This file is larger than {config.MAX_FILE_MB} MB."),
    "unsupported_type": (415, "This file type isn't supported. Use PDF, .docx, or .pptx."),
    "legacy_format": (415, "Old Word and PowerPoint formats aren't supported. Save it as .docx or .pptx and add it again."),
    "bad_signature": (415, "This file doesn't look like a real PDF, Word, or PowerPoint file."),
    "upload_rate_limited": (429, "Too many uploads in the last hour. Try again later."),
    "storage_full": (503, "The demo's storage is full right now. Try again later."),
    "no_ready_documents": (409, "Add a document before asking."),
    "ask_rate_limited": (429, "Too many questions in a minute. Try again shortly."),
    "unavailable": (503, "Storage is unreachable. Try again shortly."),
}


class ApiError(Exception):
    def __init__(self, code: ErrorCode, message: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(code)
        self.code, self.message, self.headers = code, message or ERRORS[code][1], headers


# --- Rate limits and the ingest queue (in-process by design, BACKEND_SCHEMA §6) ------------

class RateLimiter:
    """Sliding window per (ip, bucket).

    ponytail: one process only and the dict keeps one entry per IP seen; move to Redis if the
    backend ever runs more than one instance.
    """

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: tuple[str, str], limit: int, window: float) -> int:
        """Record a request; return 0 if allowed, else the seconds until the next one is."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - window:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, ceil(hits[0] + window - now))
            hits.append(now)
            return 0


limiter = RateLimiter()
jobs = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingest")  # one file parsed at a time: 512 MB host


def client_ip(request: Request) -> str:
    # Render sits behind Cloudflare, which sets CF-Connecting-IP to the address that connected to it.
    # X-Forwarded-For can't be trusted: Render keeps whatever the client sent in front of the entries
    # its proxies add, so the first entry is forgeable (measured live in step 17). Without the header
    # (local runs) every request is keyed on the socket address, which only makes limits stricter.
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "unknown")


def rate_limit(request: Request, bucket: str, limits: tuple[int, int], code: ErrorCode) -> None:
    wait = limiter.hit((client_ip(request), bucket), *limits)
    if wait:
        raise ApiError(code, headers={"Retry-After": str(wait)})


def enqueue(workspace_id: str, doc_id: str, path: Path) -> None:
    jobs.submit(process, workspace_id, doc_id, path)


def process(workspace_id: str, doc_id: str, path: Path) -> None:
    """Worker job. Owns `path` from here on and always deletes it."""
    try:
        record = store.get_document(workspace_id, doc_id)
        if record is None:
            log.info("job %s skipped: document was deleted", doc_id)
            return
        store.ingest(record, path)
    except Exception:
        # ingest marks the document failed itself; this only fires if Qdrant is down too.
        # The record then stays `processing` until the next startup sweep marks it interrupted.
        log.exception("job %s failed", doc_id)
    finally:
        path.unlink(missing_ok=True)


# --- App -----------------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Missing settings are a deploy mistake: fail now. An unreachable Qdrant is an outage:
    # start anyway so /health can report 503 and the app recovers when Qdrant is back.
    missing = [n for n in ("QDRANT_URL", "QDRANT_API_KEY", "GROQ_API_KEY") if not getattr(config, n)]
    if missing:
        raise RuntimeError(f"Missing settings: {', '.join(missing)}")
    shutil.rmtree(TMP_DIR, ignore_errors=True)  # uploads left by a previous process; their records get swept
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    store.ping()
    yield
    jobs.shutdown(wait=False, cancel_futures=True)


app = FastAPI(title="CourseMind", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Workspace-Id"],
    expose_headers=["Retry-After"],
)


@app.exception_handler(ApiError)
async def api_error(_: Request, exc: ApiError) -> JSONResponse:
    body = ErrorBody(code=exc.code, message=exc.message)
    return JSONResponse(status_code=ERRORS[exc.code][0], content=body.model_dump(), headers=exc.headers)


@app.exception_handler(UploadError)
async def upload_error(request: Request, exc: UploadError) -> JSONResponse:
    return await api_error(request, ApiError(exc.code))


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(part) for part in first.get("loc", ())[1:])
    message = f"{field}: {first['msg']}" if field and "msg" in first else ERRORS["validation_error"][1]
    return await api_error(request, ApiError("validation_error", message))


def workspace(x_workspace_id: str | None = Header(default=None)) -> str:
    try:
        workspace_id = UUID(x_workspace_id or "")
    except ValueError:
        raise ApiError("invalid_workspace") from None
    if workspace_id.version != 4:
        raise ApiError("invalid_workspace")
    return str(workspace_id)  # canonical form, so any accepted spelling maps to one workspace


def qdrant_ready() -> None:
    try:
        store.ensure_ready()
    except Exception as exc:
        log.warning("qdrant unreachable: %s: %s", type(exc).__name__, exc)
        raise ApiError("unavailable") from None


# HEAD too: UptimeRobot's keep-alive monitor checks with HEAD and counted 405 as down.
@app.api_route("/health", methods=["GET", "HEAD"], response_model=Health, responses={503: {"model": ErrorBody}})
def health() -> Health:
    if not store.ping():
        raise ApiError("unavailable")
    return Health(status="ok")


@app.get("/documents", response_model=list[Document])
def list_documents(workspace_id: str = Depends(workspace), _: None = Depends(qdrant_ready)):
    return store.list_documents(workspace_id)


@app.post("/documents", response_model=Document, status_code=202, responses={200: {"model": Document}})
async def upload_document(
    request: Request, response: Response, workspace_id: str = Depends(workspace), _: None = Depends(qdrant_ready)
):
    # Check order: BACKEND_SCHEMA §7 (workspace → rate limit → size → type → sha → existing → counts).
    rate_limit(request, "upload", config.UPLOAD_LIMIT, "upload_rate_limited")
    path, filename, size, sha256 = await receive_file(request)
    record, response.status_code = await run_in_threadpool(register, workspace_id, path, filename, size, sha256)
    return record


@app.post("/documents/samples", response_model=list[Document], status_code=202, responses={200: {"model": list[Document]}})
def add_samples(
    request: Request, response: Response, workspace_id: str = Depends(workspace), _: None = Depends(qdrant_ready)
):
    """Add every file in backend/samples/ as a sample; counts as one upload (BACKEND_SCHEMA §7)."""
    rate_limit(request, "upload", config.UPLOAD_LIMIT, "upload_rate_limited")
    samples = []
    for path in sorted(p for p in SAMPLES_DIR.iterdir() if p.is_file() and not p.name.startswith(".")):
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        doc_id = str(uuid5(config.ID_NAMESPACE, f"{workspace_id}:{sha256}"))
        # detect_type raising here means a bad file was committed to samples/: a deploy error, so a 500.
        samples.append((path, detect_type(path, path.name), sha256, doc_id, store.get_document(workspace_id, doc_id)))

    missing = [s for s in samples if s[4] is None]
    if missing:
        if store.count_documents(workspace_id) + len(missing) > config.MAX_DOCS_PER_WORKSPACE:
            raise ApiError("workspace_full")
        if store.count_chunks() >= config.MAX_TOTAL_CHUNKS:
            raise ApiError("storage_full")

    records, queued = [], False
    for path, doc_type, sha256, doc_id, record in samples:
        if record is not None and record["status"] != "failed":
            records.append(record)  # already in this workspace
            continue
        if record is None:
            record = store.create_document(workspace_id, doc_id, path.name, doc_type, path.stat().st_size, sha256, is_sample=True)
        else:
            store.set_status(doc_id, "queued")
            record["status"], record["error_code"] = "queued", None
        # The worker deletes the file it is given, so it gets a temp copy; the sample itself stays.
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        fd, copy_name = tempfile.mkstemp(dir=TMP_DIR)
        with open(fd, "wb") as out:
            out.write(path.read_bytes())
        enqueue(workspace_id, doc_id, Path(copy_name))
        records.append(record)
        queued = True
    response.status_code = 202 if queued else 200
    return records


@app.delete("/documents/{doc_id}", status_code=204, response_class=Response)
def delete_document(doc_id: UUID, workspace_id: str = Depends(workspace), _: None = Depends(qdrant_ready)) -> Response:
    record = store.get_document(workspace_id, str(doc_id))
    if record is None:
        raise ApiError("not_found")
    if record["status"] in ("queued", "processing"):
        raise ApiError("still_processing")
    store.delete_document(workspace_id, str(doc_id))
    return Response(status_code=204)


@app.post("/ask", response_class=StreamingResponse, responses={200: {"content": {"text/event-stream": {}}}})
def ask(
    body: AskRequest, request: Request, workspace_id: str = Depends(workspace), _: None = Depends(qdrant_ready)
) -> StreamingResponse:
    # Everything that can fail with a normal HTTP error happens before the stream starts (BACKEND_SCHEMA §7).
    started = time.perf_counter()
    rate_limit(request, "ask", config.ASK_LIMIT, "ask_rate_limited")
    try:
        ready_ids = [r["id"] for r in store.list_documents(workspace_id) if r["status"] == "ready"]
        sources = store.retrieve(body.question, workspace_id, ready_ids, config.RETRIEVAL_MODE, config.TOP_K)
    except Exception as exc:
        log.warning("ask: qdrant failed: %s: %s", type(exc).__name__, exc)
        raise ApiError("unavailable") from None
    if not ready_ids:
        raise ApiError("no_ready_documents")
    log.info("ask: %d of %d ready documents matched, %d sources in %.0f ms",
             len({s.doc_id for s in sources}), len(ready_ids), len(sources), (time.perf_counter() - started) * 1000)
    return StreamingResponse(
        answer_events(body.question, sources, started),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def sse(event: str, data: object) -> str:
    # json.dumps escapes newlines, so each event's data stays on one line as SSE requires.
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def answer_events(question: str, sources: list[Source], started: float) -> AsyncIterator[str]:
    """SSE body: exactly one `sources`, zero or more `token`, then exactly one `done` or `error`."""
    yield sse("sources", [s.model_dump(mode="json") for s in sources])
    if not sources:  # nothing to ground an answer on: refuse without calling the LLM (TRD §8.5)
        yield sse("token", {"t": config.REFUSAL})
        yield sse("done", {"refused": True, "model": None})
        return

    pieces, model, answer = None, None, []
    first_ms, outcome = None, "disconnected"
    try:
        model, pieces = await run_in_threadpool(llm.stream_answer, question, sources)
        async for piece in iterate_in_threadpool(pieces):
            if first_ms is None:
                first_ms = (time.perf_counter() - started) * 1000
            answer.append(piece)
            yield sse("token", {"t": piece})
        outcome = "done"
    except llm.LLMError as err:
        outcome = err.code
        yield sse("error", {"code": err.code})
        return
    finally:
        if pieces is not None:
            pieces.close()  # visitor pressed Stop (client gone): drop the Groq stream so generation stops
        log.info("ask: %s, model %s, %d pieces, first piece %s ms, total %.0f ms", outcome, model, len(answer),
                 f"{first_ms:.0f}" if first_ms is not None else "-", (time.perf_counter() - started) * 1000)
    yield sse("done", {"refused": "".join(answer).strip() == config.REFUSAL, "model": model})


# --- Upload helpers ------------------------------------------------------------------------

async def receive_file(request: Request) -> tuple[Path, str, int, str]:
    """Stream the one `file` part to a temp file, stopping as soon as the body passes the size cap."""
    cap = MAX_FILE_BYTES + FORM_OVERHEAD
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > cap:
        raise ApiError("file_too_large")

    async def capped():
        received = 0
        async for chunk in request.stream():
            received += len(chunk)
            if received > cap:
                raise ApiError("file_too_large")
            yield chunk

    bad_form = "Send one file in a multipart/form-data field named 'file'."
    if not request.headers.get("content-type", "").startswith("multipart/form-data"):
        raise ApiError("validation_error", bad_form)  # Starlette's parser raises KeyError without the header
    try:
        form = await MultiPartParser(request.headers, capped(), max_files=1, max_fields=0).parse()
    except MultiPartException:
        raise ApiError("validation_error", bad_form) from None
    try:
        upload = form.get("file")
        name = clean_name(upload.filename) if isinstance(upload, UploadFile) and upload.filename else ""
        if not name:
            raise ApiError("validation_error", bad_form)
        fd, temp_name = tempfile.mkstemp(dir=TMP_DIR)
        path = Path(temp_name)
        try:
            digest, size = hashlib.sha256(), 0
            with open(fd, "wb") as out:
                while chunk := await upload.read(1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
                    out.write(chunk)
            if size > MAX_FILE_BYTES:
                raise ApiError("file_too_large")
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return path, name, size, digest.hexdigest()
    finally:
        await form.close()


def clean_name(filename: str) -> str:
    """Drop any client path and keep at most 200 chars, extension included."""
    name = PurePosixPath(filename.replace("\\", "/")).name.strip()
    if len(name) > MAX_NAME_CHARS:
        suffix = PurePosixPath(name).suffix[:10]
        name = name[: MAX_NAME_CHARS - len(suffix)] + suffix
    return name


def register(workspace_id: str, path: Path, filename: str, size: int, sha256: str) -> tuple[store.Record, int]:
    """Type check, dedup and capacity checks, then queue. Deletes `path` unless a job took it."""
    queued = False
    try:
        doc_type = detect_type(path, filename)
        doc_id = str(uuid5(config.ID_NAMESPACE, f"{workspace_id}:{sha256}"))
        record = store.get_document(workspace_id, doc_id)
        if record is not None and record["status"] != "failed":
            return record, 200  # same file already in this workspace
        if record is None:
            if store.count_documents(workspace_id) >= config.MAX_DOCS_PER_WORKSPACE:
                raise ApiError("workspace_full")
            if store.count_chunks() >= config.MAX_TOTAL_CHUNKS:
                raise ApiError("storage_full")
            record = store.create_document(workspace_id, doc_id, filename, doc_type, size, sha256, is_sample=False)
        else:  # failed before: try again with this upload
            store.set_status(doc_id, "queued")
            record["status"], record["error_code"] = "queued", None
        enqueue(workspace_id, doc_id, path)
        queued = True
        return record, 202
    finally:
        if not queued:
            path.unlink(missing_ok=True)
