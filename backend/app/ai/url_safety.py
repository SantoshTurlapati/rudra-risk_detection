
import ipaddress
import re
import unicodedata
from typing import Any, Dict, List
from urllib.parse import unquote, urlparse


SUSPICIOUS_TLDS = {
    "xyz", "top", "buzz", "club", "work", "loan",
    "tk", "ml", "ga", "cf", "gq", "fit", "live",
    "rest", "surf", "monster", "icu", "click", "download",
}

PHISHING_PATH_KEYWORDS = [
    "login", "verify", "verification", "kyc", "update",
    "banking", "secure", "otp", "pan", "aadhar", "aadhaar",
    "claim", "reward", "cashback", "unfreeze", "wallet",
    "password", "auth", "signin", "account",
]

COMMON_DOMAIN_LABELS = {
    "com", "org", "net", "gov", "edu", "online",
}
SHORTENER_DOMAINS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly",
    "is.gd", "buff.ly", "cutt.ly", "shorturl.at",
}

URL_PATTERN = re.compile(
    r"""(?i)(?:https?://|www\.)[^\s<>"']+|"""
    r"""(?<![\w@])(?:[\w](?:[\w-]{0,61}[\w])?\.)+[\w-]{2,63}(?:/[^\s<>"']*)?"""
)
URL_TRAILING_PUNCTUATION = ".,!?;:)]}"


def is_private_ip(hostname: str) -> bool:
    """Identify private, loopback, link-local, or reserved IP addresses."""
    try:
        ip = ipaddress.ip_address(hostname)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
        )
    except ValueError:
        return hostname.lower().rstrip(".") in {
            "localhost", "127.0.0.1", "::1", "0.0.0.0"
        }


def _looks_like_ambiguous_ip_literal(hostname: str) -> bool:
    """Detect legacy numeric host forms that browsers may interpret as IPs."""
    labels = hostname.rstrip(".").lower().split(".")
    if not 1 <= len(labels) <= 4:
        return False

    def is_number(label: str) -> bool:
        return bool(
            re.fullmatch(r"(?:0x[0-9a-f]+|[0-9]+)", label)
            or re.fullmatch(r"0[0-7]+", label)
        )

    return all(is_number(label) for label in labels)


def extract_urls(text: str, limit: int = 5) -> List[str]:
    """Extract a bounded number of URL-like strings without making requests."""
    if limit <= 0:
        return []
    urls = []
    seen = set()
    for match in URL_PATTERN.finditer(text or ""):
        candidate = match.group(0).rstrip(URL_TRAILING_PUNCTUATION)
        if candidate and candidate.casefold() not in seen:
            seen.add(candidate.casefold())
            urls.append(candidate)
            if len(urls) >= limit:
                break
    return urls


def _normalize_domain(value: str) -> str:
    """Normalize a configured domain without performing network requests."""
    value = (value or "").strip().lower()

    if not value:
        return ""

    if "://" in value:
        value = urlparse(value).hostname or ""

    value = value.split("/")[0].strip().rstrip(".")

    # Remove a port from ordinary hostnames, but preserve IPv6 addresses.
    if value.startswith("[") and "]" in value:
        value = value[1:value.index("]")]
    elif value.count(":") == 1:
        host_part, port_part = value.rsplit(":", 1)
        if port_part.isdigit():
            value = host_part

    value = value.strip(".")
    try:
        return value.encode("idna").decode("ascii")
    except UnicodeError:
        return ""


def _brand_tokens(domain: str) -> set:
    """Extract useful brand-like labels from a configured domain."""
    tokens = {
        token
        for token in re.split(r"[.\-_]+", domain.lower())
        if len(token) >= 3 and token not in COMMON_DOMAIN_LABELS
    }

    # Preserve the project’s existing SBI / NPCI / UPI handling.
    if "sbi" in domain:
        tokens.add("sbi")

    if "npci" in domain or "upi" in domain:
        tokens.update({"npci", "upi"})

    return tokens


