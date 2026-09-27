import hashlib
from uuid import uuid1, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient

from app import config, main, store
from tests.files import make_pdf

WS, OTHER_WS = str(uuid4()), str(uuid4())


class FakeStore:
    """In-memory stand-in for the Qdrant-backed registry functions the routes use."""

    def __init__(self):
        self.records: dict[str, dict] = {}
        self.total_chunks = 0
        self.jobs: list[tuple] = []
        self.clock = 0

    def ensure_ready(self):
        pass

    def get_document(self, workspace_id, doc_id):
        record = self.records.get(doc_id)
        return dict(record) if record and record["workspace_id"] == workspace_id else None

    def list_documents(self, workspace_id):
        mine = [dict(r) for r in self.records.values() if r["workspace_id"] == workspace_id]
        return sorted(mine, key=lambda r: r["created_at"], reverse=True)

    def create_document(self, workspace_id, doc_id, name, doc_type, size_bytes, sha256, is_sample):
        self.clock += 1
        stamp = f"2026-09-27T10:00:{self.clock:02d}.000000Z"
        self.records[doc_id] = dict(
            id=doc_id, workspace_id=workspace_id, name=name, type=doc_type, size_bytes=size_bytes, sha256=sha256,
            is_sample=is_sample, status="queued", error_code=None, chunks=0, created_at=stamp, updated_at=stamp,
        )
        return dict(self.records[doc_id])

    def set_status(self, doc_id, status, error_code=None, chunks=None):
        self.records[doc_id].update(status=status, error_code=error_code)
        if chunks is not None:
            self.records[doc_id]["chunks"] = chunks

    def count_documents(self, workspace_id):
        return sum(r["workspace_id"] == workspace_id for r in self.records.values())

    def count_chunks(self):
        return self.total_chunks

    def delete_document(self, workspace_id, doc_id):
        del self.records[doc_id]


@pytest.fixture
def api(monkeypatch, tmp_path):
    fake = FakeStore()
    for name in ("ensure_ready", "get_document", "list_documents", "create_document", "set_status",
                 "count_documents", "count_chunks", "delete_document"):
        monkeypatch.setattr(store, name, getattr(fake, name))
    monkeypatch.setattr(main, "enqueue", lambda ws, doc_id, path: fake.jobs.append((ws, doc_id, path)))
    monkeypatch.setattr(main, "limiter", main.RateLimiter())
    monkeypatch.setattr(main, "TMP_DIR", tmp_path / "uploads")
    (tmp_path / "uploads").mkdir()
    fake.client = TestClient(main.app)  # no `with`: lifespan does not run
    fake.tmp = tmp_path / "uploads"
    return fake


@pytest.fixture
def pdf(tmp_path) -> bytes:
    return make_pdf(tmp_path / "notes.pdf", ["Deadlock needs four conditions."]).read_bytes()


def upload(api, name, content, workspace_id=WS, **headers):
    return api.client.post("/documents", files={"file": (name, content)},
                           headers={"X-Workspace-Id": workspace_id, **headers})


def leftover_files(api) -> list:
    return sorted(api.tmp.iterdir())


# --- Workspace header -----------------------------------------------------------------------

@pytest.mark.parametrize("header", [None, "", "not-a-uuid", str(uuid1())])
def test_workspace_header_must_be_a_uuid4(api, header):
    headers = {} if header is None else {"X-Workspace-Id": header}

    response = api.client.get("/documents", headers=headers)

    assert response.status_code == 400
    assert response.json() == {"code": "invalid_workspace", "message": main.ERRORS["invalid_workspace"][1]}


def test_workspace_id_is_normalised(api, pdf):
    upload(api, "notes.pdf", pdf, workspace_id=WS.upper())

    assert len(api.client.get("/documents", headers={"X-Workspace-Id": WS}).json()) == 1


# --- Upload: success paths ------------------------------------------------------------------

def test_new_upload_is_queued(api, pdf):
    response = upload(api, "C:\\Users\\me\\Lecture 1.pdf", pdf)

    assert response.status_code == 202
    body = response.json()
    expected_id = str(uuid5(config.ID_NAMESPACE, f"{WS}:{hashlib.sha256(pdf).hexdigest()}"))
    assert body == {"id": expected_id, "name": "Lecture 1.pdf", "type": "pdf", "size_bytes": len(pdf),
                    "is_sample": False, "status": "queued", "error_code": None, "chunks": 0,
                    "created_at": body["created_at"]}
    [(workspace_id, doc_id, path)] = api.jobs
    assert (workspace_id, doc_id) == (WS, expected_id)
    assert path.parent == api.tmp and path.read_bytes() == pdf


