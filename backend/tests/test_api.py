import pytest
from fastapi.testclient import TestClient

from app import config, store
from app.main import app

client = TestClient(app)  # no `with`: lifespan (Qdrant setup) does not run in offline tests


def test_health(monkeypatch):
    monkeypatch.setattr(store, "ping", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_503_when_qdrant_is_unreachable(monkeypatch):
    monkeypatch.setattr(store, "ping", lambda: False)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["code"] == "unavailable"


def test_startup_fails_fast_without_qdrant_settings(monkeypatch):
    monkeypatch.setattr(config, "QDRANT_URL", "")

    with pytest.raises(RuntimeError, match="QDRANT_URL"):
        with TestClient(app):
            pass
