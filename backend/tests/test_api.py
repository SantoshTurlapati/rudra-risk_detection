import csv
import io
import json
import uuid

import pytest
from PIL import Image
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.models import (
    Alert, AuditLog, BrandProfile, Campaign, Investigation, Organization, ThreatEntity,
    ThreatRelationship, User
)
from app.db.seed import clear_demo_records, seed_database
from app.db.session import Base, SessionLocal
from app.main import app, engine
from app.api.v1.reports import _sanitize_csv_cell

client = TestClient(app)


def authenticated_user(organization_name="Test Organization"):
    suffix = uuid.uuid4().hex[:10]
    email = f"analyst-{suffix}@example.com"
    password = "SecurePass123!"
    register_response = client.post("/api/v1/auth/register", json={
        "email": email,
        "username": f"analyst_{suffix}",
        "password": password,
        "full_name": "Test Analyst",
        "organization_name": organization_name,
    })
    assert register_response.status_code == 200
    login_response = client.post("/api/v1/auth/login", json={
        "username_or_email": email,
        "password": password,
    })
    assert login_response.status_code == 200
    data = login_response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["service"] == "RudraShield AI"
    assert data["database"] == "ready"

def test_health_check_reports_database_failure(monkeypatch):
    def fail_connect():
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(engine, "connect", fail_connect)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["database"] == "unavailable"

@pytest.mark.parametrize("secret", ["", "replace_with_a_secure_random_secret_key_in_production"])
def test_settings_reject_missing_or_placeholder_secret(secret):
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY=secret)


def test_auth_registration_and_login():
    email = f"new-user-{uuid.uuid4().hex[:8]}@example.com"
    username = f"new_user_{uuid.uuid4().hex[:8]}"

    register_response = client.post("/api/v1/auth/register", json={
        "email": email,
        "username": username,
        "password": "SecurePass123!",
        "full_name": "Test Analyst",
        "organization_name": "Test Organization",
    })
    assert register_response.status_code == 200

    login_response = client.post("/api/v1/auth/login", json={
        "username_or_email": email,
        "password": "SecurePass123!",
    })
    assert login_response.status_code == 200
    data = login_response.json()
    assert "access_token" in data
    assert data["user"]["email"] == email
    assert data["user"]["username"] == username


def test_protected_endpoints_require_bearer_authentication():
    for path in (
        "/api/v1/dashboard/stats",
        "/api/v1/brands",
        "/api/v1/investigations",
        "/api/v1/alerts",
        "/api/v1/campaigns",
        "/api/v1/reports",
        "/api/v1/settings",
        "/api/v1/threat-graph",
    ):
        assert client.get(path).status_code == 401
    assert client.post("/api/v1/analysis/url", json={"url": "https://example.com"}).status_code == 401


def test_settings_report_external_discovery_as_unavailable():
    headers, _ = authenticated_user()
    response = client.get("/api/v1/settings", headers=headers)
    assert response.status_code == 200
    integrations = response.json()["integrations"]
    assert {item["provider"] for item in integrations} == {
        "Social profile discovery",
        "App-store listing discovery",
    }
    assert all(item["connected"] is False for item in integrations)
    assert all("Unavailable" in item["status"] for item in integrations)


