-- Explicit, additive migration for SQLite. Never run automatically at startup.
-- Review and back up the target database before applying with operator approval.
CREATE TABLE brand_image_references (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL
        REFERENCES organizations (id) ON DELETE CASCADE,
    brand_id VARCHAR(36) NOT NULL
        REFERENCES brand_profiles (id) ON DELETE CASCADE,
    storage_key VARCHAR(512) NOT NULL UNIQUE,
    content_hash VARCHAR(64) NOT NULL,
    media_type VARCHAR(32) NOT NULL,
    size_bytes INTEGER NOT NULL
        CONSTRAINT ck_brand_image_reference_size CHECK (size_bytes > 0),
    reference_status VARCHAR(16) NOT NULL DEFAULT 'active'
        CONSTRAINT ck_brand_image_reference_status
        CHECK (reference_status IN ('active', 'inactive')),
    created_by_id VARCHAR(36) NULL REFERENCES users (id) ON DELETE SET NULL,
    updated_by_id VARCHAR(36) NULL REFERENCES users (id) ON DELETE SET NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE INDEX ix_brand_image_references_organization_id
    ON brand_image_references (organization_id);
CREATE INDEX ix_brand_image_references_brand_id
    ON brand_image_references (brand_id);
CREATE INDEX ix_brand_image_reference_scope_status
    ON brand_image_references (organization_id, brand_id, reference_status);
