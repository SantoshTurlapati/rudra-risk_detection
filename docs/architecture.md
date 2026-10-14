# RudraShield AI — System Architecture

## Overview
RudraShield AI is a digital-risk-protection application for manual, evidence-oriented analysis of URLs, social-profile information, message content, and app metadata. It does not currently discover profiles or app listings from external platforms, execute APKs, or run continuous monitoring.

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND LAYER                         │
│   React 18 + TypeScript + Vite + Tailwind CSS + Recharts   │
│   (RudraShield AI user interface)                           │
└──────────────────────────────┬──────────────────────────────┘
                               │ JSON / REST via Axios
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND LAYER                          │
│               FastAPI (Python) REST Endpoints               │
│   - Auth & RBAC (/api/v1/auth)                              │
│   - Multimodal Analysis (/api/v1/analysis)                  │
│   - Brand Registry (/api/v1/brands)                         │
│   - Investigations & Cases (/api/v1/investigations)         │
│   - Threat Graph (/api/v1/threat-graph)                     │
│   - Safety Copilot (/api/v1/copilot)                        │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌──────────────────────────────┐    ┌─────────────────────────┐
│     AI DETECTION ENGINE      │    │     DATABASE LAYER      │
│ - RapidFuzz & Homoglyphs     │    │ - SQLAlchemy 2 ORM      │
│ - 64-bit dHash Image Percept │    │ - SQLite (Zero-Config)  │
│ - Local URL Heuristic Parser │    │ - PostgreSQL Ready      │
│ - Scam DNA Urgency Matcher   │    │ - Data Isolation Model  │
│ - Explainable Risk Scorer    │    └─────────────────────────┘
└──────────────────────────────┘
```

## Security & Multitenancy
- **Tenant Isolation**: All investigations, alerts, and brand profiles are scoped by `organization_id`.
- **Local URL Inspection**: The analyzer makes no DNS or HTTP requests. It reports private/reserved and ambiguous numeric host indicators for analyst review; it is not an SSRF-denial control for any future URL-fetching feature.
- **Explainable Scoring**: Transparent signal attribution (0–100 scale) divided into clear operational bands:
  - 0–24: Lower Risk
  - 25–49: Needs Review
  - 50–74: High Risk
  - 75–100: Critical Risk

## Persisted analysis and review provenance
- New investigation records label their origin as authenticated API-submitted evidence and record the submitting user and timestamp. This records who submitted the case; it does not prove an external source was independently checked.
- Review updates append disposition/risk/severity/note-change history into the existing findings JSON and organization audit log. False-positive transitions require a reason, while the submitted evidence is preserved.
- Campaign clustering currently returns possible, non-persistent suggestions only. It requires exact overlap in two separate stored evidence types and does not assert attribution or intent. Suggestions are limited to the 500 most recently updated cases per organization.

## Official image references
The additive `BrandImageReference` model uses separate SQLAlchemy metadata, so normal startup cannot create its table. A reviewable SQLite-only manual migration is at `backend/migrations/001_brand_image_references.sqlite.sql`; it was exercised only on a temporary isolated database and has not been applied to any application database. Authenticated organization-scoped API routes support upload, list, replace, remove, and comparison. Writes require an organization administrator. Upload bytes are decoded and validated before storage; private keys are generated, SHA-256 integrity is checked during comparison, and old references remain inactive after replacement/removal. Comparison uses existing perceptual hashing and remains an explicitly unverified heuristic; resemblance is not proof of impersonation or authenticity.

Storage is behind a `PrivateImageStorage` interface. The default backend is disabled. An optional filesystem adapter requires an operator-configured directory and a persistent backed-up mount; it is not assumed durable in production. No cloud object-store adapter or credentials are configured. The additive schema migration has not been run or approved, so existing application databases remain unchanged and the API reports the migration blocker until a reviewed migration is applied.
