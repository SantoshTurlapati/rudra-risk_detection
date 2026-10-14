import json
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db, get_current_user, require_organization_id
from app.db.models import AuditLog, User, Organization
from app.core.config import settings
from app.providers.discovery import provider_statuses

router = APIRouter(prefix="/settings", tags=["Settings & Integrations"])


def _serialize_audit_log(log: AuditLog, user_names: dict[str, str]) -> dict:
    entry = {
        "action": log.action,
        "user": user_names.get(log.user_id, "Unknown user"),
        "timestamp": log.created_at.isoformat() if log.created_at else None,
        "details": None,
    }
    if log.action == "brand_verification_status_updated":
        try:
            stored_details = json.loads(log.details_json or "{}")
        except (json.JSONDecodeError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored brand verification audit data is invalid.",
            ) from exc
        if not isinstance(stored_details, dict):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored brand verification audit data is invalid.",
            )
        previous_status = stored_details.get("previous_status")
        new_status = stored_details.get("new_status")
        if type(previous_status) is not bool or type(new_status) is not bool:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored brand verification audit data is invalid.",
            )
        entry["details"] = {
            "previous_status": previous_status,
            "new_status": new_status,
        }
    return entry


@router.get("")
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    organization_id = require_organization_id(current_user)
    org = db.query(Organization).filter(
        Organization.id == organization_id
    ).first()
    organization_users = db.query(User).filter(
        User.organization_id == organization_id
    ).all()
    user_names = {user.id: user.full_name for user in organization_users}
    audit_logs = db.query(AuditLog).filter(
        AuditLog.organization_id == organization_id
    ).order_by(AuditLog.created_at.desc()).limit(50).all()
    return {
        "user_profile": {
            "full_name": current_user.full_name,
            "email": current_user.email,
            "username": current_user.username,
            "role": current_user.role,
            "avatar_url": current_user.avatar_url
        },
        "organization": {
            "name": org.name if org else None,
            "slug": org.slug if org else None,
            "active_seats": sum(1 for user in organization_users if user.is_active),
            "database_engine": settings.DATABASE_URL.split(":", 1)[0]
        },
        "integrations": provider_statuses(),
        "detection_engine": {
            "homoglyph_detection": "Enabled",
            "rapidfuzz_matching": "Enabled (Threshold: 70%)",
            "perceptual_image_hashing": "Candidate hashing enabled; official reference comparison unavailable",
            "url_inspection": "Lexical checks enabled; URLs are not fetched",
            "scam_dna_heuristics": "Enabled"
        },
        "audit_logs": [
            _serialize_audit_log(log, user_names)
            for log in audit_logs
        ]
    }
