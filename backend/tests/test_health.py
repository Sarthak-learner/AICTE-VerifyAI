"""Smoke test for the health-check endpoint (no DB required)."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app


@pytest.fixture
def client():
    """Test client with DB dependency mocked out."""
    mock_db = MagicMock()
    mock_db.execute.return_value = None  # Simulate successful SELECT 1

    def override_get_db():
        yield mock_db

    from app.db.session import get_db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert "disclaimer" in body
    assert "AI-generated findings" in body["disclaimer"]


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "AICTE VerifyAI"


def test_production_startup_rejects_insecure_secret():
    """Starting in production without a secure SECRET_KEY raises RuntimeError."""
    from app.core.config import Settings
    from app.main import lifespan

    mock_settings = Settings(
        app_env="production",
        secret_key="CHANGE_ME_IN_PRODUCTION",
    )
    with patch("app.main.settings", mock_settings):
        with pytest.raises(RuntimeError, match="Production security violation"):
            import asyncio
            asyncio.run(lifespan(app).__aenter__())
