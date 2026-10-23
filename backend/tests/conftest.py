"""Shared test fixtures for Prompt 02 tests.

Uses an in-memory SQLite database to avoid needing a real PostgreSQL instance.
PyMuPDF works the same way for both.
"""
import io
import uuid
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.api.deps import (
    get_current_active_user,
    get_current_user,
    require_admin,
    require_officer_or_admin,
)
from app.core.security import create_access_token, hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.core.config import get_settings, Settings
from app.services.storage.local import LocalStorageBackend


# ── In-memory SQLite engine ───────────────────────────────────────────────────
# We use check_same_thread=False for compatibility with pytest's threading.
# UUID columns map to TEXT in SQLite which is fine for our string UUIDs.

SQLITE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
)

# SQLite does not enforce FK constraints by default; enable them.
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once for the test session."""
    # SQLite doesn't support PostgreSQL enums — patch them to String
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql

    # Override PostgreSQL UUID to plain String for SQLite
    postgresql.UUID = lambda **kw: sa.String(36)

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """Provide a fresh DB session, rolling back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def tmp_upload_dir(tmp_path):
    """Provide a temporary upload directory for file storage."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return str(upload_dir)


@pytest.fixture()
def storage(tmp_upload_dir):
    """Provide a LocalStorageBackend pointed at a temp directory."""
    return LocalStorageBackend(tmp_upload_dir)


@pytest.fixture()
def override_settings(tmp_upload_dir):
    """Override settings to use temp storage and generous limits."""
    test_settings = Settings(
        database_url=SQLITE_URL,
        upload_dir=tmp_upload_dir,
        max_upload_size_mb=10,
        max_pdf_pages=500,
        secret_key="test-secret",
    )
    return test_settings


@pytest.fixture()
def default_test_user():
    return User(
        id="00000000-0000-0000-0000-000000000001",
        email="test_officer@aicte.gov.in",
        full_name="Test Verification Officer",
        role=UserRole.ADMIN,
        hashed_password=hash_password("Officer@123"),
        is_active=True,
    )


@pytest.fixture()
def client(db, override_settings, default_test_user) -> Generator[TestClient, None, None]:
    """Test client with DB, settings, and default admin/officer user overridden."""
    def override_get_db():
        yield db

    def override_get_settings():
        return override_settings

    def override_user():
        return default_test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_current_active_user] = override_user
    app.dependency_overrides[require_officer_or_admin] = override_user
    app.dependency_overrides[require_admin] = override_user

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def unauthenticated_client(db, override_settings) -> Generator[TestClient, None, None]:
    """Test client with NO auth dependency overrides (tests real JWT auth)."""
    def override_get_db():
        yield db

    def override_get_settings():
        return override_settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Synthetic file fixtures ───────────────────────────────────────────────────

def make_pdf(pages: int = 1) -> bytes:
    """Generate a minimal but valid PDF with the given number of pages using PyMuPDF."""
    import fitz
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Test page {i + 1} — AICTE VerifyAI synthetic fixture")
    data = doc.tobytes()
    doc.close()
    return data


def make_png() -> bytes:
    """Generate a minimal valid 1×1 white PNG."""
    import struct, zlib
    def chunk(name, data):
        c = struct.pack(">I", len(data)) + name + data
        crc = struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
        return c + crc

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)
    raw_row = b"\x00\xff\xff\xff"
    idat = chunk(b"IDAT", zlib.compress(raw_row))
    iend = chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


def make_jpeg() -> bytes:
    """Generate a minimal valid JPEG using Pillow."""
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (8, 8), color=(200, 200, 200))
    img.save(buf, format="JPEG")
    return buf.getvalue()


def make_tiff() -> bytes:
    """Generate a minimal valid TIFF using Pillow."""
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (8, 8), color=(180, 180, 180))
    img.save(buf, format="TIFF")
    return buf.getvalue()


VALID_APPLICATION_PAYLOAD = {
    "institution_name": "Demo Institute of Technology",
    "aicte_permanent_id": "DEMO-2025-001",
    "academic_year": "2025-26",
    "application_category": "new_programme",
    "programme_type": "BE_BTech",
    "description": "Synthetic test application",
    "applicant_name": "Test Officer",
    "applicant_email": "officer@demo.invalid",
}