def test_dashboard_stats():
    headers, _ = authenticated_user()
    response = client.get("/api/v1/dashboard/stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert data["metrics"]["total_investigations"]["value"] >= 0
    assert data["metrics"]["active_alerts"]["value"] >= 0
    assert isinstance(data["threat_categories"]["distribution"], list)
    assert data["metrics"]["total_investigations"]["value"] == 0
    assert data["metrics"]["active_alerts"]["value"] == 0
    assert data["metrics"]["total_investigations"]["trend"] == "—"
    assert data["recent_investigations"] == []
    assert data["recent_campaigns"] == []
    assert data["recent_alerts"] == []


def test_graph_dashboard_history_and_reports_use_recorded_evidence():
    headers, user = authenticated_user()
    suffix = uuid.uuid4().hex[:10]

    with SessionLocal() as db:
        brand = BrandProfile(
            organization_id=user["organization_id"],
            name=f"Evidence Brand {suffix}",
            is_verified=True,
        )
        db.add(brand)
        db.flush()

        profile = Investigation(
            case_number=f"RS-{uuid.uuid4().hex[:12].upper()}",
            organization_id=user["organization_id"],
            brand_id=brand.id,
            indicator=f"@candidate_{suffix}",
            type="social_profile",
            risk_score=63,
            confidence=None,
            status="Suspicious",
            severity="High",
            findings_json=json.dumps({
                "findings": ["Saved profile indicator evidence."],
                "details": {
                    "urls": [{
                        "url": f"https://candidate-{suffix}.example/login",
                        "risk_score": 72,
                        "reasons": ["A recorded URL rule matched."],
                    }],
                    "possible_investigation_matches": [],
                },
            }),
        )
        message = Investigation(
            case_number=f"RS-{uuid.uuid4().hex[:12].upper()}",
            organization_id=user["organization_id"],
            indicator=f"Recorded message {suffix}",
            type="message",
            risk_score=54,
            confidence=None,
            status="Under Review",
            severity="Medium",
            findings_json=json.dumps({
                "findings": ["Saved message pattern evidence."],
                "details": {"possible_investigation_matches": [{
                    "case_number": profile.case_number,
                    "indicator": profile.indicator,
                    "relationship": "Possible exact indicator match; not a confirmed relationship.",
                }]},
            }),
        )
        app_case = Investigation(
            case_number=f"RS-{uuid.uuid4().hex[:12].upper()}",
            organization_id=user["organization_id"],
            indicator=f"com.example.app{suffix}",
            type="mobile_app",
            risk_score=77,
            confidence=None,
            status="Under Review",
            severity="High",
            findings_json="{}",
        )
        website = Investigation(
            case_number=f"RS-{uuid.uuid4().hex[:12].upper()}",
            organization_id=user["organization_id"],
            indicator=f"site-{suffix}.example",
            type="website",
            risk_score=84,
            confidence=None,
            status="Malicious",
            severity="Critical",
            findings_json="{}",
        )
        url_case = Investigation(
            case_number=f"RS-{uuid.uuid4().hex[:12].upper()}",
            organization_id=user["organization_id"],
            indicator=f"https://url-{suffix}.example",
            type="url",
            risk_score=70,
            confidence=None,
            status="Suspicious",
            severity="High",
            analyst_notes="Report download test",
            findings_json=json.dumps({"findings": ["Stored URL finding."]}),
        )
        db.add_all([profile, message, app_case, website, url_case])
        db.flush()

        source = ThreatEntity(
            organization_id=user["organization_id"],
            name="Stored source entity",
            type="Domain",
        )
        target = ThreatEntity(
            organization_id=user["organization_id"],
            name="Stored target entity",
            type="Campaign",
        )
        db.add_all([source, target])
        db.flush()
        stored_edge = ThreatRelationship(
            source_id=source.id,
            target_id=target.id,
            relationship_type="PART_OF",
            confidence=90,
        )
        db.add(stored_edge)
        db.add(Alert(
            organization_id=user["organization_id"],
            title="Recorded active alert",
            description="Test evidence-backed dashboard alert",
            severity="High",
            status="Unread",
        ))
        db.commit()
        profile_id = profile.id
        profile_case = profile.case_number
        message_id = message.id
        message_case = message.case_number
        url_case_id = url_case.id
        url_case_number = url_case.case_number
        source_id = source.id
        target_id = target.id

    graph_response = client.get("/api/v1/threat-graph", headers=headers)
    assert graph_response.status_code == 200
    graph = graph_response.json()
    graph_nodes = {node["id"]: node for node in graph["nodes"]}
    graph_links = graph["links"]
    assert graph_nodes[f"investigation:{profile_id}"]["type"] == "Social Profile"
    assert graph_nodes[f"investigation:{profile_id}"]["details"]["evidence"] == [
        "Saved profile indicator evidence."
    ]
    assert any(
        link["relationship_type"] == "CASE_ASSOCIATED_WITH_BRAND"
        and link["relationship_status"] == "confirmed"
        for link in graph_links
    )
    assert any(node["type"] == "URL" and node["indicator"].endswith("/login") for node in graph["nodes"])
    assert any(
        link["relationship_type"] == "POSSIBLE_EXACT_INDICATOR_MATCH"
        and link["relationship_status"] == "possible"
        and link["source"] == f"investigation:{message_id}"
        and link["target"] == f"investigation:{profile_id}"
        for link in graph_links
    )
    assert any(
        link["relationship_type"] == "PART_OF"
        and link["relationship_status"] == "confirmed"
        and link["source"] == source_id
        and link["target"] == target_id
        for link in graph_links
    )

    dashboard_response = client.get("/api/v1/dashboard/stats", headers=headers)
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["metrics"]["total_investigations"]["value"] == 5
    assert dashboard["metrics"]["suspicious_apps"]["value"] == 1
    assert dashboard["metrics"]["unresolved_profiles"]["value"] == 1
    assert dashboard["summary"]["cases_marked_malicious_or_phishing"] == 1
    assert dashboard["summary"]["unresolved_profile_cases"] == 1
    assert dashboard["summary"]["url_analyses"] == 1
    assert dashboard["summary"]["message_analyses"] == 1
    assert {item["name"] for item in dashboard["threat_categories"]["distribution"]} == {
        "Social Profile Analyses", "Message Analyses", "Mobile App Analyses",
        "Website Analyses", "URL Analyses",
    }

    history_response = client.get("/api/v1/investigations", headers=headers)
    assert history_response.status_code == 200
    assert len(history_response.json()) == 5
    detail_response = client.get(
        f"/api/v1/investigations/{profile_case}", headers=headers
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["case_number"] == profile_case

    reports_response = client.get("/api/v1/reports", headers=headers)
    assert reports_response.status_code == 200
    reports = reports_response.json()
    assert len(reports) == 5
    report = next(item for item in reports if item["case_number"] == url_case_number)
    assert report["findings"]["findings"] == ["Stored URL finding."]
    download_response = client.get(
        f"/api/v1/reports/{url_case_id}/download-csv", headers=headers
    )
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("text/csv")
    assert "attachment;" in download_response.headers["content-disposition"]
    csv_rows = list(csv.reader(download_response.text.splitlines()))
    assert ["Case Number", url_case_number] in csv_rows
    assert ["Stored Confidence (Provenance Unknown)", "Not assessed"] in csv_rows
    provenance_row = next(row for row in csv_rows if row[0] == "Record Provenance")
    assert json.loads(provenance_row[1]) == {}
    assert ["Findings JSON", json.dumps({"findings": ["Stored URL finding."]})] in csv_rows
    assert profile_case != message_case


def test_report_csv_sanitizes_formula_like_values():
    headers, user = authenticated_user()
    with SessionLocal() as db:
        investigation = Investigation(
            case_number=f"RS-{uuid.uuid4().hex[:12].upper()}",
            organization_id=user["organization_id"],
            indicator="\t=cmd /c calc",
            type="web",
            risk_score=82,
            confidence=None,
            status="High Risk",
            severity="High",
            analyst_notes="  +SUM(1,2)",
            findings_json=json.dumps({"findings": ["\n@cmd /c calc", "normal-data"]}),
        )
        db.add(investigation)
        db.commit()
        db.refresh(investigation)
        investigation_id = investigation.id

    response = client.get(f"/api/v1/reports/{investigation_id}/download-csv", headers=headers)
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text)))
    assert ["Indicator", "'=cmd /c calc"] in rows
    assert ["Analyst Notes", "'+SUM(1,2)"] in rows
    assert any(row[0] == "Findings JSON" and row[1].startswith("{") for row in rows)
    assert ["Status", "High Risk"] in rows


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=1+1", "'=1+1"),
        ("+SUM(1,2)", "'+SUM(1,2)"),
        ("-1+2", "'-1+2"),
        ("@SUM(A1:A2)", "'@SUM(A1:A2)"),
        (" \t\r\n=1+1", "'=1+1"),
        ("\t+1+1", "'+1+1"),
        ("\r@SUM(A1:A2)", "'@SUM(A1:A2)"),
        ("\x0b=1+1", "'=1+1"),
        ("\x00 @SUM(A1:A2)", "'@SUM(A1:A2)"),
        ("normal text", "normal text"),
        ("https://example.com/path", "https://example.com/path"),
        ("", ""),
        (None, ""),
    ],
)
def test_csv_cell_sanitizer_handles_formula_prefixes_and_normal_values(value, expected):
    assert _sanitize_csv_cell(value) == expected


