import pytest

from app import store


@pytest.fixture
def fresh_start(monkeypatch):
    monkeypatch.setattr(store, "_ready", False)
    calls = []
    monkeypatch.setattr(store, "ensure_collections", lambda: calls.append("ensure"))
    monkeypatch.setattr(store, "sweep_interrupted", lambda: calls.append("sweep") or 0)
    return calls


def test_setup_runs_once(fresh_start):
    store.ensure_ready()
    store.ensure_ready()

    assert fresh_start == ["ensure", "sweep"]


def test_setup_retries_after_a_failure(fresh_start, monkeypatch):
    def down():
        raise ConnectionError("qdrant down")

    monkeypatch.setattr(store, "ensure_collections", down)
    assert store.ping() is False  # outage is reported, not raised

    monkeypatch.setattr(store, "ensure_collections", lambda: fresh_start.append("ensure"))
    store.ensure_ready()

    assert fresh_start == ["ensure", "sweep"]


@pytest.mark.parametrize("status, error_code", [("failed", None), ("ready", "no_text"), ("queued", "interrupted")])
def test_error_code_only_with_failed(status, error_code):
    with pytest.raises(ValueError):
        store.set_status("00000000-0000-4000-8000-000000000000", status, error_code=error_code)


def point(doc: str, score: float, n: int = 0):
    from qdrant_client import models
    return models.ScoredPoint(id=n, version=0, score=score, payload={"doc_id": doc})


def docs(points) -> list[str]:
    return [p.payload["doc_id"] for p in points]


def test_second_document_takes_the_last_slot_when_close(monkeypatch):
    monkeypatch.setattr(store.config, "SECOND_DOC_RATIO", 0.95)
    ranked = [point("big", 25.3), point("big", 25.2), point("big", 25.2), point("big", 25.1), point("small", 24.6)]

    assert docs(store._with_second_document(ranked, 4)) == ["big", "big", "big", "small"]


@pytest.mark.parametrize("ranked, expected", [
    # other document too far behind the leader (0.90 < 0.95): unchanged
    ([point("big", 10.5), point("big", 10.4), point("big", 10.4), point("big", 10.3), point("small", 9.5)],
     ["big", "big", "big", "big"]),
    # top k already spans two documents: unchanged
    ([point("a", 10), point("b", 9), point("a", 8), point("a", 7), point("c", 6.9)], ["a", "b", "a", "a"]),
    # no other document among the candidates: unchanged
    ([point("a", 10), point("a", 9.9), point("a", 9.8), point("a", 9.7), point("a", 9.6)], ["a", "a", "a", "a"]),
    # fewer candidates than k: unchanged
    ([point("a", 10), point("b", 9.9)], ["a", "b"]),
])
def test_second_document_rule_leaves_other_cases_alone(ranked, expected):
    assert docs(store._with_second_document(ranked, 4)) == expected
