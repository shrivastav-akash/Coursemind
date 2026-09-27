import logging
import threading
from datetime import UTC, datetime
from functools import cache
from typing import TypedDict, cast

from qdrant_client import QdrantClient, models

from app import config
from app.schemas import DocErrorCode, DocType, Status

log = logging.getLogger(__name__)

DOCUMENTS = "documents"
CHUNKS = "chunks"


class Record(TypedDict):
    """A `documents` point: its id plus the payload from BACKEND_SCHEMA §3."""
    id: str
    workspace_id: str
    name: str
    type: DocType
    size_bytes: int
    sha256: str
    is_sample: bool
    status: Status
    error_code: DocErrorCode | None
    chunks: int
    created_at: str
    updated_at: str


@cache
def client() -> QdrantClient:
    # Created on first use so importing the app (and offline tests) never needs Qdrant settings.
    return QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY, cloud_inference=True, timeout=60)


def _now() -> str:
    # Microseconds keep "newest first" stable when two uploads land in the same second.
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _workspace(workspace_id: str) -> models.FieldCondition:
    return models.FieldCondition(key="workspace_id", match=models.MatchValue(value=workspace_id))


def _record(point: models.Record) -> Record:
    # set_payload drops keys whose value is None, so a cleared error_code comes back missing.
    return cast(Record, {"error_code": None, **(point.payload or {}), "id": str(point.id)})


def _tenant_index() -> models.KeywordIndexParams:
    return models.KeywordIndexParams(type=models.KeywordIndexType.KEYWORD, is_tenant=True)


# --- Startup -------------------------------------------------------------------------------

_ready = False
_ready_lock = threading.Lock()


def ensure_ready() -> None:
    """Create collections and sweep interrupted jobs once per process.

    Called at startup and before any route touches Qdrant. If Qdrant is down at boot the app
    still starts (/health answers 503, APP_FLOW J9) and setup runs on the next call. The lock
    makes the sweep finish before any request can create a record, so it never marks new work.
    """
    global _ready
    if _ready:
        return
    with _ready_lock:
        if not _ready:
            ensure_collections()
            swept = sweep_interrupted()
            log.info("qdrant ready; %d interrupted document(s) marked failed", swept)
            _ready = True


def ping() -> bool:
    try:
        ensure_ready()
        return client().collection_exists(DOCUMENTS)
    except Exception as exc:
        # One line, no traceback: the frontend re-checks /health every 3 s during an outage.
        log.warning("qdrant unreachable: %s: %s", type(exc).__name__, exc)
        return False


def ensure_collections() -> None:
    c = client()
    if not c.collection_exists(DOCUMENTS):
        c.create_collection(DOCUMENTS, vectors_config={})
    c.create_payload_index(DOCUMENTS, "workspace_id", _tenant_index())
    c.create_payload_index(DOCUMENTS, "status", models.PayloadSchemaType.KEYWORD)

    if not c.collection_exists(CHUNKS):
        c.create_collection(
            CHUNKS,
            vectors_config={
                "dense": models.VectorParams(size=384, distance=models.Distance.COSINE),
                # Only used to re-rank, so no HNSW graph; kept on disk to save RAM on the free cluster.
                "colbert": models.VectorParams(
                    size=96,
                    distance=models.Distance.COSINE,
                    multivector_config=models.MultiVectorConfig(comparator=models.MultiVectorComparator.MAX_SIM),
                    hnsw_config=models.HnswConfigDiff(m=0),
                    on_disk=True,
                    datatype=models.Datatype.FLOAT16,
                ),
            },
            sparse_vectors_config={"sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)},
        )
    c.create_payload_index(CHUNKS, "workspace_id", _tenant_index())
    c.create_payload_index(CHUNKS, "doc_id", models.PayloadSchemaType.KEYWORD)


def sweep_interrupted() -> int:
    """Mark every queued/processing record failed: their jobs and temp files died with the last process."""
    stuck = models.Filter(must=[
        models.FieldCondition(key="status", match=models.MatchAny(any=["queued", "processing"])),
    ])
    count = client().count(DOCUMENTS, count_filter=stuck, exact=True).count
    if count:
        client().set_payload(
            DOCUMENTS, {"status": "failed", "error_code": "interrupted", "updated_at": _now()}, points=stuck, wait=True
        )
    return count


# --- Document registry ---------------------------------------------------------------------

def create_document(
    workspace_id: str, doc_id: str, name: str, doc_type: DocType, size_bytes: int, sha256: str, is_sample: bool
) -> Record:
    now = _now()
    record = Record(
        id=doc_id, workspace_id=workspace_id, name=name, type=doc_type, size_bytes=size_bytes, sha256=sha256,
        is_sample=is_sample, status="queued", error_code=None, chunks=0, created_at=now, updated_at=now,
    )
    payload = {k: v for k, v in record.items() if k != "id"}
    client().upsert(DOCUMENTS, [models.PointStruct(id=doc_id, vector={}, payload=payload)], wait=True)
    return record


def get_document(workspace_id: str, doc_id: str) -> Record | None:
    """None for unknown ids and for ids in another workspace (same answer, so ids can't be probed)."""
    points = client().retrieve(DOCUMENTS, [doc_id], with_payload=True)
    if not points or not points[0].payload or points[0].payload.get("workspace_id") != workspace_id:
        return None
    return _record(points[0])


def list_documents(workspace_id: str) -> list[Record]:
    records: list[Record] = []
    offset = None
    while True:
        points, offset = client().scroll(
            DOCUMENTS, scroll_filter=models.Filter(must=[_workspace(workspace_id)]), limit=64, offset=offset,
            with_payload=True,
        )
        records += [_record(p) for p in points]
        if offset is None:
            break
    return sorted(records, key=lambda r: r["created_at"], reverse=True)


def set_status(doc_id: str, status: Status, error_code: DocErrorCode | None = None, chunks: int | None = None) -> None:
    if (status == "failed") != (error_code is not None):
        raise ValueError("error_code is required for failed and forbidden otherwise")
    payload: dict[str, object] = {"status": status, "error_code": error_code, "updated_at": _now()}
    if chunks is not None:
        payload["chunks"] = chunks
    client().set_payload(DOCUMENTS, payload, points=[doc_id], wait=True)


def delete_record(doc_id: str) -> None:
    client().delete(DOCUMENTS, points_selector=[doc_id], wait=True)
