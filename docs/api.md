# API Reference Documentation

All endpoints are versioned under `/api/v1`. OpenAPI interactive Swagger UI is available at `/docs`.

### Readiness
- `GET /health` — Executes a database query and returns HTTP 200 only when the application can reach the database; otherwise returns HTTP 503.

### Authentication
- `POST /api/v1/auth/login` — Sign in with email/username and password. Returns JWT token.
- `POST /api/v1/auth/register` — Create a new user account with default organization.
- `GET /api/v1/auth/me` — Get current logged-in user details.
- `POST /api/v1/auth/forgot-password` — Returns an explicit unavailable response until secure reset-token delivery is configured.
- `POST /api/v1/auth/reset-password` — Returns an explicit unavailable response; no password is changed.

### Detection & Multimodal Analysis
- `POST /api/v1/analysis/url` — Heuristically inspect URL structure for private or ambiguous numeric address forms, Punycode, deceptive naming, and sensitive paths. URLs are not fetched; this is not an SSRF-denial control or a safety verdict. URLs containing embedded credentials or control characters are rejected.
- `POST /api/v1/analysis/profile` — Analyze pasted handle, display name, profile URL, and bio; use verified registry entries only. No platform lookup is performed.
- `POST /api/v1/analysis/app` — Analyze user-supplied app name, package ID, publisher, description, and optional store URL against verified registry data. A submitted URL is screened locally without fetching it; no APK, store listing, or signing data is retrieved.
- `POST /api/v1/analysis/message` — Extract explainable scam-pattern evidence and inspect up to five embedded URLs locally without fetching them.
- `POST /api/v1/analysis/image` — Validate a PNG, JPEG, or WebP candidate and compare it with active saved references for an authorized brand when the additive reference table and private storage are configured. Similarity is a heuristic review signal, not proof of impersonation or authenticity. Missing schema/storage returns an explicit unavailable response.

Rule-only analysis responses identify `model_source: "rules"` and leave `confidence` unset. Scores are heuristic review indicators, not calibrated fraud probabilities. Results include evidence, limitations, and possible exact investigation matches; matches do not assert relationships.

### Brand Identity Registry
- `GET /api/v1/brands` — List all registered organization brand profiles.
- `POST /api/v1/brands` — Register new protected brand profile. Backend validation trims text, rejects blank names/control characters, normalizes domain names and HTTP(S) URLs, deduplicates domains/publishers/contact identifiers, validates social platform/handle pairs and app package identifiers, and preserves additional string metadata on social/app records. Submitted identifiers remain owner-provided claims.
- `PATCH /api/v1/brands/{id}` — Update organization-scoped brand metadata; invalid partial updates return HTTP 422 without changing stored data. Only an organization administrator can mark a brand as verified. Verification-status transitions are recorded in the organization audit log; this admin-marked status is not independent verification.
- `DELETE /api/v1/brands/{id}` — Remove a brand profile.

### Investigations & Cases
- `GET /api/v1/investigations` — List investigations with optional filters (`type`, `status`, `search`).
- `POST /api/v1/investigations` — Persist new case from findings.
- `GET /api/v1/investigations/{id}` — Get case dossier.
- `PATCH /api/v1/investigations/{id}` — Update status, risk score, severity, or analyst notes. Updates append actor/time/change history without copying note text into audit metadata. Marking a case as `False Positive` requires a reason; submitted evidence is preserved.

### Safety Copilot
- `POST /api/v1/copilot/chat` — Conversational security advice in English (`en`) or Telugu (`te`).

### Analytics & Reports
- `GET /api/v1/dashboard/stats` — Organization-scoped counts and activity derived from saved investigations, alerts, and campaigns. Location data is empty when no location evidence is stored.
- `GET /api/v1/campaigns/cluster-suggestions` — Returns non-persistent, organization-scoped possible groupings from saved case evidence. A suggestion requires exact overlap in at least two evidence types (for example, a URL domain and message-evidence fingerprint); a shared indicator alone does not create a group. No common ownership or malicious intent is inferred. Only the 500 most recently updated cases are considered.
- `GET /api/v1/threat-graph` — Organization-scoped stored entities and relationships plus saved investigation evidence. Explicit stored associations are marked `confirmed`; exact investigation matches are marked `possible`. A confirmed status describes the saved association, not independent attribution.
- `GET /api/v1/reports` — List formal investigation reports.
- `GET /api/v1/reports/{id}/download-csv` — Export saved case fields and findings as an authenticated CSV attachment.
- `GET /api/v1/settings` — Shows organization-scoped configuration and explicit unavailable states for unconfigured social-discovery and app-store providers.

No authorized external social or app-store providers are currently configured. Discovery results are not fabricated, and continuous monitoring is not implemented.

### Official reference image storage
The authenticated routes are `GET /api/v1/brands/{id}/image-references`, `POST` to add, `PUT /api/v1/brands/{id}/image-references/{reference_id}` to replace, and `DELETE` on that reference route to disable/remove it. Reads are organization-scoped; changes require an organization administrator. Upload validation decodes PNG/JPEG/WebP content, enforces 10MB and 40-million-pixel limits, ignores client MIME/extension for format decisions, and stores a generated key, SHA-256, detected media type, size, actor, and timestamps. The filesystem adapter independently checks decoded content against the declared media type; persisted keys are revalidated before reads or deletion. Replacement preserves prior metadata as inactive. Removed objects are not used for comparison. `BRAND_IMAGE_REVIEW_THRESHOLD` configures the heuristic review threshold from 0 to 100 (default 75); this is a review trigger, not a risk probability.

The additive SQLAlchemy model is deliberately registered with separate metadata: normal application startup does not create or migrate its table. A reviewable SQLite migration is provided at `backend/migrations/001_brand_image_references.sqlite.sql`; it creates a new `brand_image_references` table with organization/brand/user foreign keys, status/size checks, and lookup indexes. The migration is manual, SQLite-specific, and is not run at startup or by the test suite against an application database. It was validated against an isolated temporary database only. No schema migration has been run against any application database; owner approval and an operator-reviewed backup/restore plan are still required before applying it.

`BRAND_IMAGE_STORAGE_BACKEND=disabled` is the safe default. `local` with `BRAND_IMAGE_STORAGE_DIR` selects the private filesystem adapter, which restricts key format and file permissions but is durable only when an operator supplies a persistent, backed-up volume. No cloud object-storage adapter or credentials are configured; do not treat local disk as production-durable by default. An object-store implementation can be injected through the `PrivateImageStorage` interface after selecting an authorized provider, credentials, access policy, encryption, retention, and backup/restore behavior. The persisted references are user-submitted claims, not independently verified official assets.
