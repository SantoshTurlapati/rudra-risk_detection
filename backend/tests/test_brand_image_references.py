import io
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.api.v1.brand_images import get_brand_image_storage
from app.api.v1.deps import get_current_user, get_db
from app.core.config import Settings
from app.db.brand_image_references import BrandImageReference
from app.db.models import BrandProfile, Organization, User
from app.db.session import Base, SessionLocal
from app.main import app
from app.storage.brand_images import (
    LocalPrivateImageStorage,
    StorageUnavailable,
    validate_storage_key,
)

client = TestClient(app)


class MemoryImageStorage:
    def __init__(self):
        self.objects = {}
        self.fail_writes = False
        self.fail_reads = False
        self.fail_deletes = False

    def put(self, key, data, media_type):
        if self.fail_writes:
            raise StorageUnavailable("storage test outage")
        self.objects[key] = (data, media_type)

    def get(self, key):
        if self.fail_reads:
            raise StorageUnavailable("storage read test outage")
        if key not in self.objects:
            raise FileNotFoundError(key)
        return self.objects[key][0]

    def delete(self, key):
        if self.fail_deletes:
            raise StorageUnavailable("storage delete test outage")
        self.objects.pop(key, None)


def _image_bytes(color="white"):
    image = Image.new("RGB", (120, 90), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 40, 70), fill="black")
    draw.ellipse((65, 25, 105, 65), fill="blue" if color == "white" else "red")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _image_variant(data, size=None, image_format="PNG", **options):
    with Image.open(io.BytesIO(data)) as image:
        if size:
            image = image.resize(size, Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(output, format=image_format, **options)
    return output.getvalue()


def _unrelated_image_bytes():
    image = Image.new("RGB", (120, 90), "black")
    ImageDraw.Draw(image).polygon(
        [(5, 5), (115, 8), (60, 85)], fill="yellow"
    )
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _register_user(role="admin"):
    suffix = uuid.uuid4().hex[:10]
    email = f"image-{suffix}@example.com"
    password = "SafeTestPass123!"
    registered = client.post("/api/v1/auth/register", json={
        "email": email,
        "username": f"image_{suffix}",
        "password": password,
        "full_name": "Image Test User",
        "organization_name": f"Image Test Org {suffix}",
    })
    assert registered.status_code == 200
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        user.role = role
        db.commit()
    logged_in = client.post("/api/v1/auth/login", json={
        "username_or_email": email,
        "password": password,
    })
    assert logged_in.status_code == 200
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


def _create_brand(headers):
    response = client.post("/api/v1/brands", headers=headers, json={
        "name": f"Image Brand {uuid.uuid4().hex[:8]}",
    })
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def image_storage(monkeypatch):
    storage = MemoryImageStorage()
    monkeypatch.setitem(app.dependency_overrides, get_brand_image_storage, lambda: storage)
    yield storage
    app.dependency_overrides.pop(get_brand_image_storage, None)


def test_image_reference_model_is_not_registered_for_startup_create_all():
    assert "brand_image_references" not in Base.metadata.tables


def test_unapproved_schema_is_reported_without_creating_it(monkeypatch, image_storage):
    with tempfile.TemporaryDirectory(prefix="brand-reference-schema-test-") as directory:
        database_path = Path(directory, "isolated.db")
        isolated_engine = create_engine(f"sqlite:///{database_path}")
        Base.metadata.create_all(bind=isolated_engine)
        IsolatedSession = sessionmaker(bind=isolated_engine)
        with IsolatedSession() as db:
            organization = Organization(name="Schema Test", slug=uuid.uuid4().hex)
            db.add(organization)
            db.flush()
            user = User(
                organization_id=organization.id,
                email=f"{uuid.uuid4().hex}@example.com",
                hashed_password="unused-test-hash",
                full_name="Schema Test Admin",
                role="admin",
                is_active=True,
            )
            brand = BrandProfile(organization_id=organization.id, name="Schema Test Brand")
            db.add_all([user, brand])
            db.commit()
            db.refresh(user)
            db.refresh(brand)
            user_id = user.id
            brand_id = brand.id

        def isolated_db_dependency():
            with IsolatedSession() as session:
                yield session

        def isolated_user_dependency():
            with IsolatedSession() as session:
                return session.get(User, user_id)

        monkeypatch.setitem(app.dependency_overrides, get_db, isolated_db_dependency)
        monkeypatch.setitem(app.dependency_overrides, get_current_user, isolated_user_dependency)
        try:
            response = client.get(
                f"/api/v1/brands/{brand_id}/image-references"
            )
            assert response.status_code == 503
            assert "migration requires approval" in response.json()["detail"]
            analysis = client.post(
                "/api/v1/analysis/image",
                data={"brand_id": brand_id},
                files={"file": ("candidate.png", _image_bytes(), "image/png")},
            )
            assert analysis.status_code == 503
            assert "migration requires approval" in analysis.json()["detail"]
            assert not inspect(isolated_engine).has_table("brand_image_references")
        finally:
            isolated_engine.dispose()


def test_additive_sqlite_migration_applies_only_to_isolated_database():
    migration = Path(__file__).parents[1] / "migrations" / "001_brand_image_references.sqlite.sql"
    with tempfile.TemporaryDirectory(prefix="brand-reference-migration-test-") as directory:
        isolated_engine = create_engine(f"sqlite:///{Path(directory, 'isolated.db')}")
        try:
            Base.metadata.create_all(bind=isolated_engine)
            with isolated_engine.begin() as connection:
                for statement in migration.read_text(encoding="utf-8").split(";"):
                    if statement.strip():
                        connection.exec_driver_sql(statement)
            inspector = inspect(isolated_engine)
            assert inspector.has_table("brand_image_references")
            assert {
                item["name"] for item in inspector.get_columns("brand_image_references")
            } == {
                "id", "organization_id", "brand_id", "storage_key", "content_hash",
                "media_type", "size_bytes", "reference_status", "created_by_id",
                "updated_by_id", "created_at", "updated_at",
            }
            foreign_keys = inspector.get_foreign_keys("brand_image_references")
            assert {item["referred_table"] for item in foreign_keys} == {
                "organizations", "brand_profiles", "users",
            }
        finally:
            isolated_engine.dispose()


@pytest.mark.parametrize("threshold", [-0.1, 100.1])
def test_image_review_threshold_must_be_between_zero_and_one_hundred(threshold):
    with pytest.raises(ValidationError, match="BRAND_IMAGE_REVIEW_THRESHOLD"):
        Settings(
            SECRET_KEY="test-only-secret-key-not-for-production-0123456789",
            BRAND_IMAGE_REVIEW_THRESHOLD=threshold,
        )


@pytest.mark.parametrize("key", [
    "../outside/evil.png",
    "/org/brand/file.png",
    "org\\brand\\file.png",
    "org/brand/sub/file.png",
])
def test_storage_rejects_unsafe_object_keys(key):
    with pytest.raises(ValueError, match="Unsafe"):
        validate_storage_key(key)


def test_local_private_storage_round_trips_and_removes_generated_key():
    with tempfile.TemporaryDirectory() as directory:
        storage = LocalPrivateImageStorage(directory)
        key = "org-id/brand-id/reference.png"
        data = _image_bytes()
        storage.put(key, data, "image/png")
        assert storage.get(key) == data
        storage.delete(key)
        with pytest.raises(FileNotFoundError):
            storage.get(key)


def test_local_private_storage_rejects_mismatched_media_type():
    with tempfile.TemporaryDirectory() as directory:
        storage = LocalPrivateImageStorage(directory)
        with pytest.raises(ValueError, match="does not match"):
            storage.put("org-id/brand-id/reference.png", _image_bytes(), "image/jpeg")
        assert not Path(directory, "org-id", "brand-id", "reference.png").exists()


def test_reference_upload_rejects_invalid_and_oversized_files(image_storage):
    headers = _register_user()
    brand = _create_brand(headers)
    invalid = client.post(
        f"/api/v1/brands/{brand['id']}/image-references",
        headers=headers,
        files={"file": ("bad.png", b"not an image", "image/png")},
    )
    assert invalid.status_code == 400
    oversized = client.post(
        f"/api/v1/brands/{brand['id']}/image-references",
        headers=headers,
        files={"file": ("large.png", b"x" * (10 * 1024 * 1024 + 1), "image/png")},
    )
    assert oversized.status_code == 400
    assert image_storage.objects == {}


def test_reference_upload_rejects_unsupported_format_and_pixel_limit(
    image_storage, monkeypatch
):
    headers = _register_user()
    brand = _create_brand(headers)
    endpoint = f"/api/v1/brands/{brand['id']}/image-references"
    gif = io.BytesIO()
    Image.new("RGB", (20, 20), "red").save(gif, format="GIF")
    unsupported = client.post(
        endpoint,
        headers=headers,
        files={"file": ("logo.gif", gif.getvalue(), "image/gif")},
    )
    assert unsupported.status_code == 400
    assert "Unsupported image format" in unsupported.json()["detail"]

    import app.ai.image_validation as image_validation

    monkeypatch.setattr(image_validation, "MAX_IMAGE_PIXELS", 100)
    dimensions = client.post(
        endpoint,
        headers=headers,
        files={"file": ("logo.png", _image_bytes(), "image/png")},
    )
    assert dimensions.status_code == 400
    assert "pixel limit" in dimensions.json()["detail"]
    assert image_storage.objects == {}


def test_reference_upload_uses_decoded_type_and_storage_failure_is_explicit(image_storage):
    headers = _register_user()
    brand = _create_brand(headers)
    uploaded = client.post(
        f"/api/v1/brands/{brand['id']}/image-references",
        headers=headers,
        files={"file": ("not-an-extension.txt", _image_bytes(), "text/plain")},
    )
    assert uploaded.status_code == 201
    reference = uploaded.json()
    assert reference["media_type"] == "image/png"
    assert reference["authenticity_verified"] is False
    assert reference["status"] == "active"

    image_storage.fail_writes = True
    replacement_failed = client.put(
        f"/api/v1/brands/{brand['id']}/image-references/{reference['id']}",
        headers=headers,
        files={"file": ("replacement.png", _image_bytes("gray"), "image/png")},
    )
    assert replacement_failed.status_code == 503
    assert client.get(
        f"/api/v1/brands/{brand['id']}/image-references",
        headers=headers,
    ).json()["items"][0]["status"] == "active"
    failed = client.post(
        f"/api/v1/brands/{brand['id']}/image-references",
        headers=headers,
        files={"file": ("logo.png", _image_bytes(), "image/png")},
    )
    assert failed.status_code == 503
    assert failed.json()["detail"] == "storage test outage"


def test_comparison_and_removal_report_private_storage_failures(image_storage):
    headers = _register_user()
    brand = _create_brand(headers)
    endpoint = f"/api/v1/brands/{brand['id']}/image-references"
    created = client.post(
        endpoint, headers=headers,
        files={"file": ("logo.png", _image_bytes(), "image/png")},
    )
    assert created.status_code == 201
    reference_id = created.json()["id"]

    image_storage.fail_reads = True
    comparison = client.post(
        "/api/v1/analysis/image",
        headers=headers,
        data={"brand_id": brand["id"]},
        files={"file": ("candidate.png", _image_bytes(), "image/png")},
    )
    assert comparison.status_code == 503
    assert comparison.json()["detail"] == "Private official-image storage is unavailable."

    image_storage.fail_reads = False
    image_storage.fail_deletes = True
    removal = client.delete(f"{endpoint}/{reference_id}", headers=headers)
    assert removal.status_code == 503
    assert client.get(endpoint, headers=headers).json()["items"][0]["status"] == "inactive"
    image_storage.fail_deletes = False
    assert client.delete(f"{endpoint}/{reference_id}", headers=headers).status_code == 204


def test_invalid_persisted_storage_key_fails_closed_before_storage_access(image_storage):
    headers = _register_user()
    brand = _create_brand(headers)
    uploaded = client.post(
        f"/api/v1/brands/{brand['id']}/image-references",
        headers=headers,
        files={"file": ("logo.png", _image_bytes(), "image/png")},
    )
    assert uploaded.status_code == 201

    with SessionLocal() as db:
        reference = db.query(BrandImageReference).filter(
            BrandImageReference.id == uploaded.json()["id"]
        ).one()
        reference.storage_key = "../outside/logo.png"
        db.commit()

    before_read = set(image_storage.objects)
    comparison = client.post(
        "/api/v1/analysis/image",
        headers=headers,
        data={"brand_id": brand["id"]},
        files={"file": ("candidate.png", _image_bytes(), "image/png")},
    )
    assert comparison.status_code == 503
    assert "invalid storage key" in comparison.json()["detail"]
    assert set(image_storage.objects) == before_read

    removal = client.delete(
        f"/api/v1/brands/{brand['id']}/image-references/{uploaded.json()['id']}",
        headers=headers,
    )
    assert removal.status_code == 503
    assert "invalid storage key" in removal.json()["detail"]
    with SessionLocal() as db:
        reference = db.query(BrandImageReference).filter(
            BrandImageReference.id == uploaded.json()["id"]
        ).one()
        assert reference.reference_status == "active"
    assert set(image_storage.objects) == before_read


def test_reference_comparison_replace_and_remove_are_explainable(image_storage):
    headers = _register_user()
    brand = _create_brand(headers)
    endpoint = f"/api/v1/brands/{brand['id']}/image-references"
    uploaded = client.post(
        endpoint, headers=headers,
        files={"file": ("logo.png", _image_bytes(), "image/png")},
    )
    assert uploaded.status_code == 201
    reference = uploaded.json()

    result = client.post(
        "/api/v1/analysis/image",
        headers=headers,
        data={"brand_id": brand["id"]},
        files={"file": ("candidate.png", _image_bytes(), "image/png")},
    )
    assert result.status_code == 200
    comparison = result.json()["details"]["comparison"]
    assert comparison["status"] == "compared"
    assert comparison["references_compared"] == 1
    assert comparison["matches"][0]["similarity_score"] == 100.0
    assert "not proof of impersonation" in comparison["explanation"]
    assert result.json()["status"] == "Unverified"
    assert result.json()["is_suspicious"] is True
    assert "not independently verified" in result.json()["missing_information"][0]

    replacement = client.put(
        f"{endpoint}/{reference['id']}",
        headers=headers,
        files={"file": ("new.png", _image_bytes("gray"), "image/png")},
    )
    assert replacement.status_code == 200
    assert replacement.json()["content_hash"] != reference["content_hash"]
    listed = client.get(endpoint, headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 2
    assert sum(item["status"] == "active" for item in listed.json()["items"]) == 1

    removed = client.delete(f"{endpoint}/{replacement.json()['id']}", headers=headers)
    assert removed.status_code == 204
    assert all(
        item["status"] == "inactive"
        for item in client.get(endpoint, headers=headers).json()["items"]
    )
    unavailable = client.post(
        "/api/v1/analysis/image",
        headers=headers,
        data={"brand_id": brand["id"]},
        files={"file": ("candidate.png", _image_bytes(), "image/png")},
    )
    assert unavailable.status_code == 200
    assert unavailable.json()["details"]["comparison"]["status"] == "no_valid_reference"


def test_reference_comparison_accepts_resized_compressed_and_rejects_unrelated(image_storage):
    headers = _register_user()
    brand = _create_brand(headers)
    endpoint = f"/api/v1/brands/{brand['id']}/image-references"
    reference_data = _image_bytes()
    uploaded = client.post(
        endpoint,
        headers=headers,
        files={"file": ("official.png", reference_data, "application/octet-stream")},
    )
    assert uploaded.status_code == 201

    for candidate in (
        _image_variant(reference_data, size=(240, 180)),
        _image_variant(reference_data, size=(240, 180), image_format="JPEG", quality=78),
    ):
        response = client.post(
            "/api/v1/analysis/image",
            headers=headers,
            data={"brand_id": brand["id"]},
            files={"file": ("candidate.jpg", candidate, "image/jpeg")},
        )
        assert response.status_code == 200
        assert response.json()["details"]["comparison"]["matches"][0]["similarity_score"] >= 75.0

    unrelated = client.post(
        "/api/v1/analysis/image",
        headers=headers,
        data={"brand_id": brand["id"]},
        files={"file": ("candidate.png", _unrelated_image_bytes(), "image/png")},
    )
    assert unrelated.status_code == 200
    unrelated_result = unrelated.json()
    assert unrelated_result["details"]["comparison"]["matches"][0]["similarity_score"] < 75.0
    assert unrelated_result["is_suspicious"] is False
    assert unrelated_result["status"] == "Unverified"


def test_reference_end_to_end_with_private_filesystem_adapter(image_storage):
    del image_storage
    with tempfile.TemporaryDirectory(prefix="brand-reference-storage-test-") as directory:
        storage = LocalPrivateImageStorage(directory)
        app.dependency_overrides[get_brand_image_storage] = lambda: storage
        try:
            headers = _register_user()
            brand = _create_brand(headers)
            endpoint = f"/api/v1/brands/{brand['id']}/image-references"
            created = client.post(
                endpoint,
                headers=headers,
                files={"file": ("logo.png", _image_bytes(), "image/png")},
            )
            assert created.status_code == 201
            listed = client.get(endpoint, headers=headers)
            assert listed.status_code == 200
            assert listed.json()["items"][0]["id"] == created.json()["id"]
            result = client.post(
                "/api/v1/analysis/image",
                headers=headers,
                data={"brand_id": brand["id"]},
                files={"file": ("candidate.png", _image_bytes(), "image/png")},
            )
            assert result.status_code == 200
            assert result.json()["details"]["comparison"]["status"] == "compared"
            assert result.json()["details"]["comparison"]["matches"][0]["similarity_score"] == 100.0
            assert client.delete(
                f"{endpoint}/{created.json()['id']}", headers=headers
            ).status_code == 204
            assert client.get(endpoint, headers=headers).json()["items"][0]["status"] == "inactive"
        finally:
            app.dependency_overrides.pop(get_brand_image_storage, None)


def test_reference_mutation_requires_admin_and_reads_are_tenant_scoped(image_storage):
    admin_headers = _register_user()
    brand = _create_brand(admin_headers)
    created = client.post(
        f"/api/v1/brands/{brand['id']}/image-references",
        headers=admin_headers,
        files={"file": ("logo.png", _image_bytes(), "image/png")},
    )
    assert created.status_code == 201

    analyst_headers = _register_user(role="analyst")
    denied = client.post(
        f"/api/v1/brands/{brand['id']}/image-references",
        headers=analyst_headers,
        files={"file": ("logo.png", _image_bytes(), "image/png")},
    )
    assert denied.status_code == 403
    denied_replace = client.put(
        f"/api/v1/brands/{brand['id']}/image-references/{created.json()['id']}",
        headers=analyst_headers,
        files={"file": ("replacement.png", _image_bytes("gray"), "image/png")},
    )
    assert denied_replace.status_code == 403
    denied_remove = client.delete(
        f"/api/v1/brands/{brand['id']}/image-references/{created.json()['id']}",
        headers=analyst_headers,
    )
    assert denied_remove.status_code == 403
    assert client.get(
        f"/api/v1/brands/{brand['id']}/image-references",
        headers=admin_headers,
    ).json()["items"][0]["status"] == "active"

    other_admin_headers = _register_user()
    assert client.get(
        f"/api/v1/brands/{brand['id']}/image-references",
        headers=other_admin_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/v1/brands/{brand['id']}/image-references/{created.json()['id']}",
        headers=other_admin_headers,
    ).status_code == 404


def test_cross_organization_image_reference_routes_and_analysis_are_isolated(image_storage):
    owner_headers = _register_user()
    brand = _create_brand(owner_headers)
    endpoint = f"/api/v1/brands/{brand['id']}/image-references"
    uploaded = client.post(
        endpoint,
        headers=owner_headers,
        files={"file": ("logo.png", _image_bytes(), "image/png")},
    )
    assert uploaded.status_code == 201
    reference_id = uploaded.json()["id"]
    other_headers = _register_user()

    assert client.get(endpoint, headers=other_headers).status_code == 404
    assert client.post(
        endpoint,
        headers=other_headers,
        files={"file": ("logo.png", _image_bytes(), "image/png")},
    ).status_code == 404
    assert client.put(
        f"{endpoint}/{reference_id}",
        headers=other_headers,
        files={"file": ("replacement.png", _image_bytes("gray"), "image/png")},
    ).status_code == 404
    assert client.delete(
        f"{endpoint}/{reference_id}",
        headers=other_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/brands/{brand['id']}",
        headers=other_headers,
    ).status_code == 404
    assert client.patch(
        f"/api/v1/brands/{brand['id']}",
        headers=other_headers,
        json={"name": "Unauthorized rename"},
    ).status_code == 404
    assert client.delete(
        f"/api/v1/brands/{brand['id']}",
        headers=other_headers,
    ).status_code == 404

    cross_organization_analysis = client.post(
        "/api/v1/analysis/image",
        headers=other_headers,
        data={"brand_id": brand["id"]},
        files={"file": ("candidate.png", _image_bytes(), "image/png")},
    )
    assert cross_organization_analysis.status_code == 404

    owner_brand = client.get(
        f"/api/v1/brands/{brand['id']}",
        headers=owner_headers,
    )
    assert owner_brand.status_code == 200
    assert owner_brand.json()["name"] == brand["name"]

    own_analysis = client.post(
        "/api/v1/analysis/image",
        headers=owner_headers,
        data={"brand_id": brand["id"]},
        files={"file": ("candidate.png", _image_bytes(), "image/png")},
    )
    assert own_analysis.status_code == 200
    assert own_analysis.json()["details"]["comparison"]["status"] == "compared"
    assert own_analysis.json()["details"]["comparison"]["references_compared"] == 1
