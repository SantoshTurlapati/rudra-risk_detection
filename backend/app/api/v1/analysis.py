import json
import logging
from typing import Optional
from fastapi import (
    APIRouter, Depends, File, Form, HTTPException, UploadFile, status
)
from sqlalchemy import func
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db, get_current_user, require_organization_id
from app.core.config import settings
from app.db.models import BrandProfile, Investigation, User
from app.schemas.all_schemas import (
    URLAnalysisRequest, ProfileAnalysisRequest,
    AppAnalysisRequest, MessageAnalysisRequest, AnalysisResult
)
from app.ai.name_matcher import analyze_name_impersonation
from app.ai.url_safety import analyze_url_safety, extract_urls
from app.ai.scam_patterns import analyze_scam_dna
from app.ai.image_hasher import compare_images, compute_dhash
from app.ai.image_validation import MAX_IMAGE_BYTES, validate_image_bytes
from app.db.brand_image_references import (
    BrandImageReference,
    is_missing_reference_table_error,
)
from app.storage.brand_images import (
    PrivateImageStorage,
    StorageUnavailable,
    get_brand_image_storage,
    validate_storage_key,
)
from app.ai.risk_engine import compute_overall_risk
from urllib.parse import urlparse

router = APIRouter(prefix="/analysis", tags=["Detection & Analysis"])
logger = logging.getLogger(__name__)


def _selected_brand(
    db: Session,
    brand_id: Optional[str],
    current_user: User
) -> Optional[BrandProfile]:
    if not brand_id:
        return None
    organization_id = require_organization_id(current_user)
    brand = db.query(BrandProfile).filter(
        BrandProfile.id == brand_id,
        BrandProfile.organization_id == organization_id
    ).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


def _json_list(value: Optional[str]) -> list:
    try:
        result = json.loads(value or "[]")
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored brand registry data is invalid."
        ) from exc
    if not isinstance(result, list):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored brand registry data must be a list."
        )
    return result


def _analyze_candidate_url(
    url: str,
    brand: Optional[BrandProfile],
) -> tuple[dict, bool, Optional[str]]:
    initial = analyze_url_safety(url)
    hostname = initial["hostname"]
    official_domains = []
    if brand and brand.is_verified:
        official_domains = [
            str(domain).strip()
            for domain in _json_list(brand.official_domains)
            if isinstance(domain, str) and domain.strip()
        ]

    matched_domain = None
    normalized_domains = []
    for domain in official_domains:
        normalized = domain
        if "://" in normalized:
            normalized = urlparse(normalized).hostname or ""
        normalized = normalized.strip().lower().rstrip(".")
        try:
            normalized = normalized.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored brand registry contains an invalid domain."
            ) from exc
        if normalized:
            normalized_domains.append(normalized)
            if hostname == normalized or hostname.endswith("." + normalized):
                matched_domain = normalized

    compare_domain = matched_domain or (
        normalized_domains[0] if normalized_domains else None
    )
    result = (
        analyze_url_safety(url, official_brand_domain=compare_domain)
        if compare_domain else initial
    )
    return result, matched_domain is not None, matched_domain


def _result_contract(overall: dict, analysis_type: str) -> dict:
    return {
        "analysis_type": analysis_type,
        "is_suspicious": overall["is_suspicious"],
        "indicators": overall["signals"],
        "evidence": overall["findings"],
        "explanations": {
            "technical": overall["technical_explanation"],
            "plain_language": overall["user_explanation"],
        },
        "limitations": overall["limitations"],
        "recommended_actions": overall["recommended_actions"],
        "model_source": overall["model_source"],
    }


def _possible_investigation_matches(
    db: Session,
    current_user: User,
    indicators: list[str],
) -> list[dict]:
    candidates = {value.strip().casefold() for value in indicators if value and value.strip()}
    if not candidates:
        return []

    rows = db.query(Investigation).filter(
        Investigation.organization_id == require_organization_id(current_user),
        func.lower(Investigation.indicator).in_(candidates),
    ).order_by(Investigation.created_at.desc()).limit(10).all()
    return [
        {
            "case_number": row.case_number,
            "type": row.type,
            "indicator": row.indicator,
            "relationship": "Possible exact indicator match; not a confirmed relationship.",
        }
        for row in rows
    ]


