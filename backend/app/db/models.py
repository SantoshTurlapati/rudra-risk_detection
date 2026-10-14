import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    brands = relationship("BrandProfile", back_populates="organization", cascade="all, delete-orphan")
    investigations = relationship("Investigation", back_populates="organization", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="organization", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="organization", cascade="all, delete-orphan")
    threat_entities = relationship("ThreatEntity", back_populates="organization", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="analyst")  # admin, analyst, investigator, viewer
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization", back_populates="users")
    investigations = relationship("Investigation", back_populates="creator")

class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    official_domains = Column(Text, default="[]")  # JSON string list
    official_socials = Column(Text, default="[]")  # JSON string list of {platform, handle, url}
    official_apps = Column(Text, default="[]")     # JSON string list of {name, package_id, store_url}
    authorized_publishers = Column(Text, default="[]") # JSON list
    contact_identifiers = Column(Text, default="[]")   # JSON list of phone/emails
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization", back_populates="brands")
    investigations = relationship("Investigation", back_populates="brand")

class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_number = Column(String(50), unique=True, nullable=False) # e.g. RS-1023
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    brand_id = Column(String(36), ForeignKey("brand_profiles.id"), nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    indicator = Column(String(500), nullable=False) # e.g. example-payments.com, @sbi_care_official
    type = Column(String(50), nullable=False)       # website, social_profile, mobile_app, message, url, image
    risk_score = Column(Integer, nullable=True)     # 0-100, absent when not assessed
    confidence = Column(Integer, nullable=True)     # optional model confidence; null for rule-only analysis
    status = Column(String(50), default="Under Review") # Malicious, Suspicious, Phishing, Low Risk, Safe, Under Review, Resolved
    severity = Column(String(20), default="Medium") # Critical, High, Medium, Low

    candidate_name = Column(String(255), nullable=True)
    candidate_metadata = Column(Text, default="{}") # JSON dict
    findings_json = Column(Text, default="{}")      # JSON dict with evidence, signals, recommendations
    analyst_notes = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization", back_populates="investigations")
    brand = relationship("BrandProfile", back_populates="investigations")
    creator = relationship("User", back_populates="investigations")
    alerts = relationship("Alert", back_populates="case")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    case_id = Column(String(36), ForeignKey("investigations.id"), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    indicator = Column(String(500), nullable=True)
    severity = Column(String(20), default="High")   # Critical, High, Medium, Low
    status = Column(String(50), default="Unread")   # Unread, Acknowledged, Resolved
    source = Column(String(100), default="Detection Engine")
    is_demo = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="alerts")
    case = relationship("Investigation", back_populates="alerts")

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)

    name = Column(String(255), nullable=False)      # e.g. SBI KYC Scam
    description = Column(Text, nullable=False)      # e.g. Fake KYC update messages
    category = Column(String(100), default="Phishing")
    related_entities_count = Column(Integer, default=0)
    risk_level = Column(String(20), default="High") # High, Medium, Low
    status = Column(String(50), default="Active")   # Active, Mitigated, Monitoring
    is_demo = Column(Boolean, default=False)

    first_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization", back_populates="campaigns")

class ThreatEntity(Base):
    __tablename__ = "threat_entities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)

    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)       # Brand, Social Profile, Domain, URL, App, Publisher, Contact, Campaign, Case
    indicator = Column(String(500), nullable=True)
    risk_score = Column(Integer, nullable=True)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization", back_populates="threat_entities")

class ThreatRelationship(Base):
    __tablename__ = "threat_relationships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("threat_entities.id"), nullable=False)
    target_id = Column(String(36), ForeignKey("threat_entities.id"), nullable=False)

    relationship_type = Column(String(100), nullable=False) # IMPERSONATES, HOSTED_ON, TARGETS, PART_OF, SENDS_MESSAGE
    confidence = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), nullable=True)
    user_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=True)
    details_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
