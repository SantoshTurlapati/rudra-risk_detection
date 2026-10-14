import ipaddress
import re
import unicodedata
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


def _clean_brand_text(value: Optional[str], field_name: str, max_length: int) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text.")
    value = value.strip()
    if any(unicodedata.category(character).startswith("C") for character in value):
        raise ValueError(f"{field_name} cannot contain control characters.")
    if len(value) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters.")
    return value


def _normalize_brand_domain(value: str) -> str:
    domain = _clean_brand_text(value, "Official domain", 253)
    if not domain:
        raise ValueError("Official domains cannot be blank.")
    if any(character in domain for character in "/\\:@?#"):
        raise ValueError("Official domains must be host names, not URLs or paths.")
    try:
        normalized = domain.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("Official domain is not a valid host name.") from exc
    labels = normalized.split(".")
    if (
        len(normalized) > 253
        or not labels
        or any(
            not label
            or len(label) > 63
            or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
            for label in labels
        )
    ):
        raise ValueError("Official domain is not a valid host name.")
    try:
        ipaddress.ip_address(normalized)
    except ValueError:
        return normalized
    raise ValueError("Official domains must be host names, not IP addresses.")


def _normalize_http_url(value: str, field_name: str) -> str:
    url = _clean_brand_text(value, field_name, 2048)
    if not url:
        raise ValueError(f"{field_name} cannot be blank.")
    if any(character.isspace() for character in url):
        raise ValueError(f"{field_name} must be a valid absolute HTTP(S) URL.")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid absolute HTTP(S) URL.") from exc
    if (
        parsed.scheme.casefold() not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(f"{field_name} must be a valid absolute HTTP(S) URL.")
    try:
        normalized_host = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError(f"{field_name} must contain a valid host name.") from exc
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        host_labels = normalized_host.rstrip(".").split(".")
        if any(
            not label
            or len(label) > 63
            or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
            for label in host_labels
        ):
            raise ValueError(f"{field_name} must contain a valid host name.")
        normalized_host = normalized_host.rstrip(".")
    if ":" in normalized_host:
        normalized_host = f"[{normalized_host}]"
    default_port = (parsed.scheme.casefold() == "http" and port == 80) or (
        parsed.scheme.casefold() == "https" and port == 443
    )
    netloc = normalized_host
    if port is not None and not default_port:
        netloc = f"{netloc}:{port}"
    return urlunsplit((
        parsed.scheme.casefold(),
        netloc,
        parsed.path,
        parsed.query,
        parsed.fragment,
    ))


def _normalize_string_list(values: List[str], field_name: str, max_length: int = 255) -> List[str]:
    normalized = []
    seen = set()
    for item in values:
        text = _clean_brand_text(item, field_name, max_length)
        if not text:
            raise ValueError(f"{field_name} cannot contain blank values.")
        key = text.casefold()
        if key not in seen:
            normalized.append(text)
            seen.add(key)
    return normalized


def _normalize_socials(values: List[Dict[str, str]]) -> List[Dict[str, str]]:
    normalized = []
    for item in values:
        social = {}
        for key, value in item.items():
            max_length = 50 if key == "platform" else 255 if key == "handle" else 2048
            social[key] = _clean_brand_text(
                value, f"Official social {key}", max_length
            ) or ""
        platform = social.get("platform", "")
        handle = social.get("handle", "")
        if not platform or not handle:
            raise ValueError("Each official social account requires a platform and handle.")
        social["platform"] = platform.casefold()
        if social.get("url"):
            social["url"] = _normalize_http_url(social["url"], "Official social URL")
        if social.get("profile_url"):
            social["profile_url"] = _normalize_http_url(
                social["profile_url"], "Official social profile URL"
            )
        normalized.append(social)
    return normalized


def _normalize_official_apps(values: List[Dict[str, str]]) -> List[Dict[str, str]]:
    normalized = []
    package_pattern = re.compile(r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+$")
    for item in values:
        app = {}
        for key, value in item.items():
            max_length = (
                255 if key in {"name", "package_id", "bundle_id", "developer", "publisher"}
                else 5000 if key == "description"
                else 2048
            )
            app[key] = _clean_brand_text(
                value, f"Official app {key}", max_length
            ) or ""
        if not app.get("name"):
            raise ValueError("Each official app entry requires a name.")
        package_id = app.get("package_id") or app.get("bundle_id")
        if package_id and not package_pattern.fullmatch(package_id):
            raise ValueError("Official app package identifiers must be dot-separated identifiers.")
        for key in ("store_url", "url"):
            if app.get(key):
                app[key] = _normalize_http_url(app[key], f"Official app {key}")
        normalized.append(app)
    return normalized


def _normalize_logo_url(value: Optional[str]) -> Optional[str]:
    logo_url = _clean_brand_text(value, "Logo URL", 500)
    if not logo_url:
        return logo_url
    if logo_url.casefold().startswith("local://"):
        if not re.fullmatch(
            r"local://reference-assets/[A-Za-z0-9_-]+\.(?:png|jpe?g|webp|svg)",
            logo_url,
            re.IGNORECASE,
        ):
            raise ValueError("Logo URL must be an absolute HTTP(S) URL or a safe legacy reference.")
        return logo_url
    return _normalize_http_url(logo_url, "Logo URL")

# ----------------- Auth Schemas -----------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    password: str
    full_name: str
    organization_name: Optional[str] = "Default Organization"

class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    full_name: str
    role: str
    avatar_url: Optional[str] = None
    organization_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

# ----------------- Brand Schemas -----------------
class BrandCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    official_domains: List[str] = Field(default_factory=list, max_length=100)
    official_socials: List[Dict[str, str]] = Field(default_factory=list, max_length=100)
    official_apps: List[Dict[str, str]] = Field(default_factory=list, max_length=100)
    authorized_publishers: List[str] = Field(default_factory=list, max_length=100)
    contact_identifiers: List[str] = Field(default_factory=list, max_length=100)

    @field_validator("name", "legal_name", "description")
    @classmethod
    def normalize_brand_text(cls, value: Optional[str], info):
        limits = {"name": 255, "legal_name": 255, "description": 5000}
        normalized = _clean_brand_text(value, info.field_name.replace("_", " ").title(), limits[info.field_name])
        if info.field_name == "name" and not normalized:
            raise ValueError("Brand name cannot be blank.")
        return normalized

    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_logo_url(value)

    @field_validator("official_domains")
    @classmethod
    def normalize_domains(cls, values: List[str]) -> List[str]:
        normalized = [_normalize_brand_domain(value) for value in values]
        return list(dict.fromkeys(normalized))

    @field_validator("official_socials")
    @classmethod
    def normalize_social_accounts(cls, values: List[Dict[str, str]]) -> List[Dict[str, str]]:
        return _normalize_socials(values)

    @field_validator("official_apps")
    @classmethod
    def normalize_official_applications(cls, values: List[Dict[str, str]]) -> List[Dict[str, str]]:
        return _normalize_official_apps(values)

    @field_validator("authorized_publishers")
    @classmethod
    def normalize_publishers(cls, values: List[str]) -> List[str]:
        return _normalize_string_list(values, "Authorized publisher")

    @field_validator("contact_identifiers")
    @classmethod
    def normalize_contacts(cls, values: List[str]) -> List[str]:
        return _normalize_string_list(values, "Contact identifier")

class BrandUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    official_domains: Optional[List[str]] = Field(default=None, max_length=100)
    official_socials: Optional[List[Dict[str, str]]] = Field(default=None, max_length=100)
    official_apps: Optional[List[Dict[str, str]]] = Field(default=None, max_length=100)
    authorized_publishers: Optional[List[str]] = Field(default=None, max_length=100)
    contact_identifiers: Optional[List[str]] = Field(default=None, max_length=100)
    is_verified: Optional[bool] = None

    @field_validator("name", "legal_name", "description")
    @classmethod
    def normalize_brand_text(cls, value: Optional[str], info):
        limits = {"name": 255, "legal_name": 255, "description": 5000}
        normalized = _clean_brand_text(value, info.field_name.replace("_", " ").title(), limits[info.field_name])
        if info.field_name == "name" and normalized == "":
            raise ValueError("Brand name cannot be blank.")
        return normalized

    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_logo_url(value)

    @field_validator("official_domains")
    @classmethod
    def normalize_domains(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        if values is None:
            return None
        normalized = [_normalize_brand_domain(value) for value in values]
        return list(dict.fromkeys(normalized))

    @field_validator("official_socials")
    @classmethod
    def normalize_social_accounts(cls, values: Optional[List[Dict[str, str]]]) -> Optional[List[Dict[str, str]]]:
        return None if values is None else _normalize_socials(values)

    @field_validator("official_apps")
    @classmethod
    def normalize_official_applications(cls, values: Optional[List[Dict[str, str]]]) -> Optional[List[Dict[str, str]]]:
        return None if values is None else _normalize_official_apps(values)

    @field_validator("authorized_publishers")
    @classmethod
    def normalize_publishers(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        return None if values is None else _normalize_string_list(values, "Authorized publisher")

    @field_validator("contact_identifiers")
    @classmethod
    def normalize_contacts(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        return None if values is None else _normalize_string_list(values, "Contact identifier")

class BrandResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    legal_name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    official_domains: List[str] = []
    official_socials: List[Dict[str, str]] = []
    official_apps: List[Dict[str, str]] = []
    authorized_publishers: List[str] = []
    contact_identifiers: List[str] = []
    is_verified: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ----------------- Analysis Schemas -----------------
class URLAnalysisRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    brand_id: Optional[str] = None

class ProfileAnalysisRequest(BaseModel):
    platform: str = Field(min_length=1, max_length=50)
    handle: Optional[str] = Field(default=None, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=255)
    profile_url: Optional[str] = Field(default=None, max_length=2048)
    bio_text: Optional[str] = Field(default=None, max_length=5000)
    brand_id: Optional[str] = None

    @field_validator("platform")
    @classmethod
    def reject_blank_platform(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Platform cannot be blank.")
        return value

    @field_validator("handle")
    @classmethod
    def normalize_profile_handle(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("display_name", "profile_url", "bio_text")
    @classmethod
    def normalize_optional_profile_fields(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def require_profile_evidence(self):
        if not any((self.handle, self.display_name, self.profile_url, self.bio_text)):
            raise ValueError(
                "Provide a handle, display name, profile URL, or profile text."
            )
        return self

class AppAnalysisRequest(BaseModel):
    app_name: str = Field(min_length=1, max_length=255)
    package_name: Optional[str] = Field(default=None, max_length=255)
    developer_name: Optional[str] = Field(default=None, max_length=255)
    store_url: Optional[str] = Field(default=None, max_length=2048)
    description: Optional[str] = Field(default=None, max_length=5000)
    brand_id: Optional[str] = None

    @field_validator("app_name")
    @classmethod
    def normalize_app_name(cls, value: str) -> str:
        normalized = _clean_brand_text(value, "App name", 255)
        if not normalized:
            raise ValueError("App name cannot be blank.")
        return normalized

    @field_validator("package_name", "developer_name", "description")
    @classmethod
    def normalize_app_metadata(cls, value: Optional[str], info) -> Optional[str]:
        return _clean_brand_text(
            value,
            info.field_name.replace("_", " ").title(),
            5000 if info.field_name == "description" else 255,
        )

    @field_validator("store_url")
    @classmethod
    def validate_submitted_store_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        return _normalize_http_url(value, "Submitted app-store URL")

class MessageAnalysisRequest(BaseModel):
    message_text: str = Field(min_length=1, max_length=10_000)
    sender_identifier: Optional[str] = Field(default=None, max_length=255)
    brand_id: Optional[str] = None

    @field_validator("message_text")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message text cannot be blank.")
        return value

class AnalysisResult(BaseModel):
    indicator: str
    type: str
    risk_score: Optional[int]
    risk_band: str
    status: str
    confidence: Optional[int]
    evidence_count: int
    signals: List[Dict[str, Any]]
    findings: List[str]
    missing_information: List[str]
    recommended_action: str
    details: Dict[str, Any]
    analysis_type: str = ""
    is_suspicious: bool = False
    indicators: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    explanations: Dict[str, str] = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    model_source: str = "rules"

# ----------------- Investigation Schemas -----------------
class InvestigationCreate(BaseModel):
    indicator: str = Field(min_length=1, max_length=500)
    type: str = Field(min_length=1, max_length=50) # website, social_profile, mobile_app, message, url, image
    risk_score: Optional[int] = Field(default=None, ge=0, le=100)
    confidence: Optional[int] = Field(default=None, ge=0, le=100)
    status: str = Field(default="Under Review", min_length=1, max_length=50)
    severity: str = Field(default="Medium", min_length=1, max_length=20)
    candidate_name: Optional[str] = Field(default=None, max_length=255)
    candidate_metadata: Dict[str, Any] = {}
    findings: Dict[str, Any] = {}
    brand_id: Optional[str] = None
    analyst_notes: Optional[str] = Field(default=None, max_length=10_000)

    @field_validator("indicator", "type", "status", "severity")
    @classmethod
    def reject_blank_case_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Case fields cannot be blank.")
        return value

class InvestigationUpdate(BaseModel):
    status: Optional[str] = Field(default=None, min_length=1, max_length=50)
    severity: Optional[str] = Field(default=None, min_length=1, max_length=20)
    analyst_notes: Optional[str] = Field(default=None, max_length=10_000)
    risk_score: Optional[int] = Field(default=None, ge=0, le=100)
    disposition_reason: Optional[str] = Field(default=None, max_length=2_000)

    @field_validator("status", "severity", "disposition_reason")
    @classmethod
    def normalize_optional_case_fields(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            if value == "":
                raise ValueError("Case fields cannot be blank.")
        return value

class InvestigationResponse(BaseModel):
    id: str
    case_number: str
    organization_id: str
    brand_id: Optional[str] = None
    indicator: str
    type: str
    risk_score: Optional[int]
    confidence: Optional[int]
    status: str
    severity: str
    candidate_name: Optional[str] = None
    candidate_metadata: Dict[str, Any] = {}
    findings_json: Dict[str, Any] = {}
    analyst_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ----------------- Alert Schemas -----------------
class AlertUpdate(BaseModel):
    status: str # Unread, Acknowledged, Resolved

class AlertResponse(BaseModel):
    id: str
    title: str
    description: str
    indicator: Optional[str] = None
    severity: str
    status: str
    source: str
    case_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ----------------- Campaign Schemas -----------------
class CampaignResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    related_entities_count: int
    risk_level: str
    status: str
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True

# ----------------- Copilot Schemas -----------------
class CopilotMessageRequest(BaseModel):
    message: str
    language: str = "en" # "en" or "te" (English or Telugu)
    context: Optional[Dict[str, Any]] = None

class CopilotResponse(BaseModel):
    reply: str
    language: str
    safety_tips: List[str]
    suggested_actions: List[str]
    risk_assessment: Optional[str] = None
