import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class Photo(Base):
    """Polymorphic photo attachment (ADR-0003, built in ADR-0018).
    `entity_id` is a UUID since every entity type this can point to
    (locations, competitors -- the only two with a real UI to upload
    from) uses a UUID PK, same reasoning as the photos/documents/reviews
    design in docs/DATABASE.md. `file_url` is an opaque, already-servable
    path (e.g. "/media/location/<uuid>.jpg") rather than a raw storage
    key, so swapping the storage backend later doesn't touch consumers.
    """

    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(500), nullable=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
