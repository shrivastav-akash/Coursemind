from uuid import uuid4

import pytest
from qdrant_client import models

from app import config, store
from tests.files import make_pdf

pytestmark = [pytest.mark.live, pytest.mark.skipif(not config.QDRANT_URL, reason="QDRANT_URL not set")]

PAGES = [
    "Processes are programs in execution. The scheduler decides which ready process runs next on the CPU.",
    "The Zorblax quorum protocol elects a coordinator by comparing lunar timestamps sent by every replica.",
    "Paging divides physical memory into fixed-size frames and maps virtual pages onto them.",
    "A file system stores files in blocks and keeps metadata such as owner and size in inodes.",
    "TCP gives reliable, ordered delivery using sequence numbers, acknowledgements and retransmission.",
    "A relation is in third normal form when no non-key attribute depends on another non-key attribute.",
]
QUESTION = "How does the Zorblax quorum protocol elect a coordinator?"


@pytest.fixture
def workspace():
    ws = str(uuid4())
    store.ensure_collections()
    yield ws
    only_this_workspace = models.Filter(must=[models.FieldCondition(key="workspace_id", match=models.MatchValue(value=ws))])
    for collection in (store.DOCUMENTS, store.CHUNKS):
        store.client().delete(collection, points_selector=only_this_workspace, wait=True)


def add(workspace_id, path, name="os-notes.pdf") -> store.Record:
    record = store.create_document(workspace_id, str(uuid4()), name, "pdf", path.stat().st_size, "0" * 64, False)
    store.ingest(record, path)
    return store.get_document(workspace_id, record["id"])


def stored_chunks(workspace_id, doc_id) -> int:
    return store.client().count(store.CHUNKS, count_filter=store._doc_filter(workspace_id, doc_id), exact=True).count


def test_ingest_then_every_mode_finds_the_right_page(workspace, tmp_path, monkeypatch):
    record = add(workspace, make_pdf(tmp_path / "notes.pdf", PAGES))

    assert (record["status"], record["chunks"], record["error_code"]) == ("ready", len(PAGES), None)
    assert stored_chunks(workspace, record["id"]) == len(PAGES)

    for mode in ("dense", "hybrid", "hybrid_rerank"):
        sources = store.retrieve(QUESTION, workspace, [record["id"]], mode, k=4)
        assert [s.n for s in sources] == [1, 2, 3, 4], mode
        assert sources[0].location == "p. 2", mode
        assert "Zorblax" in sources[0].text and sources[0].doc_name == "os-notes.pdf", mode

    # Isolation: the right doc id is not enough without the right workspace, and only ready ids are searched.
    assert store.retrieve(QUESTION, str(uuid4()), [record["id"]], "hybrid_rerank", k=4) == []
    assert store.retrieve(QUESTION, workspace, [str(uuid4())], "hybrid_rerank", k=4) == []

    # Re-processing replaces old passages: many small chunks first, then the default size must leave no extras.
    monkeypatch.setattr(config, "CHUNK_SIZE", 60)
    monkeypatch.setattr(config, "CHUNK_OVERLAP", 10)
    store.ingest(record, tmp_path / "notes.pdf")
    assert store.get_document(workspace, record["id"])["chunks"] > len(PAGES)
    monkeypatch.undo()
    store.ingest(record, tmp_path / "notes.pdf")
    assert stored_chunks(workspace, record["id"]) == len(PAGES)


def test_failures_leave_no_chunks(workspace, tmp_path):
    blank = add(workspace, make_pdf(tmp_path / "scan.pdf", ["", ""]), "scan.pdf")
    corrupt_path = tmp_path / "broken.pdf"
    corrupt_path.write_bytes(b"%PDF-1.7\nthis is not really a PDF")
    corrupt = add(workspace, corrupt_path, "broken.pdf")

    assert (blank["status"], blank["error_code"], blank["chunks"]) == ("failed", "no_text", 0)
    assert (corrupt["status"], corrupt["error_code"], corrupt["chunks"]) == ("failed", "unreadable", 0)
    assert stored_chunks(workspace, blank["id"]) == 0
    assert stored_chunks(workspace, corrupt["id"]) == 0


def test_failure_mid_upload_removes_partial_chunks(workspace, tmp_path, monkeypatch):
    qdrant = store.client()
    real_upsert = qdrant.upsert
    calls = []

    def flaky_upsert(collection, points, **kwargs):
        if collection == store.CHUNKS:
            calls.append(len(points))
            if len(calls) == 2:
                raise ConnectionError("network dropped")
        return real_upsert(collection, points, **kwargs)

    monkeypatch.setattr(qdrant, "upsert", flaky_upsert)
    pages = [f"Page {i} covers topic number {i} in some detail." for i in range(store.UPSERT_BATCH + 4)]

    record = add(workspace, make_pdf(tmp_path / "long.pdf", pages))

    assert calls == [store.UPSERT_BATCH, 4]  # first batch landed, second failed
    assert (record["status"], record["error_code"]) == ("failed", "unreadable")
    assert stored_chunks(workspace, record["id"]) == 0


def test_delete_document_removes_record_and_chunks(workspace, tmp_path):
    record = add(workspace, make_pdf(tmp_path / "notes.pdf", PAGES[:2]))
    assert stored_chunks(workspace, record["id"]) == 2

    store.delete_document(workspace, record["id"])

    assert store.get_document(workspace, record["id"]) is None
    assert stored_chunks(workspace, record["id"]) == 0