def analyze_url_safety(
    raw_url: str,
    official_brand_domain: str = "",
) -> Dict[str, Any]:
    """
    Analyze URL structure for common phishing indicators.

    This is heuristic screening, not a definitive determination
    that a URL is safe or malicious. No network requests are made.
    """
    if not isinstance(raw_url, str):
        raise ValueError("URL must be text.")

    if any(
        unicodedata.category(character) == "Cc"
        for character in raw_url
    ):
        raise ValueError("URL must not contain control characters.")

    url = raw_url.strip()

    if not url:
        raise ValueError(
            "URL is required. Please enter a valid website URL."
        )

    # Accept explicit HTTP/HTTPS URLs. Also support domain:port input.
    scheme_match = re.match(
        r"^([a-zA-Z][a-zA-Z0-9+.-]*):",
        url,
    )
    host_port_match = re.match(
        r"^(?:\[[0-9a-fA-F:]+\]|[^/:?#]+):\d+(?:[/\?#]|$)",
        url,
    )

    if "://" in url:
        supplied_scheme = url.split("://", 1)[0].lower()
        if supplied_scheme not in {"http", "https"}:
            raise ValueError(
                f"Unsupported URL scheme '{supplied_scheme}'. "
                "Only HTTP and HTTPS URLs are supported."
            )
    elif scheme_match and not host_port_match:
        supplied_scheme = scheme_match.group(1).lower()

        # A dotted hostname such as example.com:8080 is host:port,
        # not a URL scheme.
        prefix = supplied_scheme
        if "." not in prefix and prefix != "localhost":
            raise ValueError(
                f"Unsupported URL scheme '{supplied_scheme}'. "
                "Only HTTP and HTTPS URLs are supported."
            )

        url = "http://" + url
    else:
        url = "http://" + url

    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        raw_hostname = (parsed.hostname or "").rstrip(".")
        hostname = raw_hostname.encode("idna").decode("ascii").lower()
        _port = parsed.port
        if "@" in parsed.netloc:
            raise ValueError("URLs containing embedded credentials are not supported.")
        path = unquote(parsed.path).lower()
        query = unquote(parsed.query).lower()

        if scheme not in {"http", "https"}:
            raise ValueError("Only HTTP and HTTPS URLs are supported.")

        if not hostname:
            raise ValueError("URL does not contain a hostname.")

        try:
            ipaddress.ip_address(hostname)
            is_ip_address = True
        except ValueError:
            is_ip_address = False

        if not is_ip_address and hostname != "localhost":
            if (
                "." not in hostname
                and not _looks_like_ambiguous_ip_literal(hostname)
            ):
                raise ValueError(
                    "Enter a domain such as example.com."
                )

            labels = hostname.split(".")

            if any(
                not label
                or len(label) > 63
                or label.startswith("-")
                or label.endswith("-")
                or not re.fullmatch(r"[a-z0-9-]+", label)
                for label in labels
            ):
                raise ValueError("The hostname format is invalid.")

            if len(hostname) > 253:
                raise ValueError("The hostname is too long.")

    except (ValueError, UnicodeError) as exc:
        raise ValueError(f"Invalid URL: {exc}") from exc

    findings: List[str] = []
    risk_score = 0
    is_suspicious = False

    # 1. Private or internal IP address
    ssrf_risk = is_private_ip(hostname)
    ambiguous_ip_literal = (
        not is_ip_address and _looks_like_ambiguous_ip_literal(hostname)
    )

    if ssrf_risk:
        findings.append(
            "Private, loopback, link-local, or reserved IP address detected. "
            "Do not fetch this URL automatically; investigate safely."
        )
        risk_score += 90
        is_suspicious = True

    if ambiguous_ip_literal:
        findings.append(
            "The hostname uses an ambiguous numeric address form that some "
            "clients may interpret as an IP address. Verify it without "
            "automatically fetching the URL."
        )
        risk_score += 70
        is_suspicious = True

    # 2. Raw IP address
    if is_ip_address:
        findings.append(
            "The URL uses an IP address instead of a domain name."
        )
        risk_score += 40
        is_suspicious = True

    # 3. Punycode / internationalized domain indicator
    if hostname.startswith("xn--") or ".xn--" in hostname:
        findings.append(
            "Punycode domain detected; check for possible look-alike "
            "or internationalized-domain deception."
        )
        risk_score += 45
        is_suspicious = True

    # 4. TLD review indicator
    parts = hostname.split(".")
    tld = parts[-1] if len(parts) > 1 else ""

    if tld in SUSPICIOUS_TLDS:
        findings.append(
            f"The URL uses a TLD that this heuristic flags for review: .{tld}."
        )
        risk_score += 25
        is_suspicious = True

    if hostname in SHORTENER_DOMAINS:
        findings.append(
            "The hostname is a known URL-shortening service; the destination is not expanded or fetched."
        )
        risk_score += 20
        is_suspicious = True

    # 5. Detect domain-like text embedded in a larger hostname.
    # Example: paypal.com.security-check.example
    embedded_domain_pattern = re.compile(
        r"(?:^|\.)([a-z0-9-]+)\."
        r"(com|net|org|gov|edu|co|in|io)\.",
        re.IGNORECASE,
    )
    embedded_domain_match = embedded_domain_pattern.search(hostname)

    if embedded_domain_match:
        embedded_name = embedded_domain_match.group(1)
        embedded_suffix = embedded_domain_match.group(2)
        findings.append(
            f"Domain-like text '{embedded_name}.{embedded_suffix}' appears "
            "inside a larger hostname; verify the actual registered domain."
        )
        risk_score += 30
        is_suspicious = True

    # 6. Excessive subdomains
    if len(parts) > 4:
        findings.append(
            f"Excessive subdomain depth detected ({len(parts)} labels)."
        )
        risk_score += 20
        is_suspicious = True

    # 7. Compare with the configured official brand domain
    official_clean = _normalize_domain(official_brand_domain)

    if official_clean:
        hostname_is_official = (
            hostname == official_clean
            or hostname.endswith("." + official_clean)
        )

        if not hostname_is_official:
            brand_tokens = _brand_tokens(official_clean)
            hostname_labels = set(re.split(r"[.\-_]+", hostname))
            matched_tokens = sorted(brand_tokens & hostname_labels)

            if matched_tokens:
                token = matched_tokens[0]
                findings.append(
                    f"Possible brand impersonation via a deceptive subdomain: '{token}' appears in "
                    f"'{hostname}', which does not match the configured "
                    f"official domain '{official_clean}'."
                )

                # Avoid adding another brand score for the same embedded
                # domain pattern already identified above.
                if not embedded_domain_match:
                    risk_score += 55

                is_suspicious = True

    # 8. Phishing-related path and query keywords
    matched_keywords = [
        keyword
        for keyword in PHISHING_PATH_KEYWORDS
        if keyword in path or keyword in query
    ]

    if matched_keywords:
        findings.append(
            "Potentially sensitive URL keywords found: "
            + ", ".join(matched_keywords[:4])
        )
        risk_score += 25
        is_suspicious = True

    # 9. HTTP instead of HTTPS
    if scheme != "https":
        findings.append(
            "The URL does not use HTTPS. This alone does not prove phishing."
        )
        risk_score += 15

    # 10. Multiple hyphens in the hostname
    if hostname.count("-") >= 2:
        findings.append(
            "Multiple hyphens appear in the hostname; check for possible "
            "look-alike naming."
        )
        risk_score += 20
        is_suspicious = True

    final_score = min(100, max(0, risk_score))

    return {
        "url": raw_url,
        "hostname": hostname,
        "scheme": scheme,
        "is_ssrf_risk": ssrf_risk,
        "has_ambiguous_ip_literal": ambiguous_ip_literal,
        "risk_score": final_score,
        "is_suspicious": is_suspicious or final_score >= 50,
        "reasons": findings or [
            "No URL warning indicators were detected."
        ],
        "matched_keywords": matched_keywords,
    }
