from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class Permission(Base):
    """e.g. slug='location:read'. See docs/DATABASE.md."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
