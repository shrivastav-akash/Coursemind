import logging
import threading
import time
from datetime import UTC, datetime
from functools import cache
from itertools import batched
from pathlib import Path
from typing import TypedDict, cast
from uuid import uuid5

from qdrant_client import QdrantClient, models

from app import config
from app.parsing import Chunk, chunk_sections, parse
from app.schemas import DocErrorCode, DocType, RetrievalMode, Source, Status

log = logging.getLogger(__name__)

DOCUMENTS = "documents"
CHUNKS = "chunks"
UPSERT_BATCH = 16  # TRD §7.2


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
        create_chunks_collection(CHUNKS)


def create_chunks_collection(name: str) -> None:
    """The `chunks` schema (BACKEND_SCHEMA §4); eval/run_eval.py builds its temporary collections with it."""
    c = client()
    c.create_collection(
        name,
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
    c.create_payload_index(name, "workspace_id", _tenant_index())
    c.create_payload_index(name, "doc_id", models.PayloadSchemaType.KEYWORD)


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


def count_documents(workspace_id: str) -> int:
    return client().count(DOCUMENTS, count_filter=models.Filter(must=[_workspace(workspace_id)]), exact=True).count


def count_chunks() -> int:
    """All chunks in the cluster, every workspace: guards the free tier's MAX_TOTAL_CHUNKS."""
    return client().count(CHUNKS, exact=True).count


def set_status(doc_id: str, status: Status, error_code: DocErrorCode | None = None, chunks: int | None = None) -> None:
    if (status == "failed") != (error_code is not None):
        raise ValueError("error_code is required for failed and forbidden otherwise")
    payload: dict[str, object] = {"status": status, "error_code": error_code, "updated_at": _now()}
    if chunks is not None:
        payload["chunks"] = chunks
    client().set_payload(DOCUMENTS, payload, points=[doc_id], wait=True)


def delete_record(doc_id: str) -> None:
    client().delete(DOCUMENTS, points_selector=[doc_id], wait=True)


def delete_document(workspace_id: str, doc_id: str) -> None:
    # Record first: if the chunk delete then fails, retrieval never searches the leftovers,
    # because it only looks at doc ids that are `ready` in the registry (BACKEND_SCHEMA §2).
    delete_record(doc_id)
    _delete_chunks(workspace_id, doc_id)


# --- Ingest --------------------------------------------------------------------------------

def _doc_filter(workspace_id: str, doc_id: str) -> models.Filter:
    return models.Filter(must=[
        _workspace(workspace_id), models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id)),
    ])


def _delete_chunks(workspace_id: str, doc_id: str) -> None:
    client().delete(CHUNKS, points_selector=_doc_filter(workspace_id, doc_id), wait=True)


