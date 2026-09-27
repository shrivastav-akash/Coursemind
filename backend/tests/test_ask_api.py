import asyncio
import json
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import config, llm, main, store
from app.schemas import Source

WS = str(uuid4())
READY, PROCESSING = str(uuid4()), str(uuid4())
SOURCES = [
    Source(n=1, doc_id=READY, doc_name="OS_Lecture3.pdf", doc_type="pdf", location="p. 12",
           text="A deadlock needs mutual exclusion, hold and wait, no preemption and circular wait."),
    Source(n=2, doc_id=READY, doc_name="OS_Lecture3.pdf", doc_type="pdf", location="p. 13", text="Banker's algorithm."),
]


def pieces(*items):
    """A fake LLM stream: yields text, raises any exception instance in place, records when it is closed."""
    closed = []

    def gen():
        try:
            for item in items:
                if isinstance(item, Exception):
                    raise item
                yield item
        finally:
            closed.append(True)

    return gen(), closed


@pytest.fixture
def api(monkeypatch):
    state = type("State", (), {})()
    state.documents = [{"id": READY, "status": "ready"}, {"id": PROCESSING, "status": "processing"}]
    state.sources = SOURCES
    state.retrieve_calls, state.llm_calls = [], []
    stream, state.closed = pieces("A deadlock needs ", "four conditions [1].")
    state.llm_result = ("m1", stream)

    def retrieve(question, workspace_id, ready_ids, mode, k):
        state.retrieve_calls.append((question, workspace_id, ready_ids, mode, k))
        return state.sources

    def stream_answer(question, sources):
        state.llm_calls.append((question, sources))
        if isinstance(state.llm_result, Exception):
            raise state.llm_result
        return state.llm_result

    monkeypatch.setattr(store, "ensure_ready", lambda: None)
    monkeypatch.setattr(store, "list_documents", lambda _ws: state.documents)
    monkeypatch.setattr(store, "retrieve", retrieve)
    monkeypatch.setattr(llm, "stream_answer", stream_answer)
    monkeypatch.setattr(main, "limiter", main.RateLimiter())
    state.client = TestClient(main.app)
    return state


def ask(api, question="  What causes a deadlock?  ", workspace_id=WS, **kwargs):
    kwargs.setdefault("json", {"question": question})
    return api.client.post("/ask", headers={"X-Workspace-Id": workspace_id}, **kwargs)


def events(response) -> list[tuple[str, object]]:
    parsed = []
    for block in response.text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.split("\n"))
        parsed.append((fields["event"], json.loads(fields["data"])))
    return parsed


def test_streams_sources_then_tokens_then_done(api):
    response = ask(api)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert (response.headers["cache-control"], response.headers["x-accel-buffering"]) == ("no-cache", "no")
    assert events(response) == [
        ("sources", [s.model_dump(mode="json") for s in SOURCES]),
        ("token", {"t": "A deadlock needs "}),
        ("token", {"t": "four conditions [1]."}),
        ("done", {"refused": False, "model": "m1"}),
    ]
    # Question is trimmed; only ready documents are searched, with the configured mode and k.
    assert api.retrieve_calls == [("What causes a deadlock?", WS, [READY], config.RETRIEVAL_MODE, config.TOP_K)]
    assert api.llm_calls == [("What causes a deadlock?", SOURCES)]
    assert api.closed == [True]


def test_nothing_retrieved_refuses_without_calling_the_llm(api):
    api.sources = []

    assert events(ask(api)) == [
        ("sources", []),
        ("token", {"t": config.REFUSAL}),
        ("done", {"refused": True, "model": None}),
    ]
    assert api.llm_calls == []


def test_model_refusal_is_flagged(api):
    stream, _ = pieces(f"  {config.REFUSAL}\n")
    api.llm_result = ("m2", stream)

    assert events(ask(api))[-1] == ("done", {"refused": True, "model": "m2"})


@pytest.mark.parametrize("code", ["llm_busy", "daily_limit", "llm_error"])
def test_llm_failure_before_first_token_is_an_error_event(api, code):
    api.llm_result = llm.LLMError(code)

    assert [e for e, _ in events(ask(api))] == ["sources", "error"]
    assert events(ask(api))[-1] == ("error", {"code": code})


def test_failure_mid_stream_keeps_partial_text_then_errors(api):
    stream, closed = pieces("Partial ", llm.LLMError("llm_error"))
    api.llm_result = ("m1", stream)

    assert events(ask(api)) == [
        ("sources", [s.model_dump(mode="json") for s in SOURCES]),
        ("token", {"t": "Partial "}),
        ("error", {"code": "llm_error"}),
    ]
    assert closed == [True]


def test_client_disconnect_closes_the_llm_stream(api):
    stream, closed = pieces("one ", "two ", "three")
    api.llm_result = ("m1", stream)

    async def read_two_then_leave():
        body = main.answer_events("q?", SOURCES, time.perf_counter())
        received = [await anext(body), await anext(body)]  # sources, first token
        await body.aclose()  # what Starlette does when the visitor presses Stop
        return received

    received = asyncio.run(read_two_then_leave())

    assert received[1] == main.sse("token", {"t": "one "})
    assert closed == [True]


def test_no_ready_documents_is_409(api):
    api.documents = [{"id": PROCESSING, "status": "processing"}]

    response = ask(api)

    assert (response.status_code, response.json()["code"]) == (409, "no_ready_documents")
    assert api.llm_calls == []


@pytest.mark.parametrize("payload", [
    {"question": "  a  "},  # 1 character after trimming
    {"question": "x" * 501},
    {},
    {"question": "What is 3NF?", "extra": 1},  # unknown keys are rejected
    {"question": 42},
])
def test_invalid_question_is_422(api, payload):
    response = ask(api, json=payload)

    assert (response.status_code, response.json()["code"]) == (422, "validation_error")
    assert api.retrieve_calls == []


def test_ask_rate_limit(api, monkeypatch):
    monkeypatch.setattr(config, "ASK_LIMIT", (2, 60))

    assert [ask(api).status_code for _ in range(2)] == [200, 200]
    limited = ask(api)

    assert (limited.status_code, limited.json()["code"]) == (429, "ask_rate_limited")
    assert 55 <= int(limited.headers["Retry-After"]) <= 60
    assert len(api.retrieve_calls) == 2  # a limited request never reaches Qdrant


def test_bad_workspace_is_400(api):
    response = ask(api, workspace_id="nope")

    assert (response.status_code, response.json()["code"]) == (400, "invalid_workspace")


def test_qdrant_failure_before_streaming_is_503(api, monkeypatch):
    def broken(*_args):
        raise ConnectionError("qdrant down")

    monkeypatch.setattr(store, "retrieve", broken)

    response = ask(api)

    assert (response.status_code, response.json()["code"]) == (503, "unavailable")
