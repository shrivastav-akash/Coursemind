from uuid import uuid4

import pytest
from qdrant_client import models

from app import config, store
from app.schemas import Document

pytestmark = [pytest.mark.live, pytest.mark.skipif(not config.QDRANT_URL, reason="QDRANT_URL not set")]


@pytest.fixture
def workspace():
    ws = str(uuid4())
    store.ensure_collections()
    yield ws
    only_this_workspace = models.Filter(must=[models.FieldCondition(key="workspace_id", match=models.MatchValue(value=ws))])
    store.client().delete(store.DOCUMENTS, points_selector=only_this_workspace, wait=True)


def new(ws: str, name: str = "notes.pdf") -> str:
    doc_id = str(uuid4())
    store.create_document(ws, doc_id, name, "pdf", 1234, "a" * 64, False)
    return doc_id


def test_ensure_collections_is_idempotent(workspace):
    store.ensure_collections()

    assert store.client().collection_exists(store.DOCUMENTS)
    assert store.client().collection_exists(store.CHUNKS)


def test_registry_lifecycle(workspace):
    first = new(workspace, "first.pdf")
    second = new(workspace, "second.pdf")

    assert [r["id"] for r in store.list_documents(workspace)] == [second, first]
    record = store.get_document(workspace, first)
    assert record is not None and record["status"] == "queued" and record["chunks"] == 0
    assert Document.model_validate(record).name == "first.pdf"  # registry record fits the API model

    other = str(uuid4())
    assert store.get_document(other, first) is None
    assert store.list_documents(other) == []

    store.set_status(first, "processing")
    store.set_status(first, "ready", chunks=12)
    record = store.get_document(workspace, first)
    assert (record["status"], record["chunks"], record["error_code"]) == ("ready", 12, None)
    assert record["updated_at"] > record["created_at"]

    store.set_status(second, "failed", error_code="no_text")
    assert store.get_document(workspace, second)["error_code"] == "no_text"
    store.set_status(second, "queued")  # re-queue clears the old error
    assert store.get_document(workspace, second)["error_code"] is None

    store.delete_record(first)
    assert store.get_document(workspace, first) is None
    assert [r["id"] for r in store.list_documents(workspace)] == [second]


def test_sweep_marks_only_unfinished_work(workspace):
    queued, processing, ready = new(workspace), new(workspace), new(workspace)
    store.set_status(processing, "processing")
    store.set_status(ready, "ready", chunks=3)

    assert store.sweep_interrupted() >= 2

    status = {r["id"]: (r["status"], r["error_code"]) for r in store.list_documents(workspace)}
    assert status[queued] == ("failed", "interrupted")
    assert status[processing] == ("failed", "interrupted")
    assert status[ready] == ("ready", None)
