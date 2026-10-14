import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_db, require_organization_id
from app.ai.image_validation import MAX_IMAGE_BYTES, ValidatedImage, validate_image_bytes
from app.db.brand_image_references import (
    BrandImageReference,
    is_missing_reference_table_error,
)
from app.db.models import BrandProfile, User
from app.storage.brand_images import (
    PrivateImageStorage,
    StorageUnavailable,
    get_brand_image_storage,
    validate_storage_key,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brands", tags=["Brand Image References"])
_EXTENSIONS = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}


def _schema_unavailable(db: Session, exc: OperationalError) -> HTTPException:
    db.rollback()
    logger.exception("Brand image reference schema is not available", exc_info=exc)
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Official image reference storage is not initialized. "
            "An additive database migration requires approval."
        ),
    )


def _database_unavailable(db: Session, exc: OperationalError) -> HTTPException:
    if is_missing_reference_table_error(exc):
        return _schema_unavailable(db, exc)
    db.rollback()
    logger.exception("Database failed while handling an official image reference")
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="The application database is unavailable.",
    )


def _get_brand(db: Session, brand_id: str, organization_id: str) -> BrandProfile:
    brand = db.query(BrandProfile).filter(
        BrandProfile.id == brand_id,
        BrandProfile.organization_id == organization_id,
    ).first()
    if brand is None:
        raise HTTPException(status_code=404, detail="Brand not found.")
    return brand


def _require_admin(user: User) -> None:
    if (user.role or "").casefold() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization administrator permission is required.",
        )


def _serialize(reference: BrandImageReference) -> dict:
    return {
        "id": reference.id,
        "organization_id": reference.organization_id,
        "brand_id": reference.brand_id,
        "media_type": reference.media_type,
        "size_bytes": reference.size_bytes,
        "content_hash": reference.content_hash,
        "status": reference.reference_status,
        "created_at": reference.created_at,
        "updated_at": reference.updated_at,
        "created_by_id": reference.created_by_id,
        "updated_by_id": reference.updated_by_id,
        "authenticity_verified": False,
    }


def _new_storage_key(organization_id: str, brand_id: str, image_format: str) -> str:
    key = (
        f"{organization_id}/{brand_id}/"
        f"{uuid.uuid4().hex}.{_EXTENSIONS[image_format]}"
    )
    validate_storage_key(key)
    return key


def _reference_storage_key(reference: BrandImageReference) -> str:
    try:
        validate_storage_key(reference.storage_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stored official-image reference has an invalid storage key.",
        ) from exc
    return reference.storage_key