@router.post("/url", response_model=AnalysisResult)
def analyze_url(
    req: URLAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    brand = _selected_brand(db, req.brand_id, current_user)
    try:
        url_result, is_official, official_domain = _analyze_candidate_url(req.url, brand)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc)
        ) from exc

    name_result = (
        analyze_name_impersonation(url_result["hostname"], brand.name)
        if brand and brand.is_verified else None
    )

    overall = compute_overall_risk(
        url_analysis=url_result,
        name_analysis=(
            name_result if name_result and name_result["is_suspicious"] else None
        ),
        is_official_entity=is_official
    )
    missing_information = list(overall["missing_information"])
    missing_information.append(
        "Live domain reputation and current ownership verification are not configured."
    )
    return AnalysisResult(
        indicator=req.url,
        type="website",
        risk_score=overall["risk_score"],
        risk_band=overall["risk_band"],
        status=overall["status"],
        confidence=overall["confidence"],
        evidence_count=overall["evidence_count"],
        signals=overall["signals"],
        findings=overall["findings"],
        missing_information=missing_information,
        recommended_action=overall.get(
            "recommended_action",
            "Review the URL indicators and verify the domain through an official source."
        ),
        details={
            "url_metrics": url_result,
            "url_analysis": url_result,
            "name_analysis": name_result,
            "official_domain_match": is_official,
            "matched_official_domain": official_domain or None,
            "possible_investigation_matches": _possible_investigation_matches(
                db, current_user, [url_result["hostname"]]
            ),
        },
        **_result_contract(overall, "url"),
    )


@router.post("/profile", response_model=AnalysisResult)
def analyze_profile(
    req: ProfileAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    brand = _selected_brand(db, req.brand_id, current_user)
    name_results = []
    handle_result = None
    display_name_result = None
    if brand and brand.is_verified:
        handle_result = (
            analyze_name_impersonation(req.handle.lstrip("@"), brand.name)
            if req.handle else None
        )
        display_name_result = (
            analyze_name_impersonation(req.display_name, brand.name)
            if req.display_name else None
        )
        name_results = [
            result for result in (handle_result, display_name_result)
            if result
        ]
    name_result = max(
        name_results,
        key=lambda result: (
            result.get("similarity_score", 0),
            result.get("homoglyph_detected", False)
        ),
        default=None
    )

    is_official = False
    if brand and brand.is_verified and req.handle:
        platform = {
            "x (twitter)": "x",
            "twitter": "x",
        }.get(req.platform.casefold(), req.platform.casefold())
        for social in _json_list(brand.official_socials):
            if (
                isinstance(social, dict)
                and str(social.get("platform") or "").casefold() == platform
                and str(social.get("handle") or "").casefold() == req.handle.casefold()
            ):
                is_official = True
                break

    if is_official and handle_result:
        name_results = [
            result for result in name_results if result is not handle_result
        ]
        name_result = max(
            name_results,
            key=lambda result: (
                result.get("similarity_score", 0),
                result.get("homoglyph_detected", False)
            ),
            default=None
        )

    scam_dna = analyze_scam_dna(req.bio_text or "")
    profile_urls = []
    if req.profile_url:
        try:
            profile_urls.append(_analyze_candidate_url(req.profile_url, brand))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid profile URL: {exc}"
            ) from exc
    unparsed_profile_urls = []
    for candidate_url in extract_urls(req.bio_text or ""):
        if req.profile_url and candidate_url.casefold() == req.profile_url.casefold():
            continue
        try:
            profile_urls.append(_analyze_candidate_url(candidate_url, brand))
        except ValueError:
            unparsed_profile_urls.append(candidate_url)
            continue

    url_results = [item[0] for item in profile_urls]
    url_result = max(url_results, key=lambda item: item["risk_score"], default=None)
    verified_profile_match = any(item[1] for item in profile_urls)

    overall = compute_overall_risk(
        name_analysis=name_result,
        url_analysis=url_result,
        scam_dna_analysis=scam_dna if scam_dna["patterns_matched"] else None,
        is_official_entity=is_official or verified_profile_match
    )
    missing_information = list(overall["missing_information"])
    missing_information.append(
        "No live social-platform account or ownership verification is configured."
    )
    missing_information.append(
        "Account age, follower counts, posting activity, and platform verification were not supplied by a trusted source."
    )
    if brand and not brand.is_verified:
        missing_information.append(
            "The selected brand registry entry is unverified and was not used as an official comparison."
        )
    if unparsed_profile_urls:
        missing_information.append(
            f"{len(unparsed_profile_urls)} URL-like profile value(s) could not be parsed."
        )

    return AnalysisResult(
        indicator=req.handle or req.display_name or req.profile_url or "Profile text",
        type="social_profile",
        risk_score=overall["risk_score"],
        risk_band=overall["risk_band"],
        status=overall["status"],
        confidence=overall["confidence"],
        evidence_count=overall["evidence_count"],
        signals=overall["signals"],
        findings=overall["findings"],
        missing_information=missing_information,
        recommended_action=overall["recommended_action"],
        details={
            "name_analysis": name_result,
            "display_name_analysis": display_name_result,
            "registry_handle_match": is_official,
            "registry_profile_url_match": verified_profile_match,
            "urls": url_results,
            "scam_dna": scam_dna,
            "account_metadata": {
                "account_age": "Not provided",
                "followers": "Not provided",
                "following": "Not provided",
                "posting_activity": "Not provided",
                "platform_verification": "Not provided",
                "profile_image_comparison": "Unavailable",
            },
            "possible_investigation_matches": _possible_investigation_matches(
                db,
                current_user,
                [req.handle or "", *(item["hostname"] for item in url_results)],
            ),
        },
        **_result_contract(overall, "profile"),
    )


