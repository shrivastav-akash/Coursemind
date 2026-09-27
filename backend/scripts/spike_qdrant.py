"""Step 5 spike: is Qdrant Cloud Inference fast enough for the TRD design?

Run from backend/:  .venv/bin/python -m scripts.spike_qdrant [path/to/file.pdf]

Creates two throwaway collections (random suffix), measures ingest and query latency
for dense / hybrid / hybrid_rerank, checks a payload-only collection, then deletes both.
"""

import statistics
import sys
import time
from urllib.parse import urlparse
from uuid import uuid4, uuid5

from qdrant_client import QdrantClient, models

from app import config
from app.parsing import chunk_sections, parse_pdf

DEFAULT_PDF = "/usr/share/doc/printer-driver-foo2zjs/manual.pdf"
PAGES = 50
BATCH = 16
QUESTIONS = [
    "How do I set the paper size?",
    "What does the resolution option do?",
    "How do I decode a DDST file?",
    "What does arm2hpdl add to the firmware file?",
    "How do I print in color?",
    "Which printers need a firmware download?",
    "How do I enable duplex printing?",
    "How do I print more than one copy?",
    "What is the default media type?",
    "How do I use the printer with CUPS?",
]


def ms(seconds: float) -> str:
    return f"{seconds * 1000:.0f} ms"


def summary(samples: list[float]) -> str:
    return f"median {ms(statistics.median(samples))}, min {ms(min(samples))}, max {ms(max(samples))}"


def main() -> None:
    if not (config.QDRANT_URL and config.QDRANT_API_KEY):
        sys.exit("QDRANT_URL and QDRANT_API_KEY must be set in backend/.env")
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    host = urlparse(config.QDRANT_URL).hostname or ""
    print(f"Cluster region (from hostname): {'.'.join(host.split('.')[1:-3]) or 'unknown'}")

    client = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY, cloud_inference=True, timeout=120)
    suffix = uuid4().hex[:8]
    chunks_name, registry_name = f"spike_chunks_{suffix}", f"spike_registry_{suffix}"
    workspace_id, doc_id = str(uuid4()), str(uuid4())

    try:
        rtt = []
        for _ in range(5):
            t = time.perf_counter()
            client.get_collections()
            rtt.append(time.perf_counter() - t)
        print(f"Network round trip (get_collections x5): {summary(rtt)}")

        client.create_collection(
            chunks_name,
            vectors_config={
                "dense": models.VectorParams(size=384, distance=models.Distance.COSINE),
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
        client.create_payload_index(
            chunks_name, "workspace_id", models.KeywordIndexParams(type=models.KeywordIndexType.KEYWORD, is_tenant=True)
        )
        client.create_payload_index(chunks_name, "doc_id", models.PayloadSchemaType.KEYWORD)

        t = time.perf_counter()
        sections = parse_pdf(pdf_path)[:PAGES]
        chunks = chunk_sections(sections, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        parse_s = time.perf_counter() - t
        print(f"\nParsed {len(sections)} pages -> {len(chunks)} chunks in {ms(parse_s)}")

        points = [
            models.PointStruct(
                id=str(uuid5(config.ID_NAMESPACE, f"{doc_id}:{c.chunk_index}")),
                vector={
                    "dense": models.Document(text=c.text, model=config.DENSE_MODEL),
                    "sparse": models.Document(text=c.text, model=config.SPARSE_MODEL),
                    "colbert": models.Document(text=c.text, model=config.COLBERT_MODEL),
                },
                payload={
                    "workspace_id": workspace_id, "doc_id": doc_id, "doc_name": "manual.pdf", "doc_type": "pdf",
                    "location": c.location, "order": c.order, "chunk_index": c.chunk_index, "text": c.text,
                },
            )
            for c in chunks
        ]
        batch_times = []
        t = time.perf_counter()
        for i in range(0, len(points), BATCH):
            b = time.perf_counter()
            client.upsert(chunks_name, points[i:i + BATCH], wait=True)
            batch_times.append(time.perf_counter() - b)
        upsert_s = time.perf_counter() - t
        print(f"Upserted {len(points)} chunks in {len(batch_times)} batches of {BATCH}: {upsert_s:.1f} s "
              f"(per batch {summary(batch_times)})")
        print(f"Ingest total (parse + upsert): {parse_s + upsert_s:.1f} s")

        scope = models.Filter(must=[
            models.FieldCondition(key="workspace_id", match=models.MatchValue(value=workspace_id)),
            models.FieldCondition(key="doc_id", match=models.MatchAny(any=[doc_id])),
        ])

        def run(mode: str, q: str) -> list[models.ScoredPoint]:
            dense = models.Document(text=q, model=config.DENSE_MODEL)
            if mode == "dense":
                return client.query_points(chunks_name, query=dense, using="dense", query_filter=scope,
                                           limit=config.TOP_K).points
            prefetch = [
                models.Prefetch(query=dense, using="dense", filter=scope, limit=config.PREFETCH_K),
                models.Prefetch(query=models.Document(text=q, model=config.SPARSE_MODEL), using="sparse",
                                filter=scope, limit=config.PREFETCH_K),
            ]
            if mode == "hybrid":
                return client.query_points(chunks_name, prefetch=prefetch, query=models.FusionQuery(fusion=models.Fusion.RRF),
                                           query_filter=scope, limit=config.TOP_K).points
            return client.query_points(chunks_name, prefetch=prefetch,
                                       query=models.Document(text=q, model=config.COLBERT_MODEL), using="colbert",
                                       query_filter=scope, limit=config.TOP_K).points

        print(f"\nQueries ({len(QUESTIONS)} per mode, TOP_K={config.TOP_K}, PREFETCH_K={config.PREFETCH_K}):")
        medians = {}
        for mode in ("dense", "hybrid", "hybrid_rerank"):
            t = time.perf_counter()
            run(mode, "warm-up question about printing")
            first = time.perf_counter() - t
            samples, top = [], []
            for q in QUESTIONS:
                t = time.perf_counter()
                hits = run(mode, q)
                samples.append(time.perf_counter() - t)
                top.append(hits[0].payload["location"] if hits else "-")
            medians[mode] = statistics.median(samples)
            print(f"  {mode:<14} warm-up {ms(first)}; {summary(samples)}; top-1 pages: {', '.join(top)}")

        # Payload-only registry collection (documents schema: vectors_config={}).
        client.create_collection(registry_name, vectors_config={})
        record_id = str(uuid4())
        client.upsert(registry_name, [models.PointStruct(id=record_id, vector={}, payload={"status": "queued"})], wait=True)
        got = client.retrieve(registry_name, [record_id], with_payload=True)
        registry_ok = len(got) == 1 and got[0].payload == {"status": "queued"}
        print(f"\nPayload-only collection upsert + retrieve: {'ok' if registry_ok else 'FAILED'}")

        ingest_ok = parse_s + upsert_s < 60
        query_ok = medians["hybrid_rerank"] < 1
        print(f"\nGate: hybrid_rerank median < 1 s: {'PASS' if query_ok else 'FAIL'} ({ms(medians['hybrid_rerank'])}); "
              f"{len(sections)}-page ingest < 60 s: {'PASS' if ingest_ok else 'FAIL'} ({parse_s + upsert_s:.1f} s)")
    finally:
        for name in (chunks_name, registry_name):
            if client.collection_exists(name):
                client.delete_collection(name)
        leftover = [c.name for c in client.get_collections().collections if c.name.startswith(f"spike_") and suffix in c.name]
        print(f"Cleanup: {'done' if not leftover else f'LEFT OVER {leftover}'}")


if __name__ == "__main__":
    main()
