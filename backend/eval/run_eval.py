"""Step 16 retrieval eval (TRD §11).

Run from backend/:  .venv/bin/python -m eval.run_eval [--refusal]

For each chunk size it ingests backend/samples/ into a temporary collection `eval_{size}`, asks every
question once per retrieval mode, and scores hit@2/4/6, MRR@6, "both documents" for the two-document
questions, and the second-document ratio. Every k and ratio is computed from the same ranked
candidates, so rows differ only by the setting they name. No LLM calls unless --refusal: then the
out-of-scope questions go through retrieval + Groq with the current config (3 calls). Writes
eval/results.md and deletes the temporary collections.
"""

import argparse
import hashlib
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid5

from app import config, llm, store
from app.parsing import chunk_sections, detect_type, parse

HERE = Path(__file__).resolve().parent
SAMPLES = HERE.parent / "samples"
WORKSPACE = str(config.EVAL_WORKSPACE_ID)
SIZES = (400, 700, 1000)  # capped at 1000: MiniLM embeds only the first ~256 tokens (TRD §11)
MODES = ("dense", "hybrid", "hybrid_rerank")
KS = (2, 4, 6)
RATIOS = (None, 0.97, 0.95, 0.93, 0.90)  # None = second-document rule off


def build(size: int) -> tuple[str, list[str], int]:
    """Temporary collection with the samples chunked at `size`: (name, doc ids, chunk count)."""
    name = f"eval_{size}"
    if store.client().collection_exists(name):
        store.client().delete_collection(name)
    store.create_chunks_collection(name)
    doc_ids, total = [], 0
    for path in sorted(SAMPLES.iterdir()):
        doc_type = detect_type(path, path.name)
        doc_id = str(uuid5(config.ID_NAMESPACE, f"{WORKSPACE}:{hashlib.sha256(path.read_bytes()).hexdigest()}"))
        chunks = chunk_sections(parse(path, doc_type), size, config.CHUNK_OVERLAP)
        store.upsert_chunks(name, WORKSPACE, doc_id, path.name, doc_type, chunks)
        doc_ids.append(doc_id)
        total += len(chunks)
    return name, doc_ids, total


def top(mode: str, points: list, k: int, ratio: float | None) -> list[tuple[str, str]]:
    """What the app would send to the LLM for this k and ratio, as (doc name, location)."""
    if mode == "hybrid_rerank" and ratio is not None:
        points = store.with_second_document(points, k, ratio)
    return [(p.payload["doc_name"], p.payload["location"]) for p in points[:k]]


def locations(entries: list[dict]) -> set[tuple[str, str]]:
    return {(e["doc"], e["location"]) for e in entries}


def expected(q: dict) -> set[tuple[str, str]]:
    return set().union(*map(locations, q["parts"])) if "parts" in q else locations(q["expect"])


def hit(q: dict, got: list[tuple[str, str]]) -> bool:
    return bool(expected(q) & set(got))


def both(q: dict, got: list[tuple[str, str]]) -> bool:
    """Two-document question: every part has one of its locations in the top k."""
    return all(locations(part) & set(got) for part in q["parts"])


def first_rank(q: dict, got: list[tuple[str, str]]) -> int | None:
    return next((i for i, loc in enumerate(got, 1) if loc in expected(q)), None)


def pct(values: list[bool]) -> str:
    return f"{sum(values)}/{len(values)}"


