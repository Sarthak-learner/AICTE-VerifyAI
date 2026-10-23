"""Tests for CORS configuration and origin validation."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app
from app.core.config import Settings, get_settings


VERCEL_ORIGIN = "https://aicte-verify-ai-beta.vercel.app"
UNAUTHORIZED_ORIGIN = "https://unauthorized-origin.example.com"


@pytest.fixture
def client():
    """TestClient with database dependency mocked out."""
    mock_db = MagicMock()
    mock_db.execute.return_value = None

    def override_get_db():
        yield mock_db

    from app.db.session import get_db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_cors_preflight_allowed_vercel_origin(client):
    """Preflight OPTIONS request from deployed Vercel frontend is allowed."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": VERCEL_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == VERCEL_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allow_headers
    assert "content-type" in allow_headers


def test_cors_preflight_post_allowed_vercel_origin(client):
    """Preflight OPTIONS request for POST from Vercel frontend is allowed."""
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": VERCEL_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == VERCEL_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_simple_get_allowed_vercel_origin(client):
    """Simple GET request from deployed Vercel frontend includes CORS origin header."""
    response = client.get(
        "/api/v1/health",
        headers={"Origin": VERCEL_ORIGIN},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == VERCEL_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_disallowed_origin_rejected(client):
    """Preflight OPTIONS request from an unrelated/unauthorized origin is rejected."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": UNAUTHORIZED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )
    # CORSMiddleware rejects disallowed preflight with 400 Bad Request
    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") != UNAUTHORIZED_ORIGIN


def test_cors_simple_get_disallowed_origin_no_cors_header(client):
    """Simple request from an unrelated origin does not receive Access-Control-Allow-Origin."""
    response = client.get(
        "/api/v1/health",
        headers={"Origin": UNAUTHORIZED_ORIGIN},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("origin", [
    "http://localhost:5173",
    "http://localhost:3000",
])
def test_cors_localhost_origins_preserved(client, origin):
    """Local development origins continue to be allowed."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_no_wildcard_with_credentials():
    """Wildcard origin '*' must not be present when credentials are true."""
    settings = get_settings()
    assert "*" not in settings.allowed_origins
    assert VERCEL_ORIGIN in settings.allowed_origins


def test_settings_allowed_origins_parsing():
    """Settings flexibly parses comma-separated strings, json lists, and strips trailing slashes."""
    s_comma = Settings(allowed_origins="https://aicte-verify-ai-beta.vercel.app/, http://localhost:5173")
    assert s_comma.allowed_origins == [
        "https://aicte-verify-ai-beta.vercel.app",
        "http://localhost:5173",
    ]

    s_json = Settings(allowed_origins='["https://aicte-verify-ai-beta.vercel.app/"]')
    assert s_json.allowed_origins == ["https://aicte-verify-ai-beta.vercel.app"]
