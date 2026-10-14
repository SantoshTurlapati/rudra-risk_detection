import argparse
import json
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.models import (
    Alert,
    BrandProfile,
    Campaign,
    Investigation,
    Organization,
    ThreatEntity,
    ThreatRelationship,
    User,
)
from app.db.session import SessionLocal


DEMO_EMAIL = "analyst@rudrashield.ai"
DEMO_USERNAME = "yasmine_analyst"


def seed_database(
    db: Session,
    *,
    allow_demo: bool = False,
    demo_password: str | None = None
):
    """Populate synthetic development fixtures only when explicitly enabled."""
    if not allow_demo:
        return
    if not demo_password or len(demo_password) < 16:
        raise ValueError(
            "Explicit demo seeding requires RUDRASHIELD_DEMO_PASSWORD "
            "with at least 16 characters."
        )

    existing_user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if existing_user:
        return

    org = Organization(
        name="RudraShield Cyber Intelligence Center",
        slug="rudrashield-intel",
        description="Development-only synthetic monitoring workspace. Replace with real organization data in production.",
    )
    db.add(org)
    db.flush()

    analyst_user = User(
        organization_id=org.id,
        email=DEMO_EMAIL,
        username=DEMO_USERNAME,
        hashed_password=get_password_hash(demo_password),
        full_name="Demo Analyst",
        role="analyst",
    )
    db.add(analyst_user)
    db.flush()

    sbi_brand = BrandProfile(
        organization_id=org.id,
        name="State Bank of India (SBI)",
        legal_name="State Bank of India",
        description="Sample development fixture for testing the monitoring UI.",
        official_domains=json.dumps(["sbi.co.in", "onlinesbi.sbi", "retail.onlinesbi.sbi"]),
        official_socials=json.dumps([
            {"platform": "X", "handle": "@TheOfficialSBI", "url": "https://x.com/TheOfficialSBI"},
            {"platform": "Facebook", "handle": "StateBankofIndia", "url": "https://facebook.com/StateBankofIndia"},
        ]),
        official_apps=json.dumps([
            {"name": "YONO SBI: The Mobile Banking", "package_id": "com.sbi.lotusintouch", "developer": "State Bank of India"},
            {"name": "BHIM SBI Pay", "package_id": "com.sbi.upi", "developer": "State Bank of India"},
        ]),
        authorized_publishers=json.dumps(["State Bank of India", "SBI Cards and Payment Services"]),
        contact_identifiers=json.dumps(["18001234", "customercare@sbi.co.in"]),
        is_verified=False,
    )
    db.add(sbi_brand)

    npci_brand = BrandProfile(
        organization_id=org.id,
        name="National Payments Corporation of India (NPCI / UPI)",
        legal_name="National Payments Corporation of India",
        description="Sample application-brand data for development testing only.",
        official_domains=json.dumps(["npci.org.in", "bhimupi.org.in"]),
        official_socials=json.dumps([
            {"platform": "X", "handle": "@NPCI_NPCI", "url": "https://x.com/NPCI_NPCI"}
        ]),
        official_apps=json.dumps([
            {"name": "BHIM - Making India Cashless", "package_id": "in.org.npci.upiapp", "developer": "NPCI"}
        ]),
        authorized_publishers=json.dumps(["National Payments Corporation of India"]),
        contact_identifiers=json.dumps(["contact@npci.org.in"]),
        is_verified=False,
    )
    db.add(npci_brand)
    db.flush()

    now = datetime.now(timezone.utc)

    investigations_data = [
        {
            "case_number": "RS-1021",
            "type": "Website",
            "indicator": "example-payments.com",
            "risk_score": 92,
            "status": "Malicious",
            "severity": "Critical",
            "brand_id": sbi_brand.id,
            "created_at": now - timedelta(hours=1),
            "findings": {
                "summary": "Synthetic demo threat for UI validation.",
                "reasons": ["Example only", "Replace with live evidence in production"],
            },
        },
        {
            "case_number": "RS-1022",
            "type": "Social Profile",
            "indicator": "@sbi_care_official",
            "risk_score": 87,
            "status": "Suspicious",
            "severity": "High",
            "brand_id": sbi_brand.id,
            "created_at": now - timedelta(hours=2),
            "findings": {"summary": "Synthetic impersonation fixture for local testing.", "reasons": ["Example only"]},
        },
    ]

    for inv in investigations_data:
        db.add(
            Investigation(
                case_number=inv["case_number"],
                organization_id=org.id,
                brand_id=inv["brand_id"],
                created_by_id=analyst_user.id,
                indicator=inv["indicator"],
                type=inv["type"],
                risk_score=inv["risk_score"],
                confidence=88,
                status=inv["status"],
                severity=inv["severity"],
                is_demo=True,
                findings_json=json.dumps(inv["findings"]),
                created_at=inv["created_at"],
                updated_at=inv["created_at"],
            )
        )

    db.add(
        Campaign(
            organization_id=org.id,
            name="Synthetic Brand Protection Campaign",
            description="Development-only campaign fixture. Do not rely on it in production.",
            category="Demo",
            related_entities_count=3,
            risk_level="Medium",
            status="Monitoring",
            is_demo=True,
            first_seen=now - timedelta(days=7),
            last_seen=now - timedelta(hours=2),
        )
    )

    db.add(
        Alert(
            organization_id=org.id,
            title="Synthetic monitoring alert",
            description="This is a development-only record and should be replaced with real alerts.",
            indicator="example-alert.local",
            severity="Medium",
            status="Unread",
            source="Demo Seed",
            is_demo=True,
            created_at=now - timedelta(hours=1),
        )
    )

    db.commit()


def clear_demo_records(db: Session):
    """Delete explicitly marked fixtures, preserving the demo workspace and user data."""
    org_ids = [
        row[0]
        for row in db.query(Organization.id)
        .join(User, User.organization_id == Organization.id)
        .filter(
            Organization.slug == "rudrashield-intel",
            User.email == DEMO_EMAIL,
        )
        .all()
    ]
    if not org_ids:
        return 0

    removed = 0
    for model in (Alert, Investigation, Campaign):
        removed += db.query(model).filter(
            model.organization_id.in_(org_ids),
            model.is_demo.is_(True),
        ).delete(synchronize_session=False)
    db.commit()
    return removed


def _run_cli():
    parser = argparse.ArgumentParser(description="RudraShield development data utilities")
    parser.add_argument("--seed-demo", action="store_true", help="Create a synthetic development-only dataset")
    parser.add_argument("--clear-demo", action="store_true", help="Remove only demo fixtures created by this seeder")
    parser.add_argument("--confirm-clear-demo", action="store_true", help="Required before deleting demo records")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.seed_demo:
            seed_database(
                db,
                allow_demo=True,
                demo_password=os.environ.get("RUDRASHIELD_DEMO_PASSWORD")
            )
            print("Demo seed created successfully.")
        elif args.clear_demo:
            if not args.confirm_clear_demo:
                print("Refusing to delete demo records without --confirm-clear-demo.")
                return
            removed = clear_demo_records(db)
            print(f"Removed {removed} demo records.")
        else:
            print("No action selected. Use --seed-demo or --clear-demo.")
    finally:
        db.close()


if __name__ == "__main__":
    _run_cli()