def table(head: list[str], rows: list) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    return "\n".join(lines + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def refusal_check(collection: str, doc_ids: list[str], questions: list[dict]) -> list[str]:
    rows = []
    for q in questions:
        sources = store.retrieve(q["q"], WORKSPACE, doc_ids, config.RETRIEVAL_MODE, config.TOP_K, collection)
        try:
            model, pieces = llm.stream_answer(q["q"], sources)
            answer = "".join(pieces).strip()
        except llm.LLMError as err:
            rows.append(f"| {q['id']} | {q['q']} | — | error `{err.code}` | |")
            continue
        refused = answer == config.REFUSAL
        shown = "" if refused else answer[:200].replace("\n", " ").replace("|", "\\|") + ("…" if len(answer) > 200 else "")
        rows.append(f"| {q['id']} | {q['q']} | `{model}` | {'refused' if refused else '**answered**'} | {shown} |")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refusal", action="store_true", help="also run the out-of-scope questions through Groq")
    args = parser.parse_args()

    qa = json.loads((HERE / "qa.json").read_text())
    questions, two_docs = qa["questions"], [q for q in qa["questions"] if "parts" in q]
    if args.refusal and config.CHUNK_SIZE not in SIZES:
        raise SystemExit(f"CHUNK_SIZE {config.CHUNK_SIZE} is not in the grid {SIZES}")

    grid, ratio_rows, ranks, sizes_info, refusal = [], [], {}, [], []
    for size in SIZES:
        collection, doc_ids, total = build(size)
        sizes_info.append(f"{size}: {total} chunks")
        print(f"size {size}: {total} chunks", flush=True)
        try:
            store.search("warm up", WORKSPACE, doc_ids, "dense", 1, collection)  # first call opens the connection
            for mode in MODES:
                results, timings = [], []
                for q in questions:
                    started = time.perf_counter()
                    points = store.search(q["q"], WORKSPACE, doc_ids, mode, max(KS), collection)
                    timings.append((time.perf_counter() - started) * 1000)
                    results.append((q, points))
                served = config.SECOND_DOC_RATIO
                hits = {k: [hit(q, top(mode, p, k, served)) for q, p in results] for k in KS}
                mrr = statistics.mean(1 / r if (r := first_rank(q, top(mode, p, 6, served))) else 0 for q, p in results)
                both4 = [both(q, top(mode, p, 4, served)) for q, p in results if "parts" in q]
                grid.append((size, mode, *(pct(hits[k]) for k in KS), f"{mrr:.3f}", pct(both4),
                             f"{statistics.mean(timings):.0f}"))
                for q, p in results:
                    ranks.setdefault(q["id"], {})[(size, mode)] = first_rank(q, top(mode, p, 6, served))
                print(f"  {mode}: hit@4 {pct(hits[4])}, MRR@6 {mrr:.3f}", flush=True)
                if mode == "hybrid_rerank":
                    for ratio in RATIOS:
                        swaps = sum(top(mode, p, 4, ratio) != top(mode, p, 4, None) for _, p in results)
                        ratio_rows.append((
                            size, "off" if ratio is None else f"{ratio:.2f}",
                            pct([hit(q, top(mode, p, 4, ratio)) for q, p in results]),
                            *(pct([both(q, top(mode, p, k, ratio)) for q, p in results if "parts" in q]) for k in KS),
                            str(swaps),
                        ))
            if args.refusal and size == config.CHUNK_SIZE:
                refusal = refusal_check(collection, doc_ids, qa["out_of_scope"])
        finally:
            store.client().delete_collection(collection)

    cols = [f"{s} {m}" for s in SIZES for m in MODES]
    rank_rows = [
        (q["id"] + (" (2 docs)" if "parts" in q else ""), *("–" if (r := ranks[q["id"]][(s, m)]) is None else r
                                                                 for s in SIZES for m in MODES))
        for q in questions
    ]
    out = f"""# CourseMind — Evaluation results

Generated by `eval/run_eval.py` on {datetime.now(UTC):%Y-%m-%d %H:%M} UTC. Real runs only; re-run to refresh.

**Data:** the 3 files in `backend/samples/` (Git: PDF 2 pages, PPTX 11 slides, DOCX 22 sections); `eval/qa.json` has {len(questions)} questions ({len(two_docs)} needing two documents) and {len(qa["out_of_scope"])} out of scope.
**Setup:** overlap {config.CHUNK_OVERLAP} characters; `PREFETCH_K` {config.PREFETCH_K}; chunks per size: {", ".join(sizes_info)}. Qdrant Cloud Inference (AWS us-west-2) measured from the developer machine, so latency includes the network round trip.
**Metrics:** hit@k = an expected location is in the top k. MRR@6 = mean of 1/rank of the first expected location (0 if none in the top 6). Both@k = for two-document questions (each part answered by a different file), every part has an expected location in the top k. hybrid_rerank rows use the current `SECOND_DOC_RATIO` ({config.SECOND_DOC_RATIO}).
**Caveat:** the PDF has only 2 pages, so a PDF passage from the right page counts as a hit even when it is a different part of that page. Each run rebuilds the collections, and passages with near-equal scores can swap places between runs, so a difference of one question is within noise.

## Retrieval grid

{table(["Chunk size", "Mode", "hit@2", "hit@4", "hit@6", "MRR@6", "Both@4 (2-doc)", "Mean latency (ms)"], grid)}

## Second-document rule (hybrid_rerank)

A question's top k gets the best passage from another document in its last slot when all k come from one document and that passage scores at least ratio × the leader. Swaps = questions whose top 4 changed.

{table(["Chunk size", "Ratio", "hit@4", "Both@2", "Both@4", "Both@6", "Swaps (k=4)"], ratio_rows)}

## Rank of the first expected location (top 6; – = not found)

{table(["Question", *cols], rank_rows)}
"""
    if refusal:
        out += f"""
## Refusal check

Out-of-scope questions through retrieval + Groq with the current config (`CHUNK_SIZE` {config.CHUNK_SIZE}, `TOP_K` {config.TOP_K}, `{config.RETRIEVAL_MODE}`). Expected answer: "{config.REFUSAL}"

| Id | Question | Model | Result | Answer (if not refused) |
|---|---|---|---|---|
""" + "\n".join(refusal) + "\n"
    (HERE / "results.md").write_text(out)
    print(out)


if __name__ == "__main__":
    main()