def test_dashboard_excludes_explicit_demo_seed():
    with SessionLocal() as db:
        seed_database(
            db,
            allow_demo=True,
            demo_password="test-only-demo-password-0123456789",
        )
        assert db.query(Investigation).filter(Investigation.is_demo.is_(True)).count() == 2

    headers, _ = authenticated_user()
    response = client.get("/api/v1/dashboard/stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["total_investigations"]["value"] == 0
    assert data["recent_investigations"] == []
    assert data["recent_campaigns"] == []
    assert data["recent_alerts"] == []


def test_demo_cleanup_only_removes_marked_records_in_isolated_database():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(bind=test_engine)
    try:
        with TestSession() as db:
            organization = Organization(
                name="Fixture workspace",
                slug="rudrashield-intel",
            )
            db.add(organization)
            db.flush()
            user = User(
                organization_id=organization.id,
                email="analyst@rudrashield.ai",
                username="yasmine_analyst",
                hashed_password="not-a-real-password-hash",
                full_name="Fixture analyst",
            )
            brand = BrandProfile(
                organization_id=organization.id,
                name="Fixture brand",
                official_domains='["example.test"]',
            )
            demo_case = Investigation(
                case_number="RS-DEMO-CLEANUP",
                organization_id=organization.id,
                indicator="demo.example",
                type="website",
                is_demo=True,
            )
            real_case = Investigation(
                case_number="RS-REAL-PRESERVE",
                organization_id=organization.id,
                indicator="real.example",
                type="website",
                is_demo=False,
            )
            demo_alert = Alert(
                organization_id=organization.id,
                title="Demo alert",
                description="Fixture",
                is_demo=True,
            )
            demo_campaign = Campaign(
                organization_id=organization.id,
                name="Demo campaign",
                description="Fixture",
                is_demo=True,
            )
            db.add_all([user, brand, demo_case, real_case, demo_alert, demo_campaign])
            db.commit()
            organization_id = organization.id
            brand_id = brand.id

            assert clear_demo_records(db) == 3
            assert db.query(Organization).filter_by(id=organization_id).count() == 1
            assert db.query(User).filter_by(email="analyst@rudrashield.ai").count() == 1
            assert db.query(BrandProfile).filter_by(id=brand_id).count() == 1
            assert db.query(Investigation).filter_by(case_number="RS-DEMO-CLEANUP").count() == 0
            assert db.query(Investigation).filter_by(case_number="RS-REAL-PRESERVE").count() == 1
            assert db.query(Alert).filter_by(title="Demo alert").count() == 0
            assert db.query(Campaign).filter_by(name="Demo campaign").count() == 0
    finally:
        test_engine.dispose()

def test_url_analysis_endpoint():
    headers, _ = authenticated_user()
    response = client.post("/api/v1/analysis/url", json={
        "url": "https://sbi-verify-kyc-update.xyz/login"
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] > 0
    assert data["details"]["url_metrics"]["risk_score"] >= 70
    assert len(data["findings"]) > 0


@pytest.mark.parametrize(
    "url",
    [
        "https://user:password@example.com/login",
        "https://example.com/\tlogin",
    ],
)
def test_url_analysis_rejects_credentials_and_control_characters(url):
    headers, _ = authenticated_user()
    response = client.post(
        "/api/v1/analysis/url",
        json={"url": url},
        headers=headers,
    )
    assert response.status_code == 422


def test_profile_analysis_response_uses_profile_fields():
    headers, _ = authenticated_user()
    response = client.post("/api/v1/analysis/profile", json={
        "platform": "X (Twitter)",
        "handle": "@example_account",
        "display_name": "Example Account",
        "bio_text": "",
    }, headers=headers)
    assert response.status_code == 200
    details = response.json()["details"]
    assert "name_analysis" in details
    assert "url_metrics" not in details


def test_profile_analysis_supports_pasted_bio_and_inspects_its_url():
    headers, user = authenticated_user()
    with SessionLocal() as db:
        brand = BrandProfile(
            organization_id=user["organization_id"],
            name="State Bank of India",
            official_domains=json.dumps(["onlinesbi.sbi"]),
            is_verified=True,
        )
        db.add(brand)
        db.commit()
        db.refresh(brand)
        brand_id = brand.id

    response = client.post("/api/v1/analysis/profile", headers=headers, json={
        "platform": "X",
        "bio_text": (
            "Official SBI support. Send your OTP now: "
            "https://sbi-login-check.xyz/verify"
        ),
        "brand_id": brand_id,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_type"] == "profile"
    assert data["details"]["urls"][0]["risk_score"] >= 50
    assert data["risk_score"] >= 50
    assert data["confidence"] is None
    assert data["model_source"] == "rules"
    assert any("Account age" in item for item in data["missing_information"])
    assert data["explanations"]["plain_language"]
    assert data["details"]["account_metadata"]["followers"] == "Not provided"
    assert data["details"]["possible_investigation_matches"] == []


def test_app_analysis_compares_only_registered_package_and_marks_store_unavailable():
    headers, user = authenticated_user()
    with SessionLocal() as db:
        brand = BrandProfile(
            organization_id=user["organization_id"],
            name="Example Bank",
            official_apps=json.dumps([{
                "name": "Example Bank App",
                "package_id": "org.example.bank",
                "developer": "Example Bank",
            }]),
            authorized_publishers=json.dumps(["Example Bank"]),
            is_verified=True,
        )
        db.add(brand)
        db.commit()
        db.refresh(brand)
        brand_id = brand.id

    exact = client.post("/api/v1/analysis/app", headers=headers, json={
        "app_name": "Example Bank App",
        "package_name": "org.example.bank",
        "developer_name": "Example Bank",
        "brand_id": brand_id,
    })
    assert exact.status_code == 200
    assert exact.json()["details"]["registry_package_match"] is True
    assert exact.json()["confidence"] is None
    assert any("No live app-store listing" in item for item in exact.json()["missing_information"])

    different = client.post("/api/v1/analysis/app", headers=headers, json={
        "app_name": "Example Bank",
        "package_name": "org.example.unknown",
        "developer_name": "Unknown Publisher",
        "brand_id": brand_id,
    })
    assert different.status_code == 200
    assert different.json()["details"]["registry_package_match"] is False
    assert different.json()["details"]["publisher_mismatch"] is True


def test_app_analysis_handles_missing_registered_package_id():
    headers, user = authenticated_user()
    with SessionLocal() as db:
        brand = BrandProfile(
            organization_id=user["organization_id"],
            name="Example Bank",
            official_apps=json.dumps([{
                "name": "Example Bank App",
                "package_id": None,
            }]),
            is_verified=True,
        )
        db.add(brand)
        db.commit()
        db.refresh(brand)
        brand_id = brand.id

    response = client.post("/api/v1/analysis/app", headers=headers, json={
        "app_name": "Example Bank App",
        "package_name": "org.example.bank",
        "brand_id": brand_id,
    })

    assert response.status_code == 200
    assert response.json()["details"]["registry_package_match"] is False
    assert any(
        "No live app-store listing" in item
        for item in response.json()["missing_information"]
    )


def test_app_analysis_inspects_only_the_submitted_store_url_locally():
    headers, _ = authenticated_user()
    response = client.post("/api/v1/analysis/app", headers=headers, json={
        "app_name": "  Candidate App  ",
        "store_url": " HTTPS://Store.Example:443/apps/candidate ",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["indicator"] == "Candidate App"
    assert data["details"]["submitted_store_url_analysis"]["hostname"] == "store.example"
    assert data["model_source"] == "rules"
    assert data["confidence"] is None
    assert any(
        "No live app-store listing" in item
        for item in data["missing_information"]
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"app_name": "   "},
        {"app_name": "Candidate\u0000App"},
        {"app_name": "Candidate App", "store_url": "javascript:alert(1)"},
        {"app_name": "Candidate App", "store_url": "https://user:secret@store.example/app"},
    ],
)
def test_app_analysis_rejects_blank_or_unsafe_submitted_metadata(payload):
    headers, _ = authenticated_user()
    response = client.post("/api/v1/analysis/app", headers=headers, json=payload)
    assert response.status_code == 422


def test_app_analysis_rejects_a_brand_from_another_organization():
    headers, _ = authenticated_user("App analysis organization")
    _, other_user = authenticated_user("Other app analysis organization")
    with SessionLocal() as db:
        brand = BrandProfile(
            organization_id=other_user["organization_id"],
            name="Other Organization App Brand",
            is_verified=True,
        )
        db.add(brand)
        db.commit()
        db.refresh(brand)
        brand_id = brand.id

    response = client.post("/api/v1/analysis/app", headers=headers, json={
        "app_name": "Candidate App",
        "brand_id": brand_id,
    })
    assert response.status_code == 404


def test_verified_official_profile_handle_is_not_flagged_as_impersonation():
    headers, user = authenticated_user()
    with SessionLocal() as db:
        brand = BrandProfile(
            organization_id=user["organization_id"],
            name="State Bank of India",
            official_domains=json.dumps(["onlinesbi.sbi"]),
            official_socials=json.dumps([
                {"platform": "X", "handle": "@TheOfficialSBI"}
            ]),
            is_verified=True,
        )
        db.add(brand)
        db.commit()
        db.refresh(brand)
        brand_id = brand.id

    response = client.post("/api/v1/analysis/profile", headers=headers, json={
        "platform": "X",
        "handle": "@TheOfficialSBI",
        "brand_id": brand_id,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["details"]["registry_handle_match"] is True
    assert data["risk_score"] == 0
    assert data["is_suspicious"] is False


def test_message_analysis_inspects_links_without_fetching_them():
    headers, user = authenticated_user()
    with SessionLocal() as db:
        brand = BrandProfile(
            organization_id=user["organization_id"],
            name="Example Bank",
            official_domains=json.dumps(["examplebank.com"]),
            is_verified=True,
        )
        db.add(brand)
        db.commit()
        db.refresh(brand)
        brand_id = brand.id
        db.add(Investigation(
            case_number=f"RS-{uuid.uuid4().hex[:12].upper()}",
            organization_id=user["organization_id"],
            indicator="examplebank-login.xyz",
            type="Website",
            risk_score=70,
            confidence=None,
            status="Under Review",
            severity="High",
        ))
        db.commit()

    response = client.post("/api/v1/analysis/message", headers=headers, json={
        "message_text": (
            "Your account will be blocked within 24 hours. Enter your OTP now "
            "and click this link: https://examplebank-login.xyz/verify"
        ),
        "brand_id": brand_id,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_type"] == "message"
    assert data["model_source"] == "rules"
    assert data["confidence"] is None
    assert data["details"]["urls"][0]["risk_score"] >= 70
    possible_matches = data["details"]["possible_investigation_matches"]
    assert len(possible_matches) == 1
    assert "Possible exact indicator match" in possible_matches[0]["relationship"]
    assert len(data["details"]["scam_dna"]["evidence"]) >= 3
    assert data["risk_score"] >= 75
    assert data["status"] == "Suspicious"
    assert any("proof of fraud" in item for item in data["limitations"])


def test_analysis_inputs_reject_blank_and_oversized_text():
    headers, _ = authenticated_user()
    blank = client.post("/api/v1/analysis/message", headers=headers, json={
        "message_text": "   "
    })
    oversized = client.post("/api/v1/analysis/message", headers=headers, json={
        "message_text": "x" * 10_001
    })
    empty_profile = client.post("/api/v1/analysis/profile", headers=headers, json={
        "platform": "X",
    })
    assert blank.status_code == 422
    assert oversized.status_code == 422
    assert empty_profile.status_code == 422


def test_verified_registry_match_does_not_override_url_risk():
    headers, user = authenticated_user()
    with SessionLocal() as db:
        brand = BrandProfile(
            organization_id=user["organization_id"],
            name="Example Bank",
            official_domains='["example.com"]',
            is_verified=True,
        )
        db.add(brand)
        db.commit()
        db.refresh(brand)
        brand_id = brand.id

    response = client.post("/api/v1/analysis/url", headers=headers, json={
        "url": "https://example.com/login",
        "brand_id": brand_id,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["details"]["official_domain_match"] is True
    assert data["risk_score"] > 0
    assert any(signal["source"] == "Configured Brand Registry" for signal in data["signals"])


def test_brand_creation_is_unverified_and_analyst_cannot_verify():
    headers, _ = authenticated_user()
    response = client.post("/api/v1/brands", headers=headers, json={
        "name": "Test Bank",
        "official_domains": ["test.example"],
    })
    assert response.status_code == 200
    brand = response.json()
    assert brand["is_verified"] is False
    update = client.patch(
        f"/api/v1/brands/{brand['id']}",
        headers=headers,
        json={"is_verified": True},
    )
    assert update.status_code == 403


def test_brand_owner_can_delete_organization_scoped_brand():
    headers, _ = authenticated_user()
    created = client.post(
        "/api/v1/brands",
        headers=headers,
        json={"name": "Delete Workflow Example"},
    )
    assert created.status_code == 200
    brand_id = created.json()["id"]
    assert client.get(f"/api/v1/brands/{brand_id}", headers=headers).status_code == 200

    deleted = client.delete(f"/api/v1/brands/{brand_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["message"] == "Brand deleted successfully"
    assert client.get(f"/api/v1/brands/{brand_id}", headers=headers).status_code == 404


def test_brand_identifiers_are_normalized_and_unknown_metadata_is_preserved():
    headers, _ = authenticated_user()
    response = client.post("/api/v1/brands", headers=headers, json={
        "name": "  Example Bank  ",
        "official_domains": [" BANK.EXAMPLE. ", "bank.example"],
        "official_socials": [{
            "platform": " X ",
            "handle": " @ExampleBank ",
            "url": "HTTPS://X.Example:443/examplebank",
            "platform_user_id": "known-source-id",
        }],
        "official_apps": [{
            "name": " Example Bank App ",
            "package_id": " com.example.bank ",
            "store_url": "https://store.example/apps/bank",
            "developer": " Example Bank Ltd ",
        }],
        "authorized_publishers": [" Example Bank Ltd ", "example bank ltd"],
        "contact_identifiers": [" help@bank.example "],
    })

    assert response.status_code == 200
    brand = response.json()
    assert brand["name"] == "Example Bank"
    assert brand["official_domains"] == ["bank.example"]
    assert brand["official_socials"] == [{
        "platform": "x",
        "handle": "@ExampleBank",
        "url": "https://x.example/examplebank",
        "platform_user_id": "known-source-id",
    }]
    assert brand["official_apps"][0] == {
        "name": "Example Bank App",
        "package_id": "com.example.bank",
        "store_url": "https://store.example/apps/bank",
        "developer": "Example Bank Ltd",
    }
    assert brand["authorized_publishers"] == ["Example Bank Ltd"]
    assert brand["contact_identifiers"] == ["help@bank.example"]
    assert brand["is_verified"] is False


@pytest.mark.parametrize(
    "payload",
    [
        {"name": " \t "},
        {"name": "Example\u0000Bank"},
        {"name": "Example Bank", "official_domains": ["https://bank.example/login"]},
        {"name": "Example Bank", "official_domains": ["127.0.0.1"]},
        {"name": "Example Bank", "official_domains": ["-invalid.example"]},
        {"name": "Example Bank", "logo_url": "javascript:alert(1)"},
        {"name": "Example Bank", "logo_url": "file:///private/logo.png"},
        {"name": "Example Bank", "official_socials": [{"platform": "X"}]},
        {
            "name": "Example Bank",
            "official_socials": [{
                "platform": "X",
                "handle": "@example",
                "url": "javascript:alert(1)",
            }],
        },
        {"name": "Example Bank", "official_apps": [{"name": "Bank", "package_id": "bad id"}]},
        {
            "name": "Example Bank",
            "official_apps": [{
                "name": "Bank",
                "store_url": "https://user:password@store.example/app",
            }],
        },
        {"name": "Example Bank", "authorized_publishers": ["  "]},
    ],
)
def test_brand_creation_rejects_invalid_identity_data(payload):
    headers, _ = authenticated_user()
    response = client.post("/api/v1/brands", headers=headers, json=payload)
    assert response.status_code == 422


def test_invalid_brand_patch_does_not_modify_existing_metadata():
    headers, _ = authenticated_user()
    created = client.post("/api/v1/brands", headers=headers, json={
        "name": "Preserved Bank",
        "official_domains": ["bank.example"],
    })
    assert created.status_code == 200
    brand_id = created.json()["id"]

    rejected = client.patch(
        f"/api/v1/brands/{brand_id}",
        headers=headers,
        json={"official_domains": ["https://attacker.example/path"]},
    )
    assert rejected.status_code == 422
    unchanged = client.get(f"/api/v1/brands/{brand_id}", headers=headers)
    assert unchanged.status_code == 200
    assert unchanged.json()["official_domains"] == ["bank.example"]
    assert unchanged.json()["is_verified"] is False


def test_brand_verification_changes_are_audited_and_profile_edits_preserve_status():
    headers, user = authenticated_user()
    created = client.post(
        "/api/v1/brands",
        headers=headers,
        json={"name": "Audit Example", "official_domains": ["audit.example"]},
    )
    assert created.status_code == 200
    brand_id = created.json()["id"]

    with SessionLocal() as db:
        db.query(User).filter(User.id == user["id"]).update(
            {User.role: "admin"}
        )
        db.commit()

    verified = client.patch(
        f"/api/v1/brands/{brand_id}",
        headers=headers,
        json={"is_verified": True},
    )
    assert verified.status_code == 200
    assert verified.json()["is_verified"] is True

    profile_edit = client.patch(
        f"/api/v1/brands/{brand_id}",
        headers=headers,
        json={"description": "Updated without changing verification."},
    )
    assert profile_edit.status_code == 200
    assert profile_edit.json()["is_verified"] is True
    settings_response = client.get("/api/v1/settings", headers=headers)
    assert settings_response.status_code == 200
    audit_entry = next(
        item for item in settings_response.json()["audit_logs"]
        if item["action"] == "brand_verification_status_updated"
    )
    assert audit_entry["details"] == {
        "previous_status": False,
        "new_status": True,
    }

    with SessionLocal() as db:
        audit = db.query(AuditLog).filter(
            AuditLog.organization_id == user["organization_id"],
            AuditLog.user_id == user["id"],
            AuditLog.resource_id == brand_id,
            AuditLog.action == "brand_verification_status_updated",
        ).one()
        assert json.loads(audit.details_json) == {
            "previous_status": False,
            "new_status": True,
            "note": (
                "Admin-marked registry status; independent ownership "
                "verification is not implied."
            ),
        }


def test_analyst_can_revoke_but_not_grant_admin_marked_brand_status():
    headers, user = authenticated_user()
    created = client.post(
        "/api/v1/brands",
        headers=headers,
        json={"name": "Revocation Example"},
    )
    brand_id = created.json()["id"]
    with SessionLocal() as db:
        db.query(User).filter(User.id == user["id"]).update(
            {User.role: "admin"}
        )
        db.commit()
    assert client.patch(
        f"/api/v1/brands/{brand_id}",
        headers=headers,
        json={"is_verified": True},
    ).status_code == 200
    with SessionLocal() as db:
        db.query(User).filter(User.id == user["id"]).update(
            {User.role: "analyst"}
        )
        db.commit()

    revoked = client.patch(
        f"/api/v1/brands/{brand_id}",
        headers=headers,
        json={"is_verified": False},
    )
    assert revoked.status_code == 200
    assert revoked.json()["is_verified"] is False
    with SessionLocal() as db:
        audit_entries = db.query(AuditLog).filter(
            AuditLog.resource_id == brand_id,
            AuditLog.action == "brand_verification_status_updated",
        ).order_by(AuditLog.created_at.asc()).all()
        assert len(audit_entries) == 2
        assert json.loads(audit_entries[-1].details_json)["new_status"] is False


def test_brand_partial_update_preserves_existing_metadata():
    headers, _ = authenticated_user()
    created = client.post("/api/v1/brands", headers=headers, json={
        "name": "Metadata Bank",
        "logo_url": "local://reference-assets/logo.png",
        "official_domains": ["bank.example"],
        "official_socials": [{
            "platform": "X",
            "handle": "@metadata",
            "url": "https://x.example/metadata",
        }],
        "official_apps": [{
            "name": "Bank App",
            "package_id": "com.example.bank",
            "store_url": "https://store.example/app",
            "developer": "Example Bank",
        }],
        "authorized_publishers": ["Example Bank Ltd"],
        "contact_identifiers": ["help@bank.example"],
    })
    assert created.status_code == 200
    brand_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/brands/{brand_id}",
        headers=headers,
        json={"description": "Updated description"},
    )
    assert updated.status_code == 200
    brand = updated.json()
    assert brand["description"] == "Updated description"
    assert brand["logo_url"] == "local://reference-assets/logo.png"
    assert brand["official_domains"] == ["bank.example"]
    assert brand["official_socials"][0]["url"] == "https://x.example/metadata"
    assert brand["official_apps"][0]["package_id"] == "com.example.bank"
    assert brand["official_apps"][0]["store_url"] == "https://store.example/app"
    assert brand["official_apps"][0]["developer"] == "Example Bank"
    assert brand["authorized_publishers"] == ["Example Bank Ltd"]
    assert brand["contact_identifiers"] == ["help@bank.example"]
    assert brand["is_verified"] is False


@pytest.mark.parametrize(
    "payload",
    [
        {"indicator": "", "type": "website"},
        {"indicator": "candidate.example", "type": " "},
        {"indicator": "candidate.example", "type": "website", "risk_score": -1},
        {"indicator": "candidate.example", "type": "website", "risk_score": 101},
        {"indicator": "candidate.example", "type": "website", "confidence": 101},
    ],
)
def test_investigation_creation_rejects_invalid_case_fields(payload):
    headers, _ = authenticated_user()
    response = client.post("/api/v1/investigations", headers=headers, json=payload)
    assert response.status_code == 422


def test_investigation_update_rejects_invalid_risk_and_blank_status():
    headers, _ = authenticated_user()
    created = client.post("/api/v1/investigations", headers=headers, json={
        "indicator": "candidate.example",
        "type": "website",
    })
    assert created.status_code == 200
    case_id = created.json()["id"]
    assert client.patch(
        f"/api/v1/investigations/{case_id}",
        headers=headers,
        json={"risk_score": 101},
    ).status_code == 422
    assert client.patch(
        f"/api/v1/investigations/{case_id}",
        headers=headers,
        json={"status": "   "},
    ).status_code == 422


def test_false_positive_disposition_is_persisted_and_audited():
    headers, user = authenticated_user()
    created = client.post("/api/v1/investigations", headers=headers, json={
        "indicator": "candidate.example",
        "type": "social_profile",
        "findings": {
            "evidence": ["Manual profile analysis found a name match."],
            "_review_history": [{"status": "Fabricated client-supplied history"}],
        },
    })
    assert created.status_code == 200
    case_id = created.json()["id"]
    assert created.json()["findings_json"]["_record_provenance"] == {
        "submission_method": "authenticated_api_submission",
        "recorded_by_user_id": user["id"],
        "recorded_at": created.json()["findings_json"]["_record_provenance"]["recorded_at"],
        "source_attribution": (
            "Submitted evidence; external source verification was not performed by case creation."
        ),
    }
    assert created.json()["findings_json"]["_review_history"] == []
    missing_reason = client.patch(
        f"/api/v1/investigations/{case_id}",
        headers=headers,
        json={"status": "False Positive"},
    )
    assert missing_reason.status_code == 422
    blank_reason = client.patch(
        f"/api/v1/investigations/{case_id}",
        headers=headers,
        json={
            "status": "False Positive",
            "disposition_reason": "   ",
        },
    )
    assert blank_reason.status_code == 422
    updated = client.patch(
        f"/api/v1/investigations/{case_id}",
        headers=headers,
        json={
            "status": "False Positive",
            "analyst_notes": "Reviewed as a false positive.",
            "disposition_reason": "Independent review found the registered account matched.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "False Positive"
    assert updated.json()["findings_json"]["evidence"] == [
        "Manual profile analysis found a name match."
    ]
    history = updated.json()["findings_json"]["_review_history"]
    assert history[-1]["disposition_reason"] == (
        "Independent review found the registered account matched."
    )
    assert history[-1]["changes"]["status"] == {
        "previous": "Under Review",
        "new": "False Positive",
    }
    with SessionLocal() as db:
        log = db.query(AuditLog).filter(
            AuditLog.organization_id == user["organization_id"],
            AuditLog.user_id == user["id"],
            AuditLog.resource_id == case_id,
            AuditLog.action == "investigation_disposition_updated",
        ).one()
        assert json.loads(log.details_json) == {
            "status": {
                "previous": "Under Review",
                "new": "False Positive",
            },
            "analyst_notes": {"changed": True},
            "disposition_reason": (
                "Independent review found the registered account matched."
            ),
        }
    report_response = client.get(
        f"/api/v1/reports/{case_id}/download-csv",
        headers=headers,
    )
    report_rows = list(csv.reader(report_response.text.splitlines()))
    provenance_row = next(row for row in report_rows if row[0] == "Record Provenance")
    assert json.loads(provenance_row[1])["submission_method"] == (
        "authenticated_api_submission"
    )
    history_row = next(row for row in report_rows if row[0] == "Review History")
    assert json.loads(history_row[1])[-1]["disposition_reason"] == (
        "Independent review found the registered account matched."
    )


def test_case_updates_append_history_without_logging_note_content():
    headers, user = authenticated_user()
    created = client.post("/api/v1/investigations", headers=headers, json={
        "indicator": "history.example",
        "type": "website",
        "findings": {"evidence": ["Original evidence is retained."]},
    })
    case_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/investigations/{case_id}",
        headers=headers,
        json={
            "status": "Under Review",
            "risk_score": 28,
            "severity": "Low",
            "analyst_notes": "Sensitive note text must not enter audit metadata.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["findings_json"]["evidence"] == [
        "Original evidence is retained."
    ]
    event = updated.json()["findings_json"]["_review_history"][-1]
    assert event["changes"]["risk_score"] == {"previous": None, "new": 28}
    assert event["changes"]["severity"] == {"previous": "Medium", "new": "Low"}
    assert event["changes"]["analyst_notes"] == {"changed": True}
    assert "Sensitive note text" not in json.dumps(event)
    with SessionLocal() as db:
        log = db.query(AuditLog).filter(
            AuditLog.organization_id == user["organization_id"],
            AuditLog.user_id == user["id"],
            AuditLog.resource_id == case_id,
            AuditLog.action == "investigation_updated",
        ).one()
        assert "Sensitive note text" not in log.details_json


def test_campaign_cluster_suggestions_require_multiple_exact_evidence_types_and_are_tenant_scoped():
    headers, user = authenticated_user("Cluster organization")
    _, other_user = authenticated_user("Other cluster organization")
    common_findings = {
        "details": {
            "urls": [{"url": "https://shared.example/login", "risk_score": 75}],
            "scam_dna": {
                "evidence": [{"excerpt": "Your account is blocked, verify access immediately today."}]
            },
        }
    }
    only_one_signal = {
        "details": {"urls": [{"url": "https://shared.example/another-path"}]}
    }
    with SessionLocal() as db:
        cases = [
            Investigation(
                case_number=f"RS-{uuid.uuid4().hex[:12].upper()}",
                organization_id=user["organization_id"],
                indicator=f"candidate-{index}.example",
                type="message",
                status="Under Review",
                severity="Medium",
                findings_json=json.dumps(common_findings),
            )
            for index in range(2)
        ]
        single_signal = Investigation(
            case_number=f"RS-{uuid.uuid4().hex[:12].upper()}",
            organization_id=user["organization_id"],
            indicator="single-signal.example",
            type="website",
            status="Under Review",
            severity="Medium",
            findings_json=json.dumps(only_one_signal),
        )
        other_case = Investigation(
            case_number=f"RS-{uuid.uuid4().hex[:12].upper()}",
            organization_id=other_user["organization_id"],
            indicator="other-org.example",
            type="message",
            status="Under Review",
            severity="Medium",
            findings_json=json.dumps(common_findings),
        )
        db.add_all([*cases, single_signal, other_case])
        db.commit()
        expected_cases = {case.case_number for case in cases}
        other_case_number = other_case.case_number

    response = client.get("/api/v1/campaigns/cluster-suggestions", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert "no external discovery" in result["mode"]
    assert len(result["suggestions"]) == 1
    suggestion = result["suggestions"][0]
    assert {case["case_number"] for case in suggestion["cases"]} == expected_cases
    assert {item["evidence_type"] for item in suggestion["shared_evidence"]} == {
        "url_domain",
        "message_excerpt_sha256",
    }
    assert suggestion["status"] == "possible_cluster"
    assert suggestion["confidence"] is None
    assert any(
        "does not establish common ownership" in limitation
        for limitation in suggestion["limitations"]
    )
    assert other_case_number not in json.dumps(result)


def test_image_without_reference_is_unverified_not_low_risk():
    headers, _ = authenticated_user()
    image_bytes = io.BytesIO()
    Image.new("RGB", (8, 8), (1, 2, 3)).save(image_bytes, format="PNG")
    image_bytes.seek(0)
    response = client.post(
        "/api/v1/analysis/image",
        headers=headers,
        files={"file": ("candidate.png", image_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Unverified"
    assert data["risk_band"] == "Unverified"
    assert data["risk_score"] is None
    assert data["confidence"] is None
    assert data["details"]["comparison"]["comparison_available"] is False


def test_image_upload_rejects_unsupported_decoded_format():
    headers, _ = authenticated_user()
    image_bytes = io.BytesIO()
    Image.new("RGB", (8, 8), (1, 2, 3)).save(image_bytes, format="BMP")
    response = client.post(
        "/api/v1/analysis/image",
        headers=headers,
        files={"file": ("candidate.bmp", image_bytes.getvalue(), "image/bmp")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported image format. Use PNG, JPEG, or WebP."


def test_image_upload_limit_is_enforced_before_full_read():
    headers, _ = authenticated_user()
    response = client.post(
        "/api/v1/analysis/image",
        headers=headers,
        files={"file": ("oversized.png", b"x" * (10 * 1024 * 1024 + 1), "image/png")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Image file exceeds 10MB limit."


def test_cross_organization_records_are_not_visible_or_mutable():
    headers, user = authenticated_user("Organization A")
    _, other_user = authenticated_user("Organization B")
    with SessionLocal() as db:
        brand = BrandProfile(
            organization_id=other_user["organization_id"],
            name="Other Organization Brand",
            official_domains="[]",
            is_verified=False,
        )
        db.add(brand)
        db.flush()
        investigation = Investigation(
            case_number=f"RS-{uuid.uuid4().hex[:12].upper()}",
            organization_id=other_user["organization_id"],
            brand_id=brand.id,
            indicator="other.example",
            type="Website",
            risk_score=65,
            confidence=None,
            status="Under Review",
            severity="Medium",
        )
        alert = Alert(
            organization_id=other_user["organization_id"],
            title="Other alert",
            description="Tenant isolation fixture",
            severity="High",
            status="Unread",
        )
        campaign = Campaign(
            organization_id=other_user["organization_id"],
            name="Other campaign",
            description="Tenant isolation fixture",
        )
        entity = ThreatEntity(
            organization_id=other_user["organization_id"],
            name="Other entity",
            type="Domain",
        )
        db.add_all([investigation, alert, campaign, entity])
        db.commit()
        brand_id = brand.id
        investigation_id = investigation.id
        alert_id = alert.id
        campaign_id = campaign.id

    assert user["organization_id"] != other_user["organization_id"]
    assert client.get("/api/v1/brands", headers=headers).json() == []
    assert client.get(f"/api/v1/brands/{brand_id}", headers=headers).status_code == 404
    assert client.get("/api/v1/investigations", headers=headers).json() == []
    assert client.get(f"/api/v1/investigations/{investigation_id}", headers=headers).status_code == 404
    assert client.patch(
        f"/api/v1/investigations/{investigation_id}",
        headers=headers,
        json={"status": "Resolved"},
    ).status_code == 404
    assert client.get("/api/v1/alerts", headers=headers).json() == []
    assert client.get(f"/api/v1/alerts/{alert_id}", headers=headers).status_code == 404
    assert client.patch(
        f"/api/v1/alerts/{alert_id}",
        headers=headers,
        json={"status": "Resolved"},
    ).status_code == 404
    with SessionLocal() as db:
        assert db.query(Alert).filter(Alert.id == alert_id).one().status == "Unread"
    assert client.get("/api/v1/campaigns", headers=headers).json() == []
    assert client.get(f"/api/v1/campaigns/{campaign_id}", headers=headers).status_code == 404
    assert client.get("/api/v1/reports", headers=headers).json() == []
    assert client.get(f"/api/v1/reports/{investigation_id}/download-csv", headers=headers).status_code == 404
    assert client.get("/api/v1/threat-graph", headers=headers).json() == {"nodes": [], "links": []}
    assert client.get(
        "/api/v1/dashboard/stats", headers=headers
    ).json()["metrics"]["total_investigations"]["value"] == 0


def test_cross_organization_user_cannot_apply_false_positive_disposition():
    owner_headers, _ = authenticated_user("Case owner organization")
    other_headers, _ = authenticated_user("Other case organization")
    created = client.post(
        "/api/v1/investigations",
        headers=owner_headers,
        json={
            "indicator": "tenant-case.example",
            "type": "website",
            "findings": {"evidence": ["Preserve owner evidence."]},
        },
    )
    assert created.status_code == 200
    case_id = created.json()["id"]

    denied = client.patch(
        f"/api/v1/investigations/{case_id}",
        headers=other_headers,
        json={
            "status": "False Positive",
            "disposition_reason": "Not authorized to modify this case.",
        },
    )
    assert denied.status_code == 404

    unchanged = client.get(
        f"/api/v1/investigations/{case_id}",
        headers=owner_headers,
    )
    assert unchanged.status_code == 200
    assert unchanged.json()["status"] == "Under Review"
    assert unchanged.json()["findings_json"]["evidence"] == ["Preserve owner evidence."]
    assert unchanged.json()["findings_json"]["_review_history"] == []


def test_password_recovery_fails_closed_until_delivery_is_configured():
    headers, user = authenticated_user()
    forgot = client.post("/api/v1/auth/forgot-password", json={"email": user["email"]})
    assert forgot.status_code == 503
    assert "reset_token" not in forgot.json()
    reset = client.post("/api/v1/auth/reset-password", json={
        "token": "arbitrary-token",
        "new_password": "ChangedPassword123!",
    })
    assert reset.status_code == 503
    login = client.post("/api/v1/auth/login", json={
        "username_or_email": user["email"],
        "password": "SecurePass123!",
    })
    assert login.status_code == 200


def test_disabled_user_token_is_rejected():
    headers, user = authenticated_user()
    with SessionLocal() as db:
        db.query(User).filter(User.id == user["id"]).update(
            {User.is_active: False}
        )
        db.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_copilot_bilingual():
    res_en = client.post("/api/v1/copilot/chat", json={
        "message": "Why is this KYC link asking for my OTP?",
        "language": "en",
    })
    assert res_en.status_code == 200
    assert "KYC impersonation scams" in res_en.json()["reply"]
    assert res_en.json()["risk_assessment"] is None
    assert "not an analysis of your message" in res_en.json()["reply"]

    res_te = client.post("/api/v1/copilot/chat", json={
        "message": "నా ఖాతా కేవైసీ లింక్ సురక్షితమేనా?",
        "language": "te",
    })
    assert res_te.status_code == 200
    assert "1930" in res_te.json()["reply"]
    assert res_te.json()["risk_assessment"] is None
