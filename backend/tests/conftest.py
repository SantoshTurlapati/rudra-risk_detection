import os
import tempfile
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-production-0123456789")
_TEST_DATABASE_DIRECTORY = tempfile.TemporaryDirectory(prefix="rudrashield-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TEST_DATABASE_DIRECTORY.name, 'rudrashield.db').as_posix()}"

import pytest
from app.db.session import engine, Base, SessionLocal
from app.db.seed import seed_database
from app.db.brand_image_references import BrandImageReferenceBase

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    BrandImageReferenceBase.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield
    engine.dispose()
    _TEST_DATABASE_DIRECTORY.cleanup()
