import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db, get_current_user, require_organization_id
from app.db.models import AuditLog, Investigation, User, Alert, BrandProfile
from app.schemas.all_schemas import (
    InvestigationCreate, InvestigationUpdate, InvestigationResponse
)

router = APIRouter(prefix="/investigations", tags=["Investigations & Cases"])

def serialize_investigation(inv: Investigation) -> dict:
    findings = {}
    if inv.findings_json:
        try:
            findings = json.loads(inv.findings_json)
        except json.JSONDecodeError:
            findings = {"raw": inv.findings_json}

    metadata = {}
    if inv.candidate_metadata:
        try:
            metadata = json.loads(inv.candidate_metadata)
        except json.JSONDecodeError:
            metadata = {}

    return {
        "id": inv.id,
        "case_number": inv.case_number,
        "organization_id": inv.organization_id,
        "brand_id": inv.brand_id,
        "indicator": inv.indicator,
        "type": inv.type,
        "risk_score": inv.risk_score,
        "confidence": inv.confidence,
        "status": inv.status,
        "severity": inv.severity,
        "candidate_name": inv.candidate_name,
        "candidate_metadata": metadata,
        "findings_json": findings,
        "analyst_notes": inv.analyst_notes,
        "created_at": inv.created_at,
        "updated_at": inv.updated_at
    }


def _load_findings(value: Optional[str]) -> dict:
    try:
        findings = json.loads(value or "{}")
    except (json.JSONDecodeError, TypeError):
        return {"legacy_findings_unparsed": True}
    return findings if isinstance(findings, dict) else {"legacy_findings": findings}


@router.get("", response_model=List[InvestigationResponse])
def get_investigations(
    type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    query = db.query(Investigation).filter(
        Investigation.organization_id == organization_id
    ).order_by(Investigation.created_at.desc())
    if type and type != "all":
        query = query.filter(Investigation.type.ilike(f"%{type}%"))
    if status and status != "all":
        query = query.filter(Investigation.status.ilike(f"%{status}%"))
    if search:
        query = query.filter(
            (Investigation.indicator.ilike(f"%{search}%")) |
            (Investigation.case_number.ilike(f"%{search}%"))
        )
    investigations = query.all()
    return [serialize_investigation(inv) for inv in investigations]

@router.post("", response_model=InvestigationResponse)
def create_investigation(
    inv_in: InvestigationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    if inv_in.brand_id and not db.query(BrandProfile.id).filter(
        BrandProfile.id == inv_in.brand_id,
        BrandProfile.organization_id == organization_id
    ).first():
        raise HTTPException(status_code=404, detail="Brand not found")

    created_at = datetime.now(timezone.utc)
    saved_findings = dict(inv_in.findings)
    saved_findings["_review_history"] = []
    saved_findings["_record_provenance"] = {
        "submission_method": "authenticated_api_submission",
        "recorded_by_user_id": current_user.id,
        "recorded_at": created_at.isoformat(),
        "source_attribution": "Submitted evidence; external source verification was not performed by case creation.",
    }
    new_inv = Investigation(
        case_number=f"RS-{uuid.uuid4().hex[:12].upper()}",
        organization_id=organization_id,
        created_by_id=current_user.id,
        brand_id=inv_in.brand_id,
        indicator=inv_in.indicator,
        type=inv_in.type,
        risk_score=inv_in.risk_score,
        confidence=inv_in.confidence,
        status=inv_in.status,
        severity=inv_in.severity,
        candidate_name=inv_in.candidate_name,
        candidate_metadata=json.dumps(inv_in.candidate_metadata),
        findings_json=json.dumps(saved_findings),
        analyst_notes=inv_in.analyst_notes
    )
    db.add(new_inv)
    db.flush()

    # Automatically trigger alert if risk_score >= 70
    if inv_in.risk_score is not None and inv_in.risk_score >= 70:
        alert = Alert(
            organization_id=organization_id,
            case_id=new_inv.id,
            title=f"High Risk Impersonator Detected: {inv_in.indicator[:30]}",
            description=f"Auto-escalated investigation with risk score {inv_in.risk_score}/100.",
            indicator=inv_in.indicator,
            severity="Critical" if inv_in.risk_score >= 85 else "High",
            status="Unread",
            source="Investigation Escalation"
        )
        db.add(alert)

    db.commit()
    db.refresh(new_inv)
    return serialize_investigation(new_inv)

@router.get("/{investigation_id}", response_model=InvestigationResponse)
def get_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    inv = db.query(Investigation).filter(
        Investigation.organization_id == organization_id,
        (Investigation.id == investigation_id) | (Investigation.case_number == investigation_id)
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation case not found")
    return serialize_investigation(inv)

@router.patch("/{investigation_id}", response_model=InvestigationResponse)
def update_investigation(
    investigation_id: str,
    update_in: InvestigationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    inv = db.query(Investigation).filter(
        Investigation.organization_id == organization_id,
        (Investigation.id == investigation_id) | (Investigation.case_number == investigation_id)
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation case not found")

    if (
        update_in.status == "False Positive"
        and inv.status != "False Positive"
        and not update_in.disposition_reason
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A reason is required when marking an investigation as a false positive.",
        )
    if update_in.disposition_reason and (
        update_in.status or inv.status
    ) != "False Positive":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A disposition reason is only accepted for a false-positive review.",
        )

    changes = {}
    if update_in.status is not None:
        previous_status = inv.status
        inv.status = update_in.status
        if update_in.status != previous_status:
            changes["status"] = {
                "previous": previous_status,
                "new": update_in.status,
            }
    if update_in.severity is not None and update_in.severity != inv.severity:
        changes["severity"] = {
            "previous": inv.severity,
            "new": update_in.severity,
        }
    if update_in.severity is not None:
        inv.severity = update_in.severity
    if update_in.risk_score is not None and update_in.risk_score != inv.risk_score:
        changes["risk_score"] = {
            "previous": inv.risk_score,
            "new": update_in.risk_score,
        }
    if (
        update_in.analyst_notes is not None
        and update_in.analyst_notes != inv.analyst_notes
    ):
        changes["analyst_notes"] = {"changed": True}
    if update_in.analyst_notes is not None:
        inv.analyst_notes = update_in.analyst_notes
    if update_in.risk_score is not None:
        inv.risk_score = update_in.risk_score

    if (
        update_in.disposition_reason
        and "status" not in changes
        and (update_in.status or inv.status) == inv.status == "False Positive"
    ):
        changes["disposition_reason"] = {"changed": True}

    if changes:
        event_time = datetime.now(timezone.utc).isoformat()
        findings = _load_findings(inv.findings_json)
        review_history = findings.get("_review_history")
        if not isinstance(review_history, list):
            review_history = []
        event = {
            "recorded_at": event_time,
            "recorded_by_user_id": current_user.id,
            "changes": changes,
        }
        if "status" in changes or "disposition_reason" in changes:
            event["disposition_reason"] = update_in.disposition_reason
        review_history.append(event)
        findings["_review_history"] = review_history
        inv.findings_json = json.dumps(findings)
        db.add(AuditLog(
            organization_id=organization_id,
            user_id=current_user.id,
            action=(
                "investigation_disposition_updated"
                if "status" in changes or "disposition_reason" in changes
                else "investigation_updated"
            ),
            resource_type="investigation",
            resource_id=inv.id,
            details_json=json.dumps({
                **changes,
                "disposition_reason": (
                    update_in.disposition_reason
                    if "status" in changes or "disposition_reason" in changes
                    else None
                ),
            }),
        ))

    db.commit()
    db.refresh(inv)
    return serialize_investigation(inv)
