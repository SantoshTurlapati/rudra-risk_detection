import hashlib
import json
import re
from collections import defaultdict
from urllib.parse import urlparse
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db, get_current_user, require_organization_id
from app.db.models import Campaign, Investigation, User
from app.schemas.all_schemas import CampaignResponse

router = APIRouter(prefix="/campaigns", tags=["Scam Campaigns"])


def _json_object(value: str | None) -> dict:
    try:
        result = json.loads(value or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    return result if isinstance(result, dict) else {}


def _analysis_evidence(findings: dict) -> dict[str, set[str]]:
    details = findings.get("details")
    if not isinstance(details, dict):
        return {}

    evidence: dict[str, set[str]] = defaultdict(set)
    urls = details.get("urls")
    if isinstance(urls, list):
        for item in urls:
            if not isinstance(item, dict):
                continue
            raw_url = item.get("url") or item.get("hostname")
            if not isinstance(raw_url, str) or not raw_url.strip():
                continue
            candidate = raw_url.strip()
            parsed = urlparse(candidate if "://" in candidate else f"//{candidate}")
            hostname = (parsed.hostname or "").rstrip(".").casefold()
            if hostname:
                evidence["url_domain"].add(hostname)

    scam_dna = details.get("scam_dna")
    excerpts = scam_dna.get("evidence") if isinstance(scam_dna, dict) else None
    if isinstance(excerpts, list):
        for item in excerpts:
            text = item.get("excerpt") if isinstance(item, dict) else item
            if not isinstance(text, str):
                continue
            normalized = re.sub(r"\s+", " ", text).strip().casefold()
            if len(normalized) >= 20:
                evidence["message_excerpt_sha256"].add(
                    hashlib.sha256(normalized.encode("utf-8")).hexdigest()
                )

    for key in ("dhash", "image_hash"):
        image_hash = details.get(key)
        if isinstance(image_hash, str) and image_hash.strip():
            evidence["image_hash"].add(image_hash.strip().casefold())

    app_package = details.get("package_name")
    if isinstance(app_package, str) and app_package.strip():
        evidence["app_package"].add(app_package.strip().casefold())

    return evidence


def _cluster_suggestions(cases: list[Investigation], limit: int = 100) -> list[dict]:
    case_evidence = [
        (case, _analysis_evidence(_json_object(case.findings_json)))
        for case in cases
    ]
    suggestions = []
    for index, (left_case, left_evidence) in enumerate(case_evidence):
        for right_case, right_evidence in case_evidence[index + 1:]:
            shared = []
            for evidence_type in sorted(left_evidence.keys() & right_evidence.keys()):
                shared_values = left_evidence[evidence_type] & right_evidence[evidence_type]
                for value in sorted(shared_values):
                    if evidence_type == "url_domain":
                        display_value = value
                    elif evidence_type == "message_excerpt_sha256":
                        display_value = f"Exact message excerpt fingerprint: {value[:16]}"
                    elif evidence_type == "image_hash":
                        display_value = f"Exact image hash: {value[:32]}"
                    else:
                        display_value = f"Matching package identifier: {value}"
                    shared.append({
                        "evidence_type": evidence_type,
                        "indicator": display_value,
                    })
            if len({item["evidence_type"] for item in shared}) < 2:
                continue
            suggestions.append({
                "cases": [
                    {"id": left_case.id, "case_number": left_case.case_number},
                    {"id": right_case.id, "case_number": right_case.case_number},
                ],
                "shared_evidence": shared,
                "status": "possible_cluster",
                "confidence": None,
                "limitations": [
                    "This is a review suggestion based on multiple exact, saved evidence types.",
                    "Shared evidence does not establish common ownership, coordination, or malicious intent.",
                    "Only the 500 most recently updated organization cases are considered.",
                ],
            })
            if len(suggestions) >= limit:
                return suggestions
    return suggestions


@router.get("", response_model=List[CampaignResponse])
def get_campaigns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    return db.query(Campaign).filter(
        Campaign.organization_id == organization_id
    ).order_by(Campaign.related_entities_count.desc()).all()


@router.get("/cluster-suggestions")
def get_campaign_cluster_suggestions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    cases = db.query(Investigation).filter(
        Investigation.organization_id == organization_id
    ).order_by(
        Investigation.updated_at.desc(),
        Investigation.created_at.desc(),
    ).limit(500).all()
    return {
        "mode": "analysis of persisted case evidence; no external discovery",
        "suggestions": _cluster_suggestions(cases),
    }


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    organization_id = require_organization_id(current_user)
    camp = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.organization_id == organization_id
    ).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return camp
