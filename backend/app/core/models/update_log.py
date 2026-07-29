from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class UpdateLog(Base):
    """Append-only audit trail per ADR-0003 ("never overwrite historical
    information") -- entity_type/entity_id is the one deliberate
    polymorphic reference in this schema (see docs/DATABASE.md), scoped
    to this cross-cutting workflow table, not core domain data. entity_id
    is stored as text since it must hold both UUID (Location) and
    integer (future entities) primary keys.
    """

    __tablename__ = "update_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    field_name: Mapped[str] = mapped_column(String(150), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String, nullable=True)
    new_value: Mapped[str | None] = mapped_column(String, nullable=True)
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    change_source: Mapped[str] = mapped_column(String(30), nullable=False)
    # manual/import/system/verification
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
