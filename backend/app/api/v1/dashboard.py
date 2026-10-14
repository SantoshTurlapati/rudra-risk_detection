from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user, require_organization_id
from app.core.config import settings
from app.db.models import Alert, Campaign, Investigation, Organization, User

router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics"])

DEMO_ORGANIZATION_SLUG = "rudrashield-intel"
ACTIVE_ALERT_STATUSES = {"Unread", "Acknowledged"}
SUSPICIOUS_STATUSES = {"Malicious", "Suspicious", "Phishing"}

_INVESTIGATION_TYPES = {
    "social_profile": "Social Profile",
    "website": "Website",
    "url": "URL",
    "mobile_app": "Mobile App",
    "message": "Message",
    "image": "Image",
}


def _normalized_type(value: str | None) -> str:
    if not value:
        return "Other"
    normalized = value.strip().casefold().replace(" ", "_").replace("-", "_")
    return _INVESTIGATION_TYPES.get(normalized, value.strip())


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _relative_time(value: datetime | None) -> str:
    timestamp = _as_utc(value)
    if timestamp is None:
        return "Time unavailable"

    total_seconds = int((datetime.now(timezone.utc) - timestamp).total_seconds())
    if total_seconds < 60:
        return "just now"
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


def _trend(current: int, previous: int) -> str:
    if previous == 0:
        return "New" if current else "—"
    change = round((current - previous) * 100 / previous)
    return f"{change:+d}%"


