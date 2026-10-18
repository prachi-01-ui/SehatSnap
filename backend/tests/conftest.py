import pytest
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from backend.app.database import Base, get_db
from backend.app.models import MedicalRecord, ReportDocument, AuditEvent, CareTask, VerificationAuditRecord
from backend.app.seed import seed_database
from backend.app.main import app
import backend.app.storage as storage_module

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_database(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session():
    """Provides a transactional database session per test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db_session, tmp_path, monkeypatch):
    """Provides FastAPI test client wired to test db and temporary uploads directory."""
    # Redirect UPLOADS_DIR to temp directory for test isolation
    test_uploads = tmp_path / "uploads"
    test_uploads.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(storage_module, "UPLOADS_DIR", test_uploads)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