def test_same_file_again_returns_the_existing_record(api, pdf):
    first = upload(api, "notes.pdf", pdf).json()

    again = upload(api, "renamed.pdf", pdf)

    assert again.status_code == 200 and again.json() == first
    assert len(api.jobs) == 1
    assert leftover_files(api) == [api.jobs[0][2]]  # only the queued job's file remains


def test_failed_document_is_requeued(api, pdf):
    doc_id = upload(api, "notes.pdf", pdf).json()["id"]
    api.set_status(doc_id, "failed", error_code="unreadable")

    response = upload(api, "notes.pdf", pdf)

    assert response.status_code == 202
    assert (response.json()["status"], response.json()["error_code"]) == ("queued", None)
    assert api.records[doc_id]["status"] == "queued"
    assert len(api.jobs) == 2


def test_same_file_in_another_workspace_is_a_separate_document(api, pdf):
    mine = upload(api, "notes.pdf", pdf).json()
    theirs = upload(api, "notes.pdf", pdf, workspace_id=OTHER_WS)

    assert theirs.status_code == 202 and theirs.json()["id"] != mine["id"]


# --- Upload: rejections ---------------------------------------------------------------------

@pytest.mark.parametrize("name, content, code", [
    ("notes.txt", b"plain text", "unsupported_type"),
    ("old.doc", b"%PDF-1.7 anything", "legacy_format"),
    ("fake.pdf", b"not a pdf at all", "bad_signature"),
    ("empty.docx", b"", "bad_signature"),
])
def test_wrong_file_types_are_415(api, name, content, code):
    response = upload(api, name, content)

    assert (response.status_code, response.json()["code"]) == (415, code)
    assert api.jobs == [] and api.records == {} and leftover_files(api) == []


def test_size_cap(api, monkeypatch):
    monkeypatch.setattr(main, "MAX_FILE_BYTES", 1000)
    monkeypatch.setattr(main, "FORM_OVERHEAD", 300)
    at_cap = b"%PDF-" + b"x" * 995

    assert upload(api, "exact.pdf", at_cap).status_code == 202
    for content in (at_cap + b"x", at_cap * 5):  # just over (checked after parsing) / far over (Content-Length)
        response = upload(api, "big.pdf", content)
        assert (response.status_code, response.json()["code"]) == (413, "file_too_large")
    assert leftover_files(api) == [api.jobs[0][2]]


def test_size_cap_without_content_length(api, monkeypatch):
    """A chunked upload has no Content-Length, so only the byte count on the stream can catch it.

    (The test client buffers the whole body; that the server stops reading early is checked
    against a real server, see DECISIONS.)
    """
    monkeypatch.setattr(main, "MAX_FILE_BYTES", 1000)
    monkeypatch.setattr(main, "FORM_OVERHEAD", 300)
    head = (b"--X\r\nContent-Disposition: form-data; name=\"file\"; filename=\"big.pdf\"\r\n"
            b"Content-Type: application/pdf\r\n\r\n%PDF-")

    def body():
        yield head
        for _ in range(100):
            yield b"x" * 1024
        yield b"\r\n--X--\r\n"

    response = api.client.post("/documents", content=body(), headers={
        "X-Workspace-Id": WS, "Content-Type": "multipart/form-data; boundary=X"})

    assert (response.status_code, response.json()["code"]) == (413, "file_too_large")
    assert leftover_files(api) == [] and api.jobs == []


@pytest.mark.parametrize("request_kwargs", [
    {"files": {"other": ("notes.pdf", b"%PDF-")}},  # wrong field name
    {"data": {"file": "not a file"}},  # urlencoded form, no file
    {"content": b"%PDF-raw body"},  # no Content-Type at all
    {"files": {"file": ("", b"%PDF-")}},  # no file name
])
def test_missing_file_is_422(api, request_kwargs):
    response = api.client.post("/documents", headers={"X-Workspace-Id": WS}, **request_kwargs)

    assert (response.status_code, response.json()["code"]) == (422, "validation_error")
    assert leftover_files(api) == []


def test_upload_rate_limit_per_ip(api, pdf, monkeypatch):
    monkeypatch.setattr(config, "UPLOAD_LIMIT", (2, 3600))

    assert upload(api, "a.pdf", pdf).status_code == 202
    assert upload(api, "a.pdf", pdf).status_code == 200  # duplicates count too
    limited = upload(api, "a.pdf", pdf)

    assert (limited.status_code, limited.json()["code"]) == (429, "upload_rate_limited")
    assert 3590 <= int(limited.headers["Retry-After"]) <= 3600
    # Keyed on the first X-Forwarded-For entry (the client, as added by Render's proxy).
    assert upload(api, "a.pdf", pdf, **{"X-Forwarded-For": "203.0.113.9, 10.0.0.1"}).status_code == 200


