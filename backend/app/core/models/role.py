from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class Role(Base):
    """organization_id is nullable for system-wide roles. See docs/DATABASE.md."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
