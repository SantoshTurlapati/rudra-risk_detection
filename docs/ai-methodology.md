# AI and Detection Methodology

RudraShield currently uses deterministic validation and explainable rules. There
is no trained machine-learning or deep-learning model, model artifact, or live
threat-intelligence feed configured. Results report `model_source: "rules"` and
leave model confidence unset rather than presenting a heuristic certainty as a
probability.

## 1. Brand Name and Profile Signals

- Name matching uses RapidFuzz similarity, edit distance, configured brand
  names, and authority/support terms.
- Unicode normalization detects supported Cyrillic/Greek lookalikes and
  invisible characters.
- Profile analysis accepts pasted handles, display names, profile URLs, and
  bios. A selected brand is used for official comparisons only when its
  registry entry is verified.
- Profile URLs and up to five distinct URLs in the bio are inspected locally.
- Account age, followers, posting activity, platform badges, and ownership are
  unknown unless supplied by a future trusted integration; the application
  does not invent or retrieve those values.

## 2. Scam-Message Signals

Rule patterns cover urgency/coercion, financial bait, credential harvesting,
authority impersonation, and risky action prompts. Repeated matches in one
category contribute that category's score once. Evidence excerpts are returned
with the matched category. English-language patterns are configured; other
language variants may not be detected.

Message input is limited to 10,000 characters. URLs are removed from the text
pattern pass, extracted with a five-URL limit, and passed separately to the URL
analyzer. URL targets are never fetched.

## 3. URL Inspection

- Validates HTTP/HTTPS URL structure, host labels, and IP literals.
- Rejects embedded credentials and control characters, and flags legacy
  ambiguous numeric host forms that some clients may interpret as IP addresses.
- Converts internationalized hostnames to IDNA ASCII before inspection and flags
  Punycode labels.
- Flags loopback, private, link-local, and reserved IPs; suspicious TLDs;
  deceptive embedded domain text; excessive subdomains; brand-token mismatches;
  phishing-related paths/queries; non-HTTPS URLs; and configured URL shorteners.
- Shortened links are not expanded. No DNS, HTTP, or reputation lookup is made.
- Findings are heuristic review indicators, not a verdict about a site.

## 4. Shared Risk Aggregation

The scorer uses configurable modality weights in
`backend/app/ai/risk_engine.py`: name 25, image 25, URL 30, publisher mismatch
20, scam patterns 15, optional local model 35, and a capped multimodal
correlation bonus of 15.

For available positive-risk modalities, the weighted mean is computed from each
modality's 0–100 signal and its configured weight. A correlation bonus is added
only when distinct modalities independently produce the specified signals; the
final score is clamped to 0–100. Repeated patterns within one text category are
not separately weighted. Bands remain aligned to the existing thresholds:
0–24 lower risk, 25–49 needs review, 50–74 high risk, and 75–100 critical risk.

The score is not a calibrated probability. `confidence` is `null` for
rule-only results. The optional `TextRiskModel` protocol and validated model
signal input provide an adapter point for a future local classifier; no model
loader or trained model is present or activated. Automated results require
human review and independent verification.

## 5. Image Comparison

When the additive reference schema and private storage are configured, the API
compares a candidate only with active references belonging to the selected
organization's brand. The comparison uses weighted dHash and aHash similarity
and exposes per-reference similarity and a review threshold; neither is a
calibrated probability. Similarity does not prove impersonation or authenticity,
and stored references are organization-submitted claims rather than
independently verified assets. When no valid reference exists, or the schema
and storage are unavailable, the API reports that comparison was not performed.
No application database currently has the reference table, and no production
durable storage provider is configured.

## 6. Mobile App Metadata

App analysis evaluates only user-supplied app name, package identifier,
developer/publisher text, description, and optional store URL. The URL is
screened locally by the URL heuristic and is never fetched. Registry package
and publisher comparisons use only the selected admin-marked verified brand
entry; this is a configured-registry comparison, not independent publisher or
store verification. No APK is executed, and no live app-store listing or
signing certificate is retrieved.

## 7. Persistence and Investigations

Analysis endpoints do not persist submitted content automatically. Analysts can
choose the existing “Save to Case Registry” action to save the response with its
evidence and limitations through the existing investigation API. No automatic
relationships between unrelated records are asserted.
