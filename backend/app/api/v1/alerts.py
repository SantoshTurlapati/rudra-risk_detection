from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db, get_current_user, require_organization_id
from app.db.models import Alert, User
from app.schemas.all_schemas import AlertResponse, AlertUpdate

router = APIRouter(prefix="/alerts", tags=["Critical Alerts"])

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    query = db.query(Alert).filter(
        Alert.organization_id == organization_id
    ).order_by(Alert.created_at.desc())
    if severity and severity != "all":
        query = query.filter(Alert.severity.ilike(f"%{severity}%"))
    if status and status != "all":
        query = query.filter(Alert.status.ilike(f"%{status}%"))
    return query.all()

@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.organization_id == organization_id
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: str,
    update_in: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.organization_id == organization_id
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = update_in.status
    if update_in.status == "Resolved":
        alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert
