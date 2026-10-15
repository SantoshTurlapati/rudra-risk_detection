# RudraShield AI
LINK:-https://rudrashield-frontend.onrender.com/dashboard
> **"Detect Deception. Expose Threats. Protect Digital Trust."**

RudraShield AI is a digital-risk-protection application for organization administrators, analysts, and people reviewing potentially deceptive URLs, profiles, messages, and mobile-app metadata. It provides manual, evidence-oriented workflows using local heuristic analysis of submitted information. Live social-platform and app-store discovery and continuous monitoring are unavailable.

---

## 1. Project Directory Structure

```
RudraShield AI/
|-- backend/
|   |-- app/
|   |   |-- ai/
|   |   |   |-- homoglyphs.py
|   |   |   |-- image_hasher.py
|   |   |   |-- image_validation.py
|   |   |   |-- name_matcher.py
|   |   |   |-- risk_engine.py
|   |   |   |-- scam_patterns.py
|   |   |   `-- url_safety.py
|   |   |-- api/
|   |   |   `-- v1/
|   |   |       |-- alerts.py
|   |   |       |-- analysis.py
|   |   |       |-- auth.py
|   |   |       |-- brand_images.py
|   |   |       |-- brands.py
|   |   |       |-- campaigns.py
|   |   |       |-- copilot.py
|   |   |       |-- dashboard.py
|   |   |       |-- deps.py
|   |   |       |-- investigations.py
|   |   |       |-- reports.py
|   |   |       |-- settings_router.py
|   |   |       `-- threat_graph.py
|   |   |-- core/
|   |   |   |-- config.py
|   |   |   `-- security.py
|   |   |-- db/
|   |   |   |-- brand_image_references.py
|   |   |   |-- models.py
|   |   |   |-- seed.py
|   |   |   `-- session.py
|   |   |-- providers/
|   |   |   |-- __init__.py
|   |   |   `-- discovery.py
|   |   |-- schemas/
|   |   |   `-- all_schemas.py
|   |   |-- storage/
|   |   |   |-- __init__.py
|   |   |   `-- brand_images.py
|   |   `-- main.py
|   |-- tests/
|   |   |-- conftest.py
|   |   |-- test_api.py
|   |   |-- test_brand_image_references.py
|   |   |-- test_detection.py
|   |   `-- test_providers.py
|   |-- migrations/
|   |   `-- 001_brand_image_references.sqlite.sql
|   |-- .dockerignore
|   |-- Dockerfile
|   `-- requirements.txt
|-- docs/
|   |-- ai-methodology.md
|   |-- api.md
|   |-- architecture.md
|   |-- audit-report.md
|   `-- phase1-readiness.md
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |   |-- BrandLogo.tsx
|   |   |   |-- RudraMascot.tsx
|   |   |   `-- ShieldGraphic.tsx
|   |   |-- context/
|   |   |   `-- AuthContext.tsx
|   |   |-- layouts/
|   |   |   `-- AppLayout.tsx
|   |   |-- pages/
|   |   |   |-- AppAnalysis.tsx
|   |   |   |-- CaseHistory.tsx
|   |   |   |-- CriticalAlerts.tsx
|   |   |   |-- Dashboard.tsx
|   |   |   |-- ForgotPassword.tsx
|   |   |   |-- Investigate.tsx
|   |   |   |-- Login.tsx
|   |   |   |-- Register.tsx
|   |   |   |-- Reports.tsx
|   |   |   |-- ResetPassword.tsx
|   |   |   |-- SafetyCopilot.tsx
|   |   |   |-- ScamDna.tsx
|   |   |   |-- Settings.tsx
|   |   |   |-- ThreatGraph.tsx
|   |   |   |-- ThreatIntelligence.tsx
|   |   |   `-- TrustedIdentity.tsx
|   |   |-- services/
|   |   |   `-- api.ts
|   |   |-- types/
|   |   |   `-- index.ts
|   |   |-- utils/
|   |   |   `-- apiErrorMessage.ts
|   |   |-- App.tsx
|   |   |-- index.css
|   |   `-- main.tsx
|   |-- Dockerfile
|   |-- index.html
|   |-- package.json
|   |-- package-lock.json
|   |-- postcss.config.js
|   |-- tailwind.config.js
|   |-- tsconfig.json
|   |-- tsconfig.node.json
|   |-- vite.config.ts
|   `-- nginx.conf
|-- .gitignore
|-- .env.example
|-- docker-compose.yml
|-- project-structure.txt
`-- README.md
```

This source-oriented tree omits local databases, credentials, user-provided images, caches, backup files, and generated build output.

---

## 2. Prerequisites

- **Python**: 3.11+ (Tested on Python 3.14)
- **Node.js**: v18+ (Tested on Node v24.19.0 / npm 11.17.0)
- **Database**: SQLite (built-in, zero-config default) or PostgreSQL 14+ (optional)

---

## 3. Installation & Setup

### A. Backend Setup

1. Open a terminal in the project directory:
   ```powershell
   cd "c:\RudraShield AI"
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv backend\venv
   .\backend\venv\Scripts\Activate.ps1
   ```

3. Install backend dependencies:
   ```powershell
   pip install -r backend\requirements.txt
   ```

4. Configure environment variables:
   ```powershell
   Copy-Item .env.example .env
   ```
   Replace `SECRET_KEY` with the output of `python -c "import secrets; print(secrets.token_hex(32))"`.
   For a local backend process, also set `$env:SECRET_KEY` to that value in the terminal before starting Uvicorn.

### B. Frontend Setup

1. Open a terminal in `frontend/`:
   ```powershell
   cd "c:\RudraShield AI\frontend"
   npm install
   ```

---

## 4. Running the Application

### Start Backend (Terminal 1)

```powershell
cd "c:\RudraShield AI"
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Base URL: `http://localhost:8000`
- Interactive Swagger Documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Start Frontend (Terminal 2)

```powershell
cd "c:\RudraShield AI\frontend"
npm run dev
```
- Web Application: `http://localhost:5173`

---

## 5. Automated Tests

Run backend unit and integration tests using pytest:
```powershell
cd "c:\RudraShield AI"
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\python.exe -m pytest backend\tests -q
```

Frontend type check and production build:
```powershell
cd "c:\RudraShield AI\frontend"
npm run build
```

No frontend automated test runner is configured. The build performs TypeScript validation before producing the Vite bundle.

---

## 6. Development-only Demo Seeds

Synthetic demo data is never inserted automatically when the application starts. To generate a local development dataset intentionally, run:

```powershell
cd "c:\RudraShield AI"
$env:PYTHONPATH="backend"
$env:RUDRASHIELD_DEMO_PASSWORD="replace-with-a-random-password-of-16-or-more-characters"
.\backend\venv\Scripts\python.exe -m app.db.seed --seed-demo
```

Use the explicit cleanup command only when you want to remove the demo records created by the seeder:

```powershell
.\backend\venv\Scripts\python.exe -m app.db.seed --clear-demo --confirm-clear-demo
```

The seed command requires an explicit development-only password of at least 16 characters, creates an unverified synthetic analyst and sample records, and must only be run against a disposable development database. These sample records are marked synthetic and must not be treated as live intelligence.

---

## 7. AI Detection Capabilities & Limitations

### Implemented local analysis

The application performs deterministic heuristic analysis on information a user submits; it does not independently collect or verify source data.

1. **Unicode homoglyph detection**: Detects supported Cyrillic and Greek lookalike character substitutions and invisible zero-width spaces.
2. **Fuzzy brand matching**: Uses RapidFuzz similarity and edit distance alongside configured brand names and authority/support terms.
3. **URL lexical checks**: Flags suspicious URL structure, Punycode, deceptive subdomains, and private or loopback IP indicators. Submitted URLs are not fetched.
4. **Scam-pattern extraction**: Identifies urgency/coercion, financial bait, credential harvesting, authority impersonation, and risky action prompts.
5. **Explainable heuristic scoring**: Combines available signals into an explicit 0–100 score with itemized attribution and recommended actions. This is not a calibrated probability; rule-only responses do not include a model-confidence estimate.
6. **Perceptual image hashing**: The local hash algorithm is implemented. Comparing an uploaded candidate with saved organization-submitted references requires the reference schema and private storage to be configured; similarity is a heuristic, not proof of impersonation or authenticity.
7. **Safety Copilot**: Provides keyword-triggered template guidance in English and Telugu (`te`) with cyber helpline information (1930 / cybercrime.gov.in). It does not analyze submitted messages or URLs, assess individual risk, or query live threat data.

### Unavailable or unconfigured capabilities