@router.post("/app", response_model=AnalysisResult)
def analyze_app(
    req: AppAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    brand = _selected_brand(db, req.brand_id, current_user)
    submitted_store_url_analysis = None
    if req.store_url:
        try:
            submitted_store_url_analysis = analyze_url_safety(req.store_url)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
    authorized_publishers = (
        _json_list(brand.authorized_publishers)
        if brand and brand.is_verified else []
    )
    official_apps = (
        _json_list(brand.official_apps) if brand and brand.is_verified else []
    )

    is_official = False
    if brand and brand.is_verified:
        for official_app in official_apps:
            if (
                isinstance(official_app, dict)
                and req.package_name
                and str(official_app.get("package_id") or "").casefold()
                == req.package_name.casefold()
            ):
                is_official = True
                break

    publisher_mismatch = False
    normalized_publishers = [
        publisher.casefold()
        for publisher in authorized_publishers
        if isinstance(publisher, str)
    ]
    if req.developer_name and normalized_publishers:
        publisher_mismatch = not any(
            publisher in req.developer_name.casefold()
            for publisher in normalized_publishers
        )

    name_result = (
        analyze_name_impersonation(req.app_name, brand.name)
        if brand and brand.is_verified else None
    )
    desc_scam = analyze_scam_dna(req.description or "")

    overall = compute_overall_risk(
        name_analysis=name_result,
        url_analysis=submitted_store_url_analysis,
        publisher_mismatch=publisher_mismatch,
        scam_dna_analysis=desc_scam if desc_scam["patterns_matched"] else None,
        is_official_entity=is_official
    )
    missing_information = list(overall["missing_information"])
    missing_information.append(
        "No live app-store listing or publisher-signature verification is configured."
    )

    return AnalysisResult(
        indicator=req.package_name or req.app_name,
        type="mobile_app",
        risk_score=overall["risk_score"],
        risk_band=overall["risk_band"],
        status=overall["status"],
        confidence=overall["confidence"],
        evidence_count=overall["evidence_count"],
        signals=overall["signals"],
        findings=overall["findings"],
        missing_information=missing_information,
        recommended_action=overall["recommended_action"],
        details={
            "name_analysis": name_result,
            "publisher_mismatch": publisher_mismatch,
            "registry_package_match": is_official,
            "submitted_store_url_analysis": submitted_store_url_analysis,
        },
        **_result_contract(overall, "app"),
    )


@router.post("/message", response_model=AnalysisResult)
def analyze_message(
    req: MessageAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    brand = _selected_brand(db, req.brand_id, current_user)
    scam_dna = analyze_scam_dna(req.message_text)
    name_result = (
        analyze_name_impersonation(req.sender_identifier, brand.name)
        if req.sender_identifier and brand and brand.is_verified else None
    )

    message_urls = []
    for candidate_url in scam_dna["urls"]:
        try:
            url_result, registry_match, official_domain = _analyze_candidate_url(
                candidate_url,
                brand,
            )
            message_urls.append({
                **url_result,
                "registry_domain_match": registry_match,
                "matched_official_domain": official_domain,
            })
        except ValueError as exc:
            message_urls.append({
                "url": candidate_url,
                "error": str(exc),
                "risk_score": None,
            })

    valid_url_results = [
        item for item in message_urls if item.get("risk_score") is not None
    ]
    highest_url_risk = max(
        valid_url_results,
        key=lambda item: item["risk_score"],
        default=None,
    )
    overall = compute_overall_risk(
        scam_dna_analysis=scam_dna,
        name_analysis=name_result,
        url_analysis=highest_url_risk,
        is_official_entity=any(
            item.get("registry_domain_match") for item in valid_url_results
        ),
    )
    missing_information = list(overall["missing_information"])
    if not message_urls:
        missing_information.append("No URL was provided for infrastructure inspection.")
    missing_information.append(
        "No live threat-intelligence feed or sender identity verification is configured."
    )

    return AnalysisResult(
        indicator=req.message_text[:80] + ("..." if len(req.message_text) > 80 else ""),
        type="message",
        risk_score=overall["risk_score"],
        risk_band=overall["risk_band"],
        status=overall["status"],
        confidence=overall["confidence"],
        evidence_count=overall["evidence_count"],
        signals=overall["signals"],
        findings=overall["findings"],
        missing_information=missing_information,
        recommended_action=overall["recommended_action"],
        details={
            "scam_dna": scam_dna,
            "sender_analysis": name_result,
            "urls": message_urls,
            "possible_investigation_matches": _possible_investigation_matches(
                db,
                current_user,
                [
                    req.sender_identifier or "",
                    *(item["hostname"] for item in valid_url_results),
                ],
            ),
        },
        **_result_contract(overall, "message"),
    )


@router.post("/image", response_model=AnalysisResult)
async def analyze_image(
    file: UploadFile = File(...),
    brand_id: Optional[str] = Form(None),
    indicator_label: Optional[str] = Form("Uploaded Image Asset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: PrivateImageStorage = Depends(get_brand_image_storage),
):
    brand = _selected_brand(db, brand_id, current_user)
    contents = await file.read(MAX_IMAGE_BYTES + 1)
    try:
        candidate = validate_image_bytes(contents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    import io
    from PIL import Image

    with Image.open(io.BytesIO(contents)) as candidate_image:
        cand_dhash = compute_dhash(candidate_image)

    comparison = {
        "comparison_available": False,
        "status": "no_brand_selected" if not brand else "no_valid_reference",
        "references_compared": 0,
        "review_threshold": settings.BRAND_IMAGE_REVIEW_THRESHOLD,
        "method": "Weighted similarity of 64-bit difference and average perceptual hashes.",
        "explanation": (
            "Visual similarity is a heuristic signal, not proof of impersonation "
            "or image authenticity."
        ),
        "matches": [],
    }
    reason = (
        "No brand was selected; no official reference-image comparison was performed."
        if not brand else
        "No active official image reference is available for this brand. "
        "Visual impersonation could not be assessed."
    )

    if brand:
        try:
            references = db.query(BrandImageReference).filter(
                BrandImageReference.organization_id == current_user.organization_id,
                BrandImageReference.brand_id == brand.id,
                BrandImageReference.reference_status == "active",
            ).all()
        except OperationalError as exc:
            db.rollback()
            if not is_missing_reference_table_error(exc):
                logger.exception("Database failed during official image reference lookup")
                raise HTTPException(
                    status_code=503,
                    detail="The application database is unavailable.",
                ) from exc
            raise HTTPException(
                status_code=503,
                detail=(
                    "Official image reference storage is not initialized. "
                    "An additive database migration requires approval."
                ),
            ) from exc

        if references:
            matches = []
            for reference in references:
                try:
                    validate_storage_key(reference.storage_key)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=503,
                        detail="Stored official-image reference has an invalid storage key.",
                    ) from exc
                try:
                    reference_data = storage.get(reference.storage_key)
                except StorageUnavailable as exc:
                    raise HTTPException(
                        status_code=503,
                        detail="Private official-image storage is unavailable.",
                    ) from exc
                except (OSError, ValueError) as exc:
                    raise HTTPException(
                        status_code=503,
                        detail="Private official-image storage could not read a reference.",
                    ) from exc
                try:
                    stored_image = validate_image_bytes(reference_data)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=503,
                        detail="Stored official-image reference is invalid.",
                    ) from exc
                if (
                    stored_image.content_hash != reference.content_hash
                    or stored_image.media_type != reference.media_type
                ):
                    raise HTTPException(
                        status_code=503,
                        detail="Stored official-image reference failed its integrity check.",
                    )
                result = compare_images(contents, reference_data)
                if "error" in result:
                    raise HTTPException(
                        status_code=503,
                        detail="Image comparison could not be completed.",
                    )
                score = result["similarity_score"]
                matches.append({
                    "reference_id": reference.id,
                    "content_hash": reference.content_hash,
                    "media_type": reference.media_type,
                    "similarity_score": score,
                    "review_recommended": score >= settings.BRAND_IMAGE_REVIEW_THRESHOLD,
                    "interpretation": (
                        "Review recommended based on visual resemblance."
                        if score >= settings.BRAND_IMAGE_REVIEW_THRESHOLD else
                        "No strong resemblance signal from this perceptual comparison."
                    ),
                    "limitations": [
                        "Perceptual similarity is heuristic and does not prove impersonation or authenticity.",
                        "The submitted reference is organization-provided and is not independently verified.",
                    ],
                })
            matches.sort(key=lambda item: item["similarity_score"], reverse=True)
            comparison.update({
                "comparison_available": True,
                "status": "compared",
                "references_compared": len(matches),
                "best_match": matches[0]["reference_id"],
                "matches": matches,
            })
            reason = (
                "Candidate image compared with saved organization-provided references. "
                "Review any visual resemblance; similarity alone does not establish impersonation."
            )

    return AnalysisResult(
        indicator=indicator_label or file.filename or "Uploaded Image Asset",
        type="image",
        risk_score=None,
        risk_band="Unverified",
        status="Unverified",
        confidence=None,
        evidence_count=comparison["references_compared"],
        signals=[],
        findings=[reason],
        missing_information=(
            ["Saved reference images are organization-submitted and not independently verified."]
            if comparison["comparison_available"] else [reason]
        ),
        recommended_action=(
            "Verify the image against an independently sourced official asset "
            "before classifying it as safe or malicious."
        ),
        details={
            "dhash": cand_dhash,
            "candidate_content_hash": candidate.content_hash,
            "comparison": comparison
        },
        analysis_type="image",
        is_suspicious=any(
            match["review_recommended"] for match in comparison["matches"]
        ),
        evidence=[reason],
        explanations={
            "technical": (
                "Candidate and saved references were compared using weighted 64-bit "
                "difference and average perceptual hashes; this is not a trained model."
                if comparison["comparison_available"] else
                "Candidate image was decoded and hashed, but no reference comparison was performed."
            ),
            "plain_language": reason,
        },
        limitations=[
            "Perceptual hashes are heuristic signals, not a calibrated risk probability.",
            "Visual similarity does not prove impersonation or authenticity.",
        ],
        recommended_actions=[
            "Compare this image manually against an independently sourced official asset."
        ],
        model_source="perceptual_hashes",
    )
