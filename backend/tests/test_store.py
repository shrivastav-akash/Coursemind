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
