from typing import Any, Dict, List, Optional, Protocol


SCORING_WEIGHTS = {
    "image_analysis": 25.0,
    "name_analysis": 25.0,
    "url_analysis": 30.0,
    "publisher_mismatch": 20.0,
    "scam_patterns": 15.0,
    "model_analysis": 35.0,
    "multimodal_correlation_max": 15.0,
}


class TextRiskModel(Protocol):
    """Optional local model adapter; no trained model is currently configured."""

    def classify(self, text: str) -> Dict[str, Any]:
        """Return a risk_score (0-100), model confidence, source, and evidence."""


def _bounded_score(value: Any, field_name: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not 0 <= value <= 100
    ):
        raise ValueError(f"{field_name} must be a number between 0 and 100.")
    return float(value)


def compute_overall_risk(
    name_analysis: Optional[Dict[str, Any]] = None,
    image_analysis: Optional[Dict[str, Any]] = None,
    url_analysis: Optional[Dict[str, Any]] = None,
    scam_dna_analysis: Optional[Dict[str, Any]] = None,
    publisher_mismatch: bool = False,
    is_official_entity: bool = False,
    model_analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Combine available modality scores as a bounded, explainable heuristic."""
    components = []
    evidence_items: List[str] = []
    missing_info: List[str] = []

    def add_component(
        source: str,
        score: Any,
        weight_key: str,
        detail: str,
        reasons: Optional[List[str]] = None,
    ) -> None:
        bounded = _bounded_score(score, f"{source} risk score")
        components.append({
            "source": source,
            "score": bounded,
            "weight": SCORING_WEIGHTS[weight_key],
            "detail": detail,
        })
        if reasons and bounded > 0:
            evidence_items.extend(str(reason) for reason in reasons if reason)

    if name_analysis is not None:
        name_score = name_analysis.get("similarity_score", 0)
        suspicious_name = (
            name_analysis.get("is_suspicious", False)
            or name_analysis.get("homoglyph_detected", False)
        )
        add_component(
            "Brand Name Heuristics",
            name_score if suspicious_name else 0,
            "name_analysis",
            "A name-pattern signal was compared with the configured brand entry.",
            name_analysis.get("reasons"),
        )
    else:
        missing_info.append("No verified brand name was available for look-alike comparison.")

    if image_analysis is not None:
        image_score = image_analysis.get("risk_score")
        if image_score is None:
            image_similarity = image_analysis.get("similarity_score", 0)
            image_score = image_similarity if image_similarity >= 75 else 0
        add_component(
            "Visual Image Analysis",
            image_score,
            "image_analysis",
            "An image-comparison signal was supplied.",
            image_analysis.get("reasons"),
        )
    else:
        missing_info.append("No comparable official reference image was supplied.")

    if url_analysis is not None:
        url_score = url_analysis.get("risk_score", 0)
        add_component(
            "URL Security Inspection",
            url_score,
            "url_analysis",
            "URL structure was screened locally; no network request was made.",
            url_analysis.get("reasons"),
        )
    else:
        missing_info.append("No URL was available for infrastructure screening.")

    if publisher_mismatch:
        add_component(
            "Mobile App Identity",
            100,
            "publisher_mismatch",
            "Submitted publisher text did not match the configured verified publisher list.",
            ["The submitted publisher name differs from the configured verified publisher entry."],
        )

    if scam_dna_analysis is not None:
        add_component(
            "Scam Message Patterns",
            scam_dna_analysis.get("risk_score", 0),
            "scam_patterns",
            f"Matched {len(scam_dna_analysis.get('patterns_matched', []))} distinct text-pattern categories.",
            scam_dna_analysis.get("reasons"),
        )
    else:
        missing_info.append("No message or profile text was available for language-pattern screening.")

    model_confidence = None
    if model_analysis is not None:
        model_score = _bounded_score(
            model_analysis.get("risk_score"),
            "Model risk_score",
        )
        model_confidence = model_analysis.get("confidence")
        if model_confidence is not None:
            model_confidence = int(round(
                _bounded_score(model_confidence, "Model confidence")
            ))
        components.append({
            "source": str(model_analysis.get("source") or "Local Text Model"),
            "score": model_score,
            "weight": SCORING_WEIGHTS["model_analysis"],
            "detail": "Optional local model signal; review its provenance and evidence.",
        })
        evidence_items.extend(
            str(reason) for reason in model_analysis.get("reasons", []) if reason
        )

    signals = []
    active_components = [
        component for component in components if component["score"] > 0
    ]
    weight_total = sum(component["weight"] for component in active_components)
    weighted_score = 0.0
    if weight_total:
        for component in active_components:
            contribution = component["score"] * component["weight"] / weight_total
            weighted_score += contribution
            if component["score"] > 0:
                signals.append({
                    "source": component["source"],
                    "contribution": round(contribution, 1),
                    "detail": component["detail"],
                })

    correlation_bonus = 0.0
    if (
        name_analysis
        and name_analysis.get("is_suspicious", False)
        and url_analysis
        and url_analysis.get("is_suspicious", False)
    ):
        correlation_bonus = SCORING_WEIGHTS["multimodal_correlation_max"]
        signals.append({
            "source": "Multimodal Correlation",
            "contribution": correlation_bonus,
            "detail": "Separate name and URL rule sets both produced suspicious indicators.",
        })
    elif (
        name_analysis
        and name_analysis.get("similarity_score", 0) >= 75
        and image_analysis
        and image_analysis.get("similarity_score", 0) >= 75
    ):
        correlation_bonus = SCORING_WEIGHTS["multimodal_correlation_max"]
        signals.append({
            "source": "Multimodal Correlation",
            "contribution": correlation_bonus,
            "detail": "Separate name and visual comparison signals both indicate similarity.",
        })

    if is_official_entity:
        registry_finding = (
            "Candidate matches a configured verified registry entry; "
            "current ownership was not independently verified."
        )
        signals.append({
            "source": "Configured Brand Registry",
            "contribution": 0,
            "detail": registry_finding,
        })
        evidence_items.append(registry_finding)
        missing_info.append(
            "A registry match does not independently verify current ownership."
        )

    final_score = int(round(min(100.0, max(0.0, weighted_score + correlation_bonus))))
    if final_score >= 75:
        risk_band = "Critical Risk"
        status = "Suspicious"
        recommended_action = (
            "Prioritize manual review and independently verify the source before restricting or reporting it."
        )
    elif final_score >= 50:
        risk_band = "High Risk"
        status = "Suspicious"
        recommended_action = (
            "Escalate for manual review; do not treat heuristic findings as confirmed attribution."
        )
    elif final_score >= 25:
        risk_band = "Needs Review"
        status = "Under Review"
        recommended_action = (
            "Gather independent evidence and confirm authorization before taking enforcement action."
        )
    else:
        risk_band = "Lower Risk"
        status = "Low Risk"
        recommended_action = (
            "No configured high-risk indicators were triggered; this does not prove the content is safe."
        )

    model_source = (
        f"rules+{model_analysis.get('source') or 'model'}"
        if model_analysis else "rules"
    )
    technical_explanation = (
        "; ".join(signal["detail"] for signal in signals if signal["contribution"] > 0)
        or "No configured risk signals were triggered."
    )
    if any(component["score"] > 0 for component in components):
        user_explanation = "Review this content before acting. " + " ".join(evidence_items[:3])
    elif is_official_entity:
        user_explanation = (
            "A configured verified registry entry matched, but the current account or domain owner was not independently verified."
        )
    else:
        user_explanation = (
            "No configured warning signs were detected, but this automated check cannot verify that the content is safe."
        )
    final_evidence = evidence_items or [
        "No configured risk indicators were detected; this does not establish that the content is safe."
    ]

    return {
        "risk_score": final_score,
        "risk_band": risk_band,
        "status": status,
        "confidence": model_confidence,
        "model_source": model_source,
        "evidence_count": len(evidence_items),
        "signals": signals,
        "findings": final_evidence,
        "missing_information": missing_info,
        "recommended_action": recommended_action,
        "is_suspicious": final_score >= 50,
        "technical_explanation": technical_explanation,
        "user_explanation": user_explanation,
        "limitations": [
            "Scores are heuristic indicators, not calibrated probabilities or proof of fraud.",
            "Automated findings require human review and independent source verification.",
        ],
        "recommended_actions": [recommended_action],
    }
