import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BrandImageReferenceBase(DeclarativeBase):
    """Metadata kept separate so application startup cannot create this table."""

    metadata = MetaData()


for parent_table in ("organizations", "brand_profiles", "users"):
    Table(
        parent_table,
        BrandImageReferenceBase.metadata,
        Column("id", String(36), primary_key=True),
    )


class BrandImageReference(BrandImageReferenceBase):
    __tablename__ = "brand_image_references"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_brand_image_reference_size"),
        CheckConstraint(
            "reference_status IN ('active', 'inactive')",
            name="ck_brand_image_reference_status",
        ),
        Index(
            "ix_brand_image_reference_scope_status",
            "organization_id",
            "brand_id",
            "reference_status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    brand_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("brand_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    media_type: Mapped[str] = mapped_column(String(32))
    size_bytes: Mapped[int] = mapped_column(Integer)
    reference_status: Mapped[str] = mapped_column(String(16), default="active")
    created_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


def is_missing_reference_table_error(error: Exception) -> bool:
    message = str(error).casefold()
    return "brand_image_references" in message and any(
        marker in message
        for marker in ("no such table", "does not exist", "undefined table")
    )