- **Live social-profile and app-store discovery** are unavailable. Provider interfaces exist, but no authorized provider is configured; no live provider integration has been tested.
- **Continuous monitoring** is not implemented. Analyses are initiated manually and inspect submitted information.
- **Trained ML/deep-learning detection** is unavailable. A lightweight model adapter contract exists, but no trained model or model artifact is installed or active.
- **Image-reference storage and comparison are not ready by default.** The API/UI path and a local private-storage adapter exist, but the reference schema requires its additive migration. Storage is disabled by default, and no durable private image store or cloud object-store adapter is configured.
- **Production deployment is not active or verified.** No production deployment has been performed.

### Additional product limitations

- Publisher-signature verification is unavailable.
- Campaign groupings are review suggestions computed from persisted case evidence. They are non-persistent, require at least two exact evidence types, and do not assert common ownership or malicious intent.
- Investigation records include authenticated-submission provenance and a review history. A false-positive transition requires a reason and preserves the original findings.
- Safety Copilot responses are fixed keyword-triggered guidance templates, not AI analysis; Scam DNA quick-test text and explicitly invoked demo-seed records are synthetic examples.
- Does not scan live private social network chats without authorized API keys.
- Password recovery is unavailable until secure reset-token validation and delivery are configured; the UI and API do not claim to change a password.
- Google and GitHub OAuth buttons are placeholders; neither provider is configured or used for authentication.
- URL and message inspections are local heuristics and do not fetch URLs or query live reputation sources. Message analysis inspects at most five distinct embedded URLs.
- Profile analysis accepts pasted handles, display names, profile URLs, and bios. Account-age, follower, activity, badge, and ownership data are unknown without a trusted platform integration.
- Rule-only analysis results have no model-confidence value. Risk scores are weighted heuristic indicators, not calibrated probabilities; manual review is required.
- Scoring is an intelligence-gathering aid and does not independently verify ownership or constitute a human judicial determination.
- Brand entries created by users are unverified by default. Only an organization administrator can mark an entry verified.

---

## 8. Optional Docker Deployment

Docker is optional; local development does not require Docker.

The Compose configuration requires a unique `SECRET_KEY` of at least 32 characters and stores SQLite at `backend/data/rudrashield.db`. It does not automatically use or merge the local backend default database (`backend/rudrashield.db`). Verify which existing database is authoritative before deployment; back up the selected file and do not remove or replace it.

### Free-tier deployment limitations (checked 2026-10-14)

No free-tier production architecture has been validated for this project. Render documents free static sites and web services, but its free web-service filesystem is ephemeral: local SQLite files and uploads can be lost on restart, redeploy, or spin-down. Render also documents free Postgres as limited to 1 GB and expiring 30 days after creation. These constraints make Render's free database or a local SQLite file on its free web service unsuitable as the sole durable production store. See [Render's free-instance limitations](https://render.com/docs/free).

Cloudflare R2 documents a free monthly allowance for standard object storage and requests, but object storage does not replace the application's relational database, and RudraShield AI does not currently integrate R2 for private images or evidence. See [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/). Do not treat a free object-storage allowance as a complete deployment solution or assume other providers' current free-tier terms without checking their official documentation.

Before a public deployment, select and test a durable database and private evidence-storage design, confirm backup/restore and retention, configure production `SECRET_KEY` and restrictive CORS, and exercise health checks and persistence across restart/redeploy. Live social/app discovery and continuous monitoring remain unavailable without authorized sources and a reliable worker/scheduler. No public deployment has been performed.

From PowerShell at the repository root:

```powershell
$env:SECRET_KEY = & python -c "import secrets; print(secrets.token_urlsafe(48))"
if (Test-Path -LiteralPath "backend\data\rudrashield.db") {
  $backup = "backend\data\rudrashield.db.predeploy-$(Get-Date -Format yyyyMMdd-HHmmss).bak"
  Copy-Item -LiteralPath "backend\data\rudrashield.db" -Destination $backup
}
docker compose config --quiet
docker compose up --build -d
Invoke-RestMethod "http://localhost:8000/health"
Invoke-WebRequest "http://localhost:5173/" -UseBasicParsing
```

Keep the generated secret in a protected secret manager for later container recreations, or in the current process environment for a one-time launch; do not commit it. Reuse the same secret across restarts and rotate it intentionally. The backend health endpoint must report database readiness and the frontend request must return HTTP 200 before considering deployment verified. Put a TLS-terminating reverse proxy or managed HTTPS load balancer in front of public production traffic.