def _read_and_validate_upload(file: UploadFile) -> tuple[bytes, ValidatedImage]:
    contents = file.file.read(MAX_IMAGE_BYTES + 1)
    try:
        return contents, validate_image_bytes(contents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _storage_error(exc: Exception) -> HTTPException:
    if isinstance(exc, StorageUnavailable):
        detail = str(exc)
    else:
        logger.exception("Private official-image storage operation failed")
        detail = "Private official-image storage operation failed."
    return HTTPException(status_code=503, detail=detail)


@router.get("/{brand_id}/image-references")
def list_image_references(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organization_id = require_organization_id(current_user)
    _get_brand(db, brand_id, organization_id)
    try:
        references = db.query(BrandImageReference).filter(
            BrandImageReference.organization_id == organization_id,
            BrandImageReference.brand_id == brand_id,
        ).order_by(BrandImageReference.created_at.desc()).all()
    except OperationalError as exc:
        raise _database_unavailable(db, exc) from exc
    return {"items": [_serialize(reference) for reference in references]}


@router.post("/{brand_id}/image-references", status_code=201)
def upload_image_reference(
    brand_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: PrivateImageStorage = Depends(get_brand_image_storage),
):
    _require_admin(current_user)
    organization_id = require_organization_id(current_user)
    _get_brand(db, brand_id, organization_id)
    contents, image = _read_and_validate_upload(file)
    key = _new_storage_key(organization_id, brand_id, image.format)
    try:
        storage.put(key, contents, image.media_type)
    except (StorageUnavailable, OSError, ValueError) as exc:
        raise _storage_error(exc) from exc

    reference = BrandImageReference(
        organization_id=organization_id,
        brand_id=brand_id,
        storage_key=key,
        content_hash=image.content_hash,
        media_type=image.media_type,
        size_bytes=len(contents),
        reference_status="active",
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    try:
        db.add(reference)
        db.commit()
        db.refresh(reference)
    except OperationalError as exc:
        db.rollback()
        try:
            storage.delete(key)
        except (StorageUnavailable, OSError, ValueError):
            logger.exception("Failed to clean up image after schema error")
        raise _database_unavailable(db, exc) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        try:
            storage.delete(key)
        except (StorageUnavailable, OSError, ValueError):
            logger.exception("Failed to clean up image after database error")
        logger.exception("Could not save official image reference")
        raise HTTPException(status_code=500, detail="Could not save image reference.") from exc
    return _serialize(reference)


@router.put("/{brand_id}/image-references/{reference_id}")
def replace_image_reference(
    brand_id: str,
    reference_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: PrivateImageStorage = Depends(get_brand_image_storage),
):
    _require_admin(current_user)
    organization_id = require_organization_id(current_user)
    _get_brand(db, brand_id, organization_id)
    contents, image = _read_and_validate_upload(file)
    try:
        reference = db.query(BrandImageReference).filter(
            BrandImageReference.id == reference_id,
            BrandImageReference.organization_id == organization_id,
            BrandImageReference.brand_id == brand_id,
        ).first()
    except OperationalError as exc:
        raise _database_unavailable(db, exc) from exc
    if reference is None:
        raise HTTPException(status_code=404, detail="Image reference not found.")
    if reference.reference_status != "active":
        raise HTTPException(status_code=409, detail="Only active references can be replaced.")

    old_key = _reference_storage_key(reference)
    new_key = _new_storage_key(organization_id, brand_id, image.format)
    try:
        storage.put(new_key, contents, image.media_type)
    except (StorageUnavailable, OSError, ValueError) as exc:
        raise _storage_error(exc) from exc
    reference.reference_status = "inactive"
    reference.updated_by_id = current_user.id
    reference.updated_at = datetime.now(timezone.utc)
    replacement = BrandImageReference(
        organization_id=organization_id,
        brand_id=brand_id,
        storage_key=new_key,
        content_hash=image.content_hash,
        media_type=image.media_type,
        size_bytes=len(contents),
        reference_status="active",
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    try:
        db.add(replacement)
        db.commit()
        db.refresh(replacement)
    except OperationalError as exc:
        db.rollback()
        try:
            storage.delete(new_key)
        except (StorageUnavailable, OSError, ValueError):
            logger.exception("Failed to clean up replacement after schema error")
        raise _database_unavailable(db, exc) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        try:
            storage.delete(new_key)
        except (StorageUnavailable, OSError, ValueError):
            logger.exception("Failed to clean up replacement after database error")
        logger.exception("Could not replace official image reference")
        raise HTTPException(status_code=500, detail="Could not replace image reference.") from exc
    try:
        storage.delete(old_key)
    except (StorageUnavailable, OSError, ValueError) as exc:
        logger.exception("Replacement succeeded but old private image cleanup failed")
        raise HTTPException(
            status_code=503,
            detail="Image was replaced, but cleanup of the prior private object failed.",
        ) from exc
    return _serialize(replacement)


@router.delete("/{brand_id}/image-references/{reference_id}", status_code=204)
def remove_image_reference(
    brand_id: str,
    reference_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: PrivateImageStorage = Depends(get_brand_image_storage),
):
    _require_admin(current_user)
    organization_id = require_organization_id(current_user)
    _get_brand(db, brand_id, organization_id)
    try:
        reference = db.query(BrandImageReference).filter(
            BrandImageReference.id == reference_id,
            BrandImageReference.organization_id == organization_id,
            BrandImageReference.brand_id == brand_id,
        ).first()
    except OperationalError as exc:
        raise _database_unavailable(db, exc) from exc
    if reference is None:
        raise HTTPException(status_code=404, detail="Image reference not found.")
    key = _reference_storage_key(reference)
    if reference.reference_status != "inactive":
        reference.reference_status = "inactive"
        reference.updated_by_id = current_user.id
        reference.updated_at = datetime.now(timezone.utc)
        try:
            db.commit()
        except OperationalError as exc:
            raise _schema_unavailable(db, exc) from exc
        except SQLAlchemyError as exc:
            db.rollback()
            logger.exception("Could not remove official image reference")
            raise HTTPException(status_code=500, detail="Could not remove image reference.") from exc
    try:
        storage.delete(key)
    except (StorageUnavailable, OSError, ValueError) as exc:
        logger.exception("Reference was disabled but private object cleanup failed")
        raise HTTPException(
            status_code=503,
            detail="Reference was disabled, but cleanup of its private object failed.",
        ) from exc
