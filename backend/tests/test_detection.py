import pytest
import io
from PIL import Image, ImageDraw
from app.ai.homoglyphs import detect_and_normalize_homoglyphs
from app.ai.name_matcher import analyze_name_impersonation
from app.ai.url_safety import analyze_url_safety, extract_urls, is_private_ip
from app.ai.scam_patterns import analyze_scam_dna
from app.ai.risk_engine import compute_overall_risk
from app.ai.image_hasher import compare_images

def test_homoglyph_detection():
    # Cyrillic 'а' (U+0430) instead of Latin 'a'
    deceptive_sbi = "sb\u0430" # looks like 'sba'
    norm, anomalies, has_deception = detect_and_normalize_homoglyphs(deceptive_sbi)
    assert has_deception is True
    assert norm == "sba"
    assert len(anomalies) > 0

def test_name_similarity_typosquatting():
    res = analyze_name_impersonation("sbi_care_official", "State Bank of India")
    assert res["is_suspicious"] is True
    assert len(res["matched_keywords"]) > 0
    assert "care" in res["matched_keywords"] or "official" in res["matched_keywords"]

def test_url_ssrf_detection():
    # Private loopback IP check
    assert is_private_ip("127.0.0.1") is True
    assert is_private_ip("localhost") is True
    assert is_private_ip("192.168.1.100") is True
    assert is_private_ip("10.0.0.1") is True
    assert is_private_ip("example.com") is False

    res = analyze_url_safety("http://127.0.0.1:8000/internal")
    assert res["is_ssrf_risk"] is True
    assert res["risk_score"] >= 80

def test_url_brand_subdomain_spoof():
    res = analyze_url_safety("https://sbi.login-verify-account.xyz", official_brand_domain="onlinesbi.sbi")
    assert res["is_suspicious"] is True
    assert res["risk_score"] >= 50
    assert any("subdomain" in r.lower() for r in res["reasons"])

def test_scam_dna_urgency_and_otp():
    text = "Dear customer, your SBI account is blocked! Update KYC immediately within 24 hours. Enter your OTP at bit.ly/test"
    dna = analyze_scam_dna(text)
    assert dna["risk_score"] >= 60
    assert "Urgency & Coercion" in dna["categories"]
    assert "Credential & Secret Harvesting" in dna["categories"]

def test_overall_risk_engine():
    name_mock = {"similarity_score": 85.0, "is_suspicious": True, "reasons": ["Typosquatting"], "matched_keywords": ["official"], "homoglyph_detected": False}
    url_mock = {"risk_score": 75, "is_ssrf_risk": False, "reasons": ["Suspicious TLD"]}
    scam_mock = {"risk_score": 80, "patterns_matched": [{"category": "Urgency"}], "reasons": ["Urgency detected"]}

    risk = compute_overall_risk(name_analysis=name_mock, url_analysis=url_mock, scam_dna_analysis=scam_mock)
    assert risk["risk_score"] >= 40
    assert risk["risk_band"] in ["Needs Review", "High Risk", "Critical Risk"]
    assert len(risk["signals"]) >= 2


def test_url_analyzer_flags_shorteners_and_idn_without_fetching():
    shortener = analyze_url_safety("https://bit.ly/example")
    assert shortener["is_suspicious"] is True
    assert any("shortening service" in item for item in shortener["reasons"])

    idn = analyze_url_safety("https://раypal.example")
    assert idn["hostname"].startswith("xn--")
    assert any("Punycode" in item for item in idn["reasons"])


def test_url_extraction_is_deduplicated_and_bounded():
    text = "https://example.com/a, https://example.com/a and bit.ly/test"
    assert extract_urls(text) == ["https://example.com/a", "bit.ly/test"]
    assert extract_urls(text, limit=0) == []