def _daily_counts(
    records: List[Any],
    predicate,
    last_day: date,
) -> List[int]:
    counts = []
    for days_back in range(6, -1, -1):
        target_day = last_day - timedelta(days=days_back)
        counts.append(
            sum(
                1
                for record in records
                if predicate(record)
                and _as_utc(record.created_at) is not None
                and _as_utc(record.created_at).date() == target_day
            )
        )
    return counts


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    organization_id = require_organization_id(current_user)
    is_demo_organization = db.query(Organization.id).filter(
        Organization.id == organization_id,
        Organization.slug == DEMO_ORGANIZATION_SLUG
    ).first() is not None

    def non_demo_records(model):
        query = db.query(model).filter(
            model.organization_id == organization_id,
            or_(model.is_demo.is_(False), model.is_demo.is_(None))
        )
        if is_demo_organization:
            query = query.filter(False)
        return query

    investigations = (
        non_demo_records(Investigation)
        .order_by(Investigation.created_at.desc())
        .all()
    )
    alerts = non_demo_records(Alert).order_by(Alert.created_at.desc()).all()
    campaigns = (
        non_demo_records(Campaign)
        .filter(Campaign.related_entities_count > 0)
        .order_by(Campaign.last_seen.desc())
        .all()
    )

    active_alerts = [alert for alert in alerts if alert.status in ACTIVE_ALERT_STATUSES]
    unresolved_profiles = [
        item for item in investigations
        if _normalized_type(item.type) == "Social Profile"
        and item.status not in {"Safe", "Resolved"}
    ]
    suspicious_apps = [
        item for item in investigations
        if _normalized_type(item.type) == "Mobile App"
        and item.status not in {"Safe", "Resolved"}
    ]
    malicious_or_phishing_cases = [
        item for item in investigations
        if _normalized_type(item.type) in {
            "Website", "Social Profile", "Mobile App", "Message"
        }
        and item.status in {"Malicious", "Phishing"}
    ]
    url_analyses = sum(
        1 for item in investigations if _normalized_type(item.type) == "URL"
    )
    message_analyses = sum(
        1 for item in investigations if _normalized_type(item.type) == "Message"
    )

    grouped_alerts = defaultdict(int)
    for alert in alerts:
        grouped_alerts[alert.severity or "Low"] += 1

    type_color_map = {
        "Social Profile": ("Social Profile Analyses", "#087CF0"),
        "Website": ("Website Analyses", "#06C8F9"),
        "Mobile App": ("Mobile App Analyses", "#8B5CF6"),
        "Message": ("Message Analyses", "#12B981"),
        "URL": ("URL Analyses", "#F59E0B"),
    }
    threat_distribution: Dict[str, Dict[str, Any]] = {}
    for investigation in investigations:
        key = _normalized_type(investigation.type)
        label, color = type_color_map.get(key, ("Other Analyses", "#F59E0B"))
        entry = threat_distribution.setdefault(key, {"count": 0, "label": label, "color": color})
        entry["count"] += 1

    total_investigations = len(investigations)
    distribution = [
        {
            "name": entry["label"],
            "percentage": round(entry["count"] * 100 / total_investigations) if total_investigations else 0,
            "count": entry["count"],
            "color": entry["color"],
        }
        for entry in threat_distribution.values()
    ]
    distribution.sort(key=lambda item: item["count"], reverse=True)

    now = datetime.now(timezone.utc)
    today = now.date()
    current_start = today - timedelta(days=6)
    previous_start = today - timedelta(days=13)

    def count_period(records, predicate, start: date, end: date) -> int:
        return sum(
            1
            for record in records
            if predicate(record)
            and _as_utc(record.created_at) is not None
            and start <= _as_utc(record.created_at).date() <= end
        )

    metric_specs = {
        "total_investigations": (investigations, lambda _: True),
        "active_alerts": (alerts, lambda item: item.status in ACTIVE_ALERT_STATUSES),
        "suspicious_apps": (investigations, lambda item: _normalized_type(item.type) == "Mobile App" and item.status not in {"Safe", "Resolved"}),
        "unresolved_profiles": (investigations, lambda item: _normalized_type(item.type) == "Social Profile" and item.status not in {"Safe", "Resolved"}),
    }
    metrics = {}
    metric_values = {
        "total_investigations": total_investigations,
        "active_alerts": len(active_alerts),
        "suspicious_apps": len(suspicious_apps),
        "unresolved_profiles": len(unresolved_profiles),
    }
    for name, (records, predicate) in metric_specs.items():
        daily = _daily_counts(records, predicate, today)
        current_count = sum(daily)
        previous_count = count_period(records, predicate, previous_start, current_start - timedelta(days=1))
        metrics[name] = {
            "value": metric_values[name],
            "trend": _trend(current_count, previous_count),
            "trend_label": "vs. previous 7 days",
            "sparkline": daily,
        }

    activities = []
    for investigation in investigations[:5]:
        timestamp = investigation.updated_at or investigation.created_at
        activities.append({
            "action": f"Investigation updated: {investigation.indicator}",
            "timestamp": timestamp,
            "icon": "investigation",
        })
    for alert in alerts[:3]:
        activities.append({
            "action": f"Alert: {alert.title}",
            "timestamp": alert.created_at,
            "icon": "alert",
        })
    activities.sort(key=lambda item: _as_utc(item["timestamp"]) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    recent_activity = [
        {
            "action": item["action"],
            "time": _relative_time(item["timestamp"]),
            "icon": item["icon"],
        }
        for item in activities[:5]
    ]

    investigations_over_time = [
        {"date": today - timedelta(days=days_back), "count": count}
        for days_back, count in zip(range(6, -1, -1), metrics["total_investigations"]["sparkline"])
    ]
    investigations_over_time = [
        {"date": item["date"].isoformat(), "count": item["count"]}
        for item in investigations_over_time
    ]

    return {
        "metrics": metrics,
        "recent_investigations": [
            {
                "id": item.id,
                "case_number": item.case_number,
                "type": _normalized_type(item.type),
                "indicator": item.indicator,
                "risk_score": item.risk_score,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in investigations[:5]
        ],
        "recent_campaigns": [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "related_entities_count": item.related_entities_count,
                "risk_level": item.risk_level,
            }
            for item in campaigns[:5]
        ],
        "recent_alerts": [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "severity": item.severity,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in active_alerts[:5]
        ],
        "india_heatmap": {
            "top_affected_states": [],
            "severity_legend": [
                {"label": "Very High", "color": "#EF4444"},
                {"label": "High", "color": "#F59E0B"},
                {"label": "Medium", "color": "#FBBF24"},
                {"label": "Low", "color": "#06C8F9"},
            ],
        },
        "threat_categories": {
            "total": total_investigations,
            "distribution": distribution,
        },
        "recent_activity": recent_activity,
        "alerts_by_severity": {
            "Critical": grouped_alerts.get("Critical", 0),
            "High": grouped_alerts.get("High", 0),
            "Medium": grouped_alerts.get("Medium", 0),
            "Low": grouped_alerts.get("Low", 0),
        },
        "investigations_over_time": investigations_over_time,
        "summary": {
            "cases_marked_malicious_or_phishing": len(malicious_or_phishing_cases),
            "unresolved_profile_cases": len(unresolved_profiles),
            "suspicious_application_candidates": len(suspicious_apps),
            "url_analyses": url_analyses,
            "message_analyses": message_analyses,
            "campaigns_supported_by_evidence": len(campaigns),
        },
        "system_status": {
            "status": "ready",
            "uptime": None,
            "active_nodes": None,
            "version": settings.VERSION,
            "last_updated": now.isoformat(),
        },
    }