def test_workspace_full_is_409(api, pdf, monkeypatch):
    monkeypatch.setattr(store, "count_documents", lambda _ws: config.MAX_DOCS_PER_WORKSPACE)

    response = upload(api, "notes.pdf", pdf)

    assert (response.status_code, response.json()["code"]) == (409, "workspace_full")
    assert api.records == {} and leftover_files(api) == []


def test_storage_full_is_503(api, pdf):
    api.total_chunks = config.MAX_TOTAL_CHUNKS

    response = upload(api, "notes.pdf", pdf)

    assert (response.status_code, response.json()["code"]) == (503, "storage_full")
    assert api.records == {} and leftover_files(api) == []


def test_qdrant_down_is_503(api, pdf, monkeypatch):
    def down():
        raise ConnectionError("qdrant down")

    monkeypatch.setattr(store, "ensure_ready", down)

    for response in (api.client.get("/documents", headers={"X-Workspace-Id": WS}), upload(api, "notes.pdf", pdf)):
        assert (response.status_code, response.json()["code"]) == (503, "unavailable")


# --- List and delete ------------------------------------------------------------------------

def test_list_is_newest_first_scoped_and_hides_internal_fields(api, tmp_path):
    older = upload(api, "older.pdf", make_pdf(tmp_path / "1.pdf", ["one"]).read_bytes()).json()
    newer = upload(api, "newer.pdf", make_pdf(tmp_path / "2.pdf", ["two"]).read_bytes()).json()
    upload(api, "theirs.pdf", make_pdf(tmp_path / "3.pdf", ["three"]).read_bytes(), workspace_id=OTHER_WS)

    listed = api.client.get("/documents", headers={"X-Workspace-Id": WS}).json()

    assert [d["id"] for d in listed] == [newer["id"], older["id"]]
    assert "sha256" not in listed[0] and "workspace_id" not in listed[0]


def test_delete_rules(api, pdf, tmp_path):
    doc_id = upload(api, "notes.pdf", pdf).json()["id"]
    theirs = upload(api, "t.pdf", make_pdf(tmp_path / "t.pdf", ["t"]).read_bytes(), workspace_id=OTHER_WS).json()["id"]

    def delete(target, workspace_id=WS):
        return api.client.delete(f"/documents/{target}", headers={"X-Workspace-Id": workspace_id})

    assert delete(str(uuid4())).json()["code"] == "not_found"
    assert delete(theirs).status_code == 404  # another workspace's id looks exactly like an unknown one
    assert delete("not-a-uuid").status_code == 422
    for status in ("queued", "processing"):
        api.set_status(doc_id, status)
        assert (delete(doc_id).status_code, delete(doc_id).json()["code"]) == (409, "still_processing")

    api.set_status(doc_id, "ready", chunks=3)
    response = delete(doc_id)

    assert response.status_code == 204 and response.content == b""
    assert doc_id not in api.records and theirs in api.records


# --- Worker and rate limiter ----------------------------------------------------------------

def test_worker_ingests_and_always_deletes_the_file(monkeypatch, tmp_path):
    ingested = []
    records = {"doc-1": {"id": "doc-1"}}
    monkeypatch.setattr(store, "get_document", lambda _ws, doc_id: records.get(doc_id))
    monkeypatch.setattr(store, "ingest", lambda record, path: ingested.append((record["id"], path.read_bytes())))

    ok, deleted, broken = (tmp_path / name for name in ("ok", "deleted", "broken"))
    for path in (ok, deleted, broken):
        path.write_bytes(b"data")

    main.process(WS, "doc-1", ok)
    main.process(WS, "gone", deleted)  # record deleted while queued: skipped
    monkeypatch.setattr(store, "ingest", lambda *_: (_ for _ in ()).throw(ConnectionError("qdrant down")))
    main.process(WS, "doc-1", broken)  # failure is logged, not raised

    assert ingested == [("doc-1", b"data")]
    assert not ok.exists() and not deleted.exists() and not broken.exists()


def test_rate_limiter_window_slides(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(main.time, "monotonic", lambda: now[0])
    limiter = main.RateLimiter()

    assert [limiter.hit(("ip", "b"), 2, 60) for _ in range(3)] == [0, 0, 60]
    now[0] += 30
    assert limiter.hit(("ip", "b"), 2, 60) == 30
    assert limiter.hit(("other-ip", "b"), 2, 60) == 0
    now[0] += 30
    assert limiter.hit(("ip", "b"), 2, 60) == 0
