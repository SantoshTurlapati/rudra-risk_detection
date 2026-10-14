import re
from typing import Any, Dict

from app.ai.url_safety import extract_urls

MAX_MESSAGE_LENGTH = 10_000

SCAM_SIGNATURES = [
    {
        "id": "DNA-URGENCY",
        "category": "Urgency & Coercion",
        "weight": 25,
        "description": "The text creates artificial urgency or threatens an account consequence.",
        "regexes": [
            r"\b(within\s+\d+\s*(hours?|hrs?|mins?))\b",
            r"\b(account\s+(will\s+be\s+)?(blocked|suspended|terminated|deactivated|frozen))\b",
            r"\b(immediate\s+(action|verification|attention)\s+required)\b",
            r"\b(kyc\s+(expired|pending|incomplete))\b",
            r"\b(last\s+chance|final\s+notice|penalty)\b",
            r"\b(urgent|immediately|without\s+delay)\b",
            r"\b(act\s+now|expires?\s+(today|soon|in\s+\d+))\b",
        ],
    },
    {
        "id": "DNA-FINANCIAL-BAIT",
        "category": "Financial Bait & Rewards",
        "weight": 20,
        "description": "The text promotes an unexpected prize, refund, reward, or guaranteed return.",
        "regexes": [
            r"\b(cashback|reward|won\s+(₹|rs\.?|\$)\s*\d+)\b",
            r"\b(claim\s+(now|free|reward|bonus|gift|prize))\b",
            r"\b(guaranteed\s+(profit|return|income))\b",
            r"\b(crypto\s+trading|double\s+your\s+money)\b",
            r"\b(free\s+gift\s+card|lucky\s+draw)\b",
            r"\b(tax\s+refund|refund\s+(approved|pending|release))\b",
            r"\b(job|work)\s+offer\b.{0,60}\b(registration|processing)\s+fee\b",
            r"\b(pay|transfer|deposit)\s+(now|immediately|to\s+release)\b",
        ],
    },
    {
        "id": "DNA-CREDENTIAL-HARVEST",
        "category": "Credential & Secret Harvesting",
        "weight": 35,
        "description": "The text asks for credentials, payment secrets, or identity information.",
        "regexes": [
            r"\b(enter|share|send|provide|tell)\s+(your\s+)?(otp|pin|upi\s*pin|password|cvv)\b",
            r"\b(otp|one[- ]time password|upi\s*pin)\b.{0,50}\b(share|send|enter|reply|provide)\b",
            r"\b(pan\s*card\s*(update|verification|number))\b",
            r"\b(aadhaar\s*(link|verification|number))\b",
            r"\b(net\s*banking\s*(credentials|login|password))\b",
            r"\b(verify\s+your\s+card\s+details)\b",
        ],
    },
    {
        "id": "DNA-IMPERSONATION",
        "category": "Brand & Authority Impersonation",
        "weight": 25,
        "description": "The text claims authority or support identity that cannot be verified from the message.",
        "regexes": [
            r"\b(official\s+(support|bank|representative|executive|care))\b",
            r"\b(customer\s+care\s+(helpline|team|desk))\b",
            r"\b(rbi\s+guidelines?|reserve\s+bank|income\s+tax\s+department)\b",
            r"\b(cyber\s+crime\s+cell|police\s+notice)\b",
            r"\b(sbi\s+support|hdfc\s+care|icici\s+desk|paytm\s+kyc)\b",
            r"\b(delivery|courier)\s+(company|agent|support)\b",
            r"\b(verification|support)\s+team\b",
        ],
    },
    {
        "id": "DNA-ACTION-CALL",
        "category": "Malicious Action Prompt",
        "weight": 20,
        "description": "The text directs the recipient to click, install, scan, or move to another channel.",
        "regexes": [
            r"\b(click\s+(here|link|below|this\s+url))\b",
            r"\b(download\s+(the\s+)?(apk|app|file|software))\b",
            r"\b(install\s+anydesk|teamviewer|quicksupport)\b",
            r"\b(scan\s+(this\s+)?qr\s*(code)?\s*to\s*(receive|get))\b",
            r"\b(install|download)\s+(this|our)\s+app\b",
            r"\b(move|continue|contact)\s+(this\s+)?conversation\s+(to|on)\s+(telegram|whatsapp)\b",
        ],
    },
]


def analyze_scam_dna(text: str) -> Dict[str, Any]:
    """Return explainable rule matches; this does not determine whether text is fraudulent."""
    if not isinstance(text, str):
        raise ValueError("Message text must be a string.")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"Message text cannot exceed {MAX_MESSAGE_LENGTH} characters.")

    urls = extract_urls(text)
    text_without_urls = text
    for url in urls:
        text_without_urls = text_without_urls.replace(url, " ")

    patterns_matched = []
    matched_snippets = []
    evidence = []
    reasons = []
    total_score = 0

    for signature in SCAM_SIGNATURES:
        category_matches = []
        for pattern in signature["regexes"]:
            for match in re.finditer(pattern, text_without_urls, re.IGNORECASE):
                snippet = match.group(0).strip()
                if snippet and snippet.casefold() not in {
                    item.casefold() for item in matched_snippets
                }:
                    matched_snippets.append(snippet[:160])
                if snippet and all(
                    item["excerpt"].casefold() != snippet.casefold()
                    for item in category_matches
                ):
                    category_matches.append({
                        "id": signature["id"],
                        "category": signature["category"],
                        "excerpt": snippet[:160],
                        "explanation": signature["description"],
                    })

        if category_matches:
            total_score += signature["weight"]
            patterns_matched.append({
                "id": signature["id"],
                "category": signature["category"],
                "description": signature["description"],
                "weight": signature["weight"],
            })
            evidence.extend(category_matches)
            reasons.append(f"{signature['category']}: {signature['description']}")

    return {
        "risk_score": min(100, total_score),
        "patterns_matched": patterns_matched,
        "matched_snippets": matched_snippets,
        "categories": [item["category"] for item in patterns_matched],
        "evidence": evidence,
        "urls": urls,
        "confidence": None,
        "reasons": reasons or ["No configured scam-pattern indicators were detected."],
        "model_source": "rules",
        "limitations": [
            "Rule matches are indicators for human review, not proof that the message is fraudulent.",
            "English-language patterns are used; other-language scam wording may not be detected.",
        ],
    }