@pytest.mark.parametrize(
    "url",
    [
        "https://user:password@example.com/login",
        "https://user@example.com/login",
        "https://example.com/\tlogin",
        "https://example.com/login\r\n",
    ],
)
def test_url_analyzer_rejects_credentials_and_control_characters(url):
    with pytest.raises(ValueError):
        analyze_url_safety(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.1/admin",
        "http://0177.0.0.1/admin",
        "http://0x7f000001/admin",
    ],
)
def test_url_analyzer_flags_ambiguous_numeric_ip_forms_without_fetching(url):
    result = analyze_url_safety(url)
    assert result["has_ambiguous_ip_literal"] is True
    assert result["is_suspicious"] is True
    assert any("ambiguous numeric address" in reason for reason in result["reasons"])


def test_url_analyzer_accepts_normal_domain_without_fetching():
    result = analyze_url_safety("https://example.com/path")
    assert result["hostname"] == "example.com"
    assert result["has_ambiguous_ip_literal"] is False
    assert result["is_ssrf_risk"] is False


def test_scam_dna_returns_evidence_and_does_not_call_text_safe():
    result = analyze_scam_dna(
        "Urgent: your account will be blocked. Enter your OTP immediately."
    )
    assert result["risk_score"] == 60
    assert result["model_source"] == "rules"
    assert len(result["categories"]) == 2
    assert len(result["evidence"]) >= 2
    assert "not proof" in result["limitations"][0]


def test_scam_dna_does_not_double_count_repeated_matches_or_score_embedded_url():
    repeated = analyze_scam_dna(
        "Urgent urgent urgent: account blocked; verify at https://example.com/otp"
    )
    assert len(repeated["patterns_matched"]) == 1
    assert repeated["risk_score"] == 25
    assert repeated["urls"] == ["https://example.com/otp"]


def test_scam_dna_rejects_non_text_and_oversized_input():
    with pytest.raises(ValueError, match="must be a string"):
        analyze_scam_dna(None)
    with pytest.raises(ValueError, match="cannot exceed"):
        analyze_scam_dna("a" * 10_001)


def test_risk_engine_uses_available_scores_and_never_fabricates_confidence():
    risk = compute_overall_risk(
        url_analysis={
            "risk_score": 90,
            "is_suspicious": True,
            "reasons": ["Suspicious URL structure."],
        }
    )
    assert risk["risk_score"] == 90
    assert risk["risk_band"] == "Critical Risk"
    assert risk["confidence"] is None
    assert risk["model_source"] == "rules"
    assert "manual review" in risk["recommended_action"]


def test_risk_engine_validates_optional_model_output():
    model_result = compute_overall_risk(model_analysis={
        "risk_score": 80,
        "confidence": 75,
        "source": "local-test-model",
        "reasons": ["Model indicator."],
    })
    assert model_result["confidence"] == 75
    assert model_result["model_source"] == "rules+local-test-model"
    assert 0 <= model_result["risk_score"] <= 100

    with pytest.raises(ValueError, match="between 0 and 100"):
        compute_overall_risk(model_analysis={"risk_score": 101})


def _image_bytes(image, image_format="PNG", **save_options):
    buffer = io.BytesIO()
    image.save(buffer, format=image_format, **save_options)
    return buffer.getvalue()


def test_image_comparison_handles_matching_resized_compressed_and_unrelated_images():
    reference = Image.new("RGB", (128, 96), "white")
    draw = ImageDraw.Draw(reference)
    draw.rectangle((12, 12, 44, 72), fill="black")
    draw.ellipse((72, 30, 112, 70), fill="black")

    resized = reference.resize((256, 192), Image.Resampling.LANCZOS)
    compressed = _image_bytes(resized, "JPEG", quality=80)
    unrelated = Image.new("RGB", (128, 96), "white")
    ImageDraw.Draw(unrelated).rectangle((80, 8, 120, 86), fill="black")

    reference_bytes = _image_bytes(reference)
    assert compare_images(reference_bytes, reference_bytes)["similarity_score"] == 100.0
    assert compare_images(reference_bytes, _image_bytes(resized))["similarity_score"] >= 75.0
    assert compare_images(reference_bytes, compressed)["similarity_score"] >= 75.0
    assert compare_images(reference_bytes, _image_bytes(unrelated))["similarity_score"] < 75.0


def test_image_comparison_reports_invalid_image_data():
    result = compare_images(b"not an image", b"still not an image")
    assert "error" in result
    assert result["similarity_score"] == 0.0
