import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db, get_current_user, require_organization_id
from app.db.models import AuditLog, BrandProfile, User
from app.schemas.all_schemas import BrandCreate, BrandUpdate, BrandResponse

router = APIRouter(prefix="/brands", tags=["Brand Registry"])

def serialize_brand(b: BrandProfile) -> dict:
    return {
        "id": b.id,
        "organization_id": b.organization_id,
        "name": b.name,
        "legal_name": b.legal_name,
        "description": b.description,
        "logo_url": b.logo_url,
        "official_domains": json.loads(b.official_domains or "[]"),
        "official_socials": json.loads(b.official_socials or "[]"),
        "official_apps": json.loads(b.official_apps or "[]"),
        "authorized_publishers": json.loads(b.authorized_publishers or "[]"),
        "contact_identifiers": json.loads(b.contact_identifiers or "[]"),
        "is_verified": b.is_verified,
        "created_at": b.created_at
    }

@router.get("", response_model=List[BrandResponse])
def get_brands(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    organization_id = require_organization_id(current_user)
    brands = db.query(BrandProfile).filter(
        BrandProfile.organization_id == organization_id
    ).all()
    return [serialize_brand(b) for b in brands]

@router.post("", response_model=BrandResponse)
def create_brand(brand_in: BrandCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    organization_id = require_organization_id(current_user)
    brand = BrandProfile(
        organization_id=organization_id,
        name=brand_in.name,
        legal_name=brand_in.legal_name,
        description=brand_in.description,
        logo_url=brand_in.logo_url,
        official_domains=json.dumps(brand_in.official_domains),
        official_socials=json.dumps(brand_in.official_socials),
        official_apps=json.dumps(brand_in.official_apps),
        authorized_publishers=json.dumps(brand_in.authorized_publishers),
        contact_identifiers=json.dumps(brand_in.contact_identifiers),
        is_verified=False
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return serialize_brand(brand)

@router.get("/{brand_id}", response_model=BrandResponse)
def get_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    brand = db.query(BrandProfile).filter(
        BrandProfile.id == brand_id,
        BrandProfile.organization_id == organization_id
    ).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return serialize_brand(brand)

@router.patch("/{brand_id}", response_model=BrandResponse)
def update_brand(
    brand_id: str,
    brand_in: BrandUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    brand = db.query(BrandProfile).filter(
        BrandProfile.id == brand_id,
        BrandProfile.organization_id == organization_id
    ).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    if brand_in.is_verified is True and (current_user.role or "").casefold() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization administrators can verify brand records."
        )

    if brand_in.name is not None:
        brand.name = brand_in.name
    if brand_in.legal_name is not None:
        brand.legal_name = brand_in.legal_name
    if brand_in.description is not None:
        brand.description = brand_in.description
    if brand_in.logo_url is not None:
        brand.logo_url = brand_in.logo_url
    if brand_in.official_domains is not None:
        brand.official_domains = json.dumps(brand_in.official_domains)
    if brand_in.official_socials is not None:
        brand.official_socials = json.dumps(brand_in.official_socials)
    if brand_in.official_apps is not None:
        brand.official_apps = json.dumps(brand_in.official_apps)
    if brand_in.authorized_publishers is not None:
        brand.authorized_publishers = json.dumps(brand_in.authorized_publishers)
    if brand_in.contact_identifiers is not None:
        brand.contact_identifiers = json.dumps(brand_in.contact_identifiers)
    if brand_in.is_verified is not None:
        previous_verification_status = brand.is_verified
        brand.is_verified = brand_in.is_verified
        if brand_in.is_verified != previous_verification_status:
            db.add(AuditLog(
                organization_id=organization_id,
                user_id=current_user.id,
                action="brand_verification_status_updated",
                resource_type="brand",
                resource_id=brand.id,
                details_json=json.dumps({
                    "previous_status": previous_verification_status,
                    "new_status": brand_in.is_verified,
                    "note": "Admin-marked registry status; independent ownership verification is not implied.",
                }),
            ))

    db.commit()
    db.refresh(brand)
    return serialize_brand(brand)

@router.delete("/{brand_id}")
def delete_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    brand = db.query(BrandProfile).filter(
        BrandProfile.id == brand_id,
        BrandProfile.organization_id == organization_id
    ).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    db.delete(brand)
    db.commit()
    return {"message": "Brand deleted successfully"}
