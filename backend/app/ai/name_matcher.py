import re
from typing import Dict, Any, List
from rapidfuzz import fuzz, distance
from app.ai.homoglyphs import detect_and_normalize_homoglyphs

IMPERSONATION_KEYWORDS = [
    "official", "support", "care", "helpdesk", "help", "customer",
    "service", "verify", "verification", "rewards", "reward", "kyc",
    "update", "security", "alert", "agent", "executive", "admin", "team"
]

def analyze_name_impersonation(candidate_name: str, official_brand: str) -> Dict[str, Any]:
    """
    Compares candidate name against official brand name to detect look-alike tactics,
    typosquatting, character swaps, homoglyphs, and deceptive suffix/prefix words.
    """
    findings: List[str] = []

    # Clean input
    cand_raw = (candidate_name or "").strip()
    brand_raw = (official_brand or "").strip()

    if not cand_raw or not brand_raw:
        return {
            "similarity_score": 0.0,
            "is_suspicious": False,
            "reasons": ["Empty candidate or brand name provided."],
            "matched_keywords": [],
            "homoglyph_detected": False,
            "levenshtein_distance": 999
        }

    # Step 1: Homoglyph and Unicode analysis
    cand_norm, homoglyphs, has_homoglyphs = detect_and_normalize_homoglyphs(cand_raw)
    brand_norm, _, _ = detect_and_normalize_homoglyphs(brand_raw)

    if has_homoglyphs:
        findings.extend(homoglyphs)

    # Strip special punctuation for token matching
    cand_tokens = set(re.findall(r'[a-zA-Z0-9]+', cand_norm))
    brand_tokens = set(re.findall(r'[a-zA-Z0-9]+', brand_norm))

    # Compute brand acronyms (e.g. State Bank of India -> sbi, National Payments Corporation of India -> npci)
    brand_acronym = "".join([w[0] for w in brand_norm.split() if w and w not in ["of", "and", "the", "in", "for"]])
    if len(brand_acronym) >= 2:
        brand_tokens.add(brand_acronym)

    # Check for impersonation keywords
    matched_keywords = [kw for kw in IMPERSONATION_KEYWORDS if kw in cand_norm]
    if matched_keywords:
        findings.append(f"Contains high-risk trust/support keywords: {', '.join(matched_keywords)}")

    # Fuzzy similarity metrics
    ratio = fuzz.ratio(cand_norm, brand_norm)
    partial_ratio = fuzz.partial_ratio(cand_norm, brand_norm)
    token_set_ratio = fuzz.token_set_ratio(cand_norm, brand_norm)

    # Levenshtein distance
    lev_dist = distance.Levenshtein.distance(cand_norm, brand_norm)

    # Check for direct containment with deceptive modifiers (e.g. "SBI" in "sbi_care_official")
    contains_brand = (
        brand_norm in cand_norm or
        (brand_acronym and brand_acronym in cand_tokens) or
        any(bt in cand_tokens for bt in brand_tokens if len(bt) >= 3) or
        (brand_acronym and brand_acronym in cand_norm)
    )

    is_exact_match = (cand_norm == brand_norm)
    is_suspicious = False

    if is_exact_match:
        findings.append("Candidate name is an exact match to the brand name.")
        final_similarity = 100.0
    elif has_homoglyphs and (ratio > 60 or contains_brand):
        findings.append("Deceptive Unicode homoglyphs used to mimic brand appearance.")
        is_suspicious = True
        final_similarity = max(ratio, 85.0)
    elif contains_brand and matched_keywords:
        findings.append(f"Brand '{official_brand}' combined with deceptive authority keywords.")
        is_suspicious = True
        final_similarity = max(token_set_ratio, 80.0)
    elif lev_dist in [1, 2] and len(brand_norm) >= 4:
        findings.append(f"Typosquatting detected: edit distance of {lev_dist} from authentic brand name.")
        is_suspicious = True
        final_similarity = max(ratio, 75.0)
    else:
        final_similarity = float(max(ratio, token_set_ratio if contains_brand else ratio))
        if final_similarity >= 70:
            is_suspicious = True
            findings.append(f"High name similarity ({final_similarity:.1f}%) detected.")

    return {
        "similarity_score": round(final_similarity, 1),
        "is_suspicious": is_suspicious,
        "reasons": findings,
        "matched_keywords": matched_keywords,
        "homoglyph_detected": has_homoglyphs,
        "levenshtein_distance": lev_dist,
        "normalized_candidate": cand_norm
    }
