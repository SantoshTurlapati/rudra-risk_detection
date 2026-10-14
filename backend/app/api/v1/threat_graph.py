import json
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_db, require_organization_id
from app.db.models import (
    BrandProfile,
    Investigation,
    ThreatEntity,
    ThreatRelationship,
    User,
)

router = APIRouter(prefix="/threat-graph", tags=["Threat Graph"])

_INVESTIGATION_TYPES = {
    "social_profile": "Social Profile",
    "website": "Website",
    "url": "URL",
    "mobile_app": "Mobile App",
    "message": "Message",
    "image": "Image",
}


def _json_object(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {"parse_error": "Stored JSON evidence could not be decoded."}
    return parsed if isinstance(parsed, dict) else {}


def _evidence_lines(findings: dict) -> list[str]:
    evidence = findings.get("findings") or findings.get("evidence") or []
    if not isinstance(evidence, list):
        return []
    return [
        item[:500]
        for item in evidence
        if isinstance(item, str) and item.strip()
    ][:8]


def _node_type(investigation_type: str) -> str:
    normalized = investigation_type.strip().casefold().replace(" ", "_")
    return _INVESTIGATION_TYPES.get(normalized, investigation_type or "Investigation")


@router.get("")
def get_threat_graph(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    organization_id = require_organization_id(current_user)
    entities = db.query(ThreatEntity).filter(
        ThreatEntity.organization_id == organization_id
    ).all()

    entity_ids = [entity.id for entity in entities]
    stored_relationships = []
    if entity_ids:
        stored_relationships = db.query(ThreatRelationship).filter(
            ThreatRelationship.source_id.in_(entity_ids),
            ThreatRelationship.target_id.in_(entity_ids),
        ).all()

    investigations = db.query(Investigation).filter(
        Investigation.organization_id == organization_id
    ).order_by(Investigation.created_at.desc()).all()
    investigation_by_case = {
        item.case_number: item for item in investigations
    }
    brand_ids = {
        item.brand_id for item in investigations if item.brand_id
    }
    brands = db.query(BrandProfile).filter(
        BrandProfile.organization_id == organization_id,
        BrandProfile.id.in_(brand_ids),
    ).all() if brand_ids else []
    brand_by_id = {brand.id: brand for brand in brands}

    nodes = [
        {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type,
            "indicator": entity.indicator,
            "risk_score": entity.risk_score,
            "details": _json_object(entity.metadata_json),
        }
        for entity in entities
    ]
    links = [
        {
            "id": relationship.id,
            "source": relationship.source_id,
            "target": relationship.target_id,
            "relationship_type": relationship.relationship_type,
            "confidence": relationship.confidence,
            "relationship_status": "confirmed",
            "details": {
                "basis": "Explicitly stored threat relationship; external attribution is not independently verified."
            },
        }
        for relationship in stored_relationships
    ]

    investigation_node_ids = {
        investigation.id: f"investigation:{investigation.id}"
        for investigation in investigations
    }
    for investigation in investigations:
        node_id = investigation_node_ids[investigation.id]
        findings = _json_object(investigation.findings_json)
        nodes.append({
            "id": node_id,
            "name": investigation.indicator,
            "type": _node_type(investigation.type),
            "indicator": investigation.indicator,
            "risk_score": investigation.risk_score,
            "details": {
                "case_number": investigation.case_number,
                "status": investigation.status,
                "severity": investigation.severity,
                "created_at": (
                    investigation.created_at.isoformat()
                    if investigation.created_at else None
                ),
                "evidence": _evidence_lines(findings),
            },
        })

        if investigation.brand_id in brand_by_id:
            brand = brand_by_id[investigation.brand_id]
            brand_node_id = f"brand:{brand.id}"
            if not any(node["id"] == brand_node_id for node in nodes):
                nodes.append({
                    "id": brand_node_id,
                    "name": brand.name,
                    "type": "Brand",
                    "indicator": None,
                    "risk_score": None,
                    "details": {
                        "verified": brand.is_verified,
                        "basis": "Brand assigned to the saved investigation record.",
                    },
                })
            links.append({
                "id": f"brand-association:{investigation.id}:{brand.id}",
                "source": node_id,
                "target": brand_node_id,
                "relationship_type": "CASE_ASSOCIATED_WITH_BRAND",
                "confidence": None,
                "relationship_status": "confirmed",
                "details": {
                    "case_number": investigation.case_number,
                    "basis": "Saved investigation brand_id association; not an independent impersonation finding.",
                },
            })

        analysis_details = findings.get("details")
        if not isinstance(analysis_details, dict):
            analysis_details = {}

        embedded_urls = analysis_details.get("urls")
        if isinstance(embedded_urls, list):
            for index, url_evidence in enumerate(embedded_urls):
                if not isinstance(url_evidence, dict):
                    continue
                url = url_evidence.get("url") or url_evidence.get("hostname")
                if not isinstance(url, str) or not url.strip():
                    continue
                url_node_id = f"evidence-url:{investigation.id}:{index}"
                nodes.append({
                    "id": url_node_id,
                    "name": url,
                    "type": "URL",
                    "indicator": url,
                    "risk_score": url_evidence.get("risk_score"),
                    "details": {
                        "source_case": investigation.case_number,
                        "evidence": url_evidence.get("reasons", []),
                    },
                })
                links.append({
                    "id": f"url-evidence:{investigation.id}:{index}",
                    "source": node_id,
                    "target": url_node_id,
                    "relationship_type": "CONTAINS_RECORDED_URL",
                    "confidence": None,
                    "relationship_status": "confirmed",
                    "details": {
                        "basis": "URL was present in the saved analysis findings.",
                        "case_number": investigation.case_number,
                    },
                })

        matches = analysis_details.get("possible_investigation_matches")
        if isinstance(matches, list):
            for index, match in enumerate(matches):
                if not isinstance(match, dict):
                    continue
                matched_case = investigation_by_case.get(match.get("case_number"))
                if not matched_case or matched_case.id == investigation.id:
                    continue
                links.append({
                    "id": f"possible-match:{investigation.id}:{matched_case.id}:{index}",
                    "source": node_id,
                    "target": investigation_node_ids[matched_case.id],
                    "relationship_type": "POSSIBLE_EXACT_INDICATOR_MATCH",
                    "confidence": None,
                    "relationship_status": "possible",
                    "details": {
                        "basis": (
                            "Exact indicator match recorded by analysis; "
                            "not a confirmed relationship."
                        ),
                        "indicator": match.get("indicator"),
                    },
                })

    return {"nodes": nodes, "links": links}
