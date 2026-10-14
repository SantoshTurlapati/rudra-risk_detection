import csv
import io
import json
import unicodedata
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db, get_current_user, require_organization_id
from app.db.models import Investigation, BrandProfile, User

router = APIRouter(prefix="/reports", tags=["Investigation Reports"])


def _sanitize_csv_cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    prefix_length = 0
    for character in text:
        if character.isspace() or unicodedata.category(character).startswith("C"):
            prefix_length += 1
            continue
        break
    normalized = text[prefix_length:]
    if normalized.startswith(("=", "+", "-", "@")):
        return f"'{normalized}"
    return text


@router.get("")
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    organization_id = require_organization_id(current_user)
    cases = db.query(Investigation).filter(
        Investigation.organization_id == organization_id
    ).order_by(Investigation.created_at.desc()).all()
    reports = []
    for c in cases:
        brand = None
        if c.brand_id:
            brand = db.query(BrandProfile).filter(
                BrandProfile.id == c.brand_id,
                BrandProfile.organization_id == organization_id
            ).first()
        try:
            findings = json.loads(c.findings_json or "{}")
        except json.JSONDecodeError:
            findings = {"raw": c.findings_json}
        reports.append({
            "id": f"REP-{c.case_number}",
            "case_number": c.case_number,
            "title": f"Threat Assessment Report: {c.indicator}",
            "brand_name": brand.name if brand else None,
            "indicator": c.indicator,
            "type": c.type,
            "risk_score": c.risk_score,
            "confidence": c.confidence,
            "severity": c.severity,
            "status": c.status,
            "findings": findings,
            "created_at": c.created_at
        })
    return reports

@router.get("/{case_id}/download-csv")
def download_csv(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    case = db.query(Investigation).filter(
        Investigation.organization_id == organization_id,
        (Investigation.id == case_id) | (Investigation.case_number == case_id)
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Report Field", "Value"])
    writer.writerow(["Case Number", _sanitize_csv_cell(case.case_number)])
    writer.writerow(["Indicator", _sanitize_csv_cell(case.indicator)])
    writer.writerow(["Threat Type", _sanitize_csv_cell(case.type)])
    writer.writerow([
        "Risk Score (0-100)",
        _sanitize_csv_cell(case.risk_score if case.risk_score is not None else "Not assessed")
    ])
    writer.writerow([
        "Stored Confidence (Provenance Unknown)",
        _sanitize_csv_cell(f"{case.confidence}%" if case.confidence is not None else "Not assessed")
    ])
    writer.writerow(["Status", _sanitize_csv_cell(case.status)])
    writer.writerow(["Severity", _sanitize_csv_cell(case.severity)])
    writer.writerow(["Analyst Notes", _sanitize_csv_cell(case.analyst_notes or "N/A")])
    writer.writerow(["Detection Timestamp", _sanitize_csv_cell(case.created_at.isoformat() if case.created_at else "N/A")])
    try:
        saved_findings = json.loads(case.findings_json or "{}")
    except (json.JSONDecodeError, TypeError):
        saved_findings = {}
    if not isinstance(saved_findings, dict):
        saved_findings = {}
    writer.writerow([
        "Record Provenance",
        _sanitize_csv_cell(json.dumps(saved_findings.get("_record_provenance", {}))),
    ])
    writer.writerow([
        "Review History",
        _sanitize_csv_cell(json.dumps(saved_findings.get("_review_history", []))),
    ])
    writer.writerow(["Findings JSON", _sanitize_csv_cell(case.findings_json)])
    writer.writerow(["Legal Disclaimer", _sanitize_csv_cell("AI-assisted heuristic analysis. Does not constitute human judicial proof.")])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=RudraShield_{case.case_number}_Report.csv"}
    )