def ingest(record: Record, path: Path | str) -> None:
    """Worker job (TRD §7.2): parse, chunk, embed via Cloud Inference, mark ready or failed.

    The caller owns `path` and deletes it afterwards (sample files must not be deleted).
    """
    doc_id, workspace_id = record["id"], record["workspace_id"]
    started = time.perf_counter()
    set_status(doc_id, "processing")
    try:
        chunks = chunk_sections(parse(path, record["type"]), config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        if not chunks:
            set_status(doc_id, "failed", error_code="no_text")
            log.info("ingest %s: no text", doc_id)
            return
        _delete_chunks(workspace_id, doc_id)  # re-processing never mixes old and new passages
        upsert_chunks(CHUNKS, workspace_id, doc_id, record["name"], record["type"], chunks)
        set_status(doc_id, "ready", chunks=len(chunks))
        log.info("ingest %s: %d chunks in %.1f s", doc_id, len(chunks), time.perf_counter() - started)
    except Exception:
        log.exception("ingest %s failed", doc_id)
        try:
            _delete_chunks(workspace_id, doc_id)
        except Exception:
            log.warning("ingest %s: could not remove partial chunks", doc_id)
        set_status(doc_id, "failed", error_code="unreadable")


def upsert_chunks(
    collection: str, workspace_id: str, doc_id: str, name: str, doc_type: DocType, chunks: list[Chunk]
) -> None:
    """Store chunks with their three vectors, which Qdrant Cloud Inference embeds from the text."""
    points = [
        models.PointStruct(
            id=str(uuid5(config.ID_NAMESPACE, f"{doc_id}:{c.chunk_index}")),
            vector={
                "dense": models.Document(text=c.text, model=config.DENSE_MODEL),
                "sparse": models.Document(text=c.text, model=config.SPARSE_MODEL),
                "colbert": models.Document(text=c.text, model=config.COLBERT_MODEL),
            },
            payload={
                "workspace_id": workspace_id, "doc_id": doc_id, "doc_name": name, "doc_type": doc_type,
                "location": c.location, "order": c.order, "chunk_index": c.chunk_index, "text": c.text,
            },
        )
        for c in chunks
    ]
    for batch in batched(points, UPSERT_BATCH):
        client().upsert(collection, list(batch), wait=True)


# --- Retrieval -----------------------------------------------------------------------------

def retrieve(
    question: str, workspace_id: str, ready_ids: list[str], mode: RetrievalMode, k: int, collection: str = CHUNKS
) -> list[Source]:
    """One Qdrant query (TRD §8.2), scoped to the workspace's ready documents in every stage."""
    points = search(question, workspace_id, ready_ids, mode, k, collection)
    if mode == "hybrid_rerank":
        points = with_second_document(points, k, config.SECOND_DOC_RATIO)
    return [
        Source(
            n=i, doc_id=p.payload["doc_id"], doc_name=p.payload["doc_name"], doc_type=p.payload["doc_type"],
            location=p.payload["location"], text=p.payload["text"],
        )
        for i, p in enumerate(points, start=1)
        if p.payload
    ]


def search(
    question: str, workspace_id: str, ready_ids: list[str], mode: RetrievalMode, k: int, collection: str = CHUNKS
) -> list[models.ScoredPoint]:
    """Ranked candidates: the top k for dense and hybrid; for hybrid_rerank the whole re-ranked union
    (2 × PREFETCH_K), which with_second_document cuts to k. The eval scores every k from one call."""
    if not ready_ids:
        return []
    scope = models.Filter(must=[
        _workspace(workspace_id), models.FieldCondition(key="doc_id", match=models.MatchAny(any=ready_ids)),
    ])
    dense = models.Document(text=question, model=config.DENSE_MODEL)
    if mode == "dense":
        return client().query_points(collection, query=dense, using="dense", query_filter=scope, limit=k).points
    prefetch = [
        models.Prefetch(query=dense, using="dense", filter=scope, limit=config.PREFETCH_K),
        models.Prefetch(
            query=models.Document(text=question, model=config.SPARSE_MODEL), using="sparse",
            filter=scope, limit=config.PREFETCH_K,
        ),
    ]
    if mode == "hybrid":
        return client().query_points(
            collection, prefetch=prefetch, query=models.FusionQuery(fusion=models.Fusion.RRF),
            query_filter=scope, limit=k,
        ).points
    # hybrid_rerank: ColBERT MaxSim re-scores the whole union of both candidate lists
    return client().query_points(
        collection, prefetch=prefetch, query=models.Document(text=question, model=config.COLBERT_MODEL),
        using="colbert", query_filter=scope, limit=2 * config.PREFETCH_K,
    ).points


def with_second_document(points: list[models.ScoredPoint], k: int, ratio: float) -> list[models.ScoredPoint]:
    """Top k by re-rank score, except when all k come from one document while another document's
    best passage scores at least `ratio` × the leader: then that passage takes the last slot.

    Without this a question spanning two documents loses the smaller one (PRD FR-12). In the step 10
    check a two-topic question filled the top 20 from a 70-chunk PDF although the other document's
    best passage scored 24.6 against 25.3. Slots 1..k-1 never change.
    """
    top = points[:k]
    if k < 2 or len(top) < k or not top[0].payload or len({p.payload["doc_id"] for p in top if p.payload}) > 1:
        return top
    leader = top[0].payload["doc_id"]
    other = next((p for p in points[k:] if p.payload and p.payload["doc_id"] != leader), None)
    if other is None or top[0].score <= 0 or other.score < ratio * top[0].score:
        return top
    return [*top[:-1], other]
