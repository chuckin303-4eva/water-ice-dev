"""Photo upload/list/delete (Phase 2 "Photos"; ADR-0018).

Local disk storage under settings.upload_dir, served back out via a
StaticFiles mount at /media (see app/main.py) -- same MVP decision
already made and proven in the sibling LPC project's media library, not
re-litigated here. Scoped to the two entity types that actually have a
detail panel to upload from: locations and competitors.
"""

import os
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.models.competitor import Competitor
from app.core.models.location import Location
from app.core.models.photo import Photo
from app.services import image_processing

_ENTITY_MODELS = {"location": Location, "competitor": Competitor}

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class UnsupportedEntityTypeError(Exception):
    pass


class EntityNotFoundError(Exception):
    pass


class UnsupportedFileTypeError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


def _validate_entity(db: Session, entity_type: str, entity_id: uuid.UUID) -> None:
    model = _ENTITY_MODELS.get(entity_type)
    if model is None:
        raise UnsupportedEntityTypeError(f"Unsupported entity_type: {entity_type}")
    if db.get(model, entity_id) is None:
        raise EntityNotFoundError(f"{entity_type} {entity_id} does not exist")


def upload_photo(
    db: Session,
    entity_type: str,
    entity_id: uuid.UUID,
    content: bytes,
    content_type: str,
    uploaded_by: int,
    caption: str | None = None,
    is_primary: bool = False,
) -> Photo:
    _validate_entity(db, entity_type, entity_id)

    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise UnsupportedFileTypeError(f"Unsupported file type: {content_type}")
    if len(content) > settings.max_upload_size_bytes:
        raise FileTooLargeError(
            f"File exceeds the {settings.max_upload_size_bytes // (1024 * 1024)} MB limit"
        )

    # Raises image_processing.InvalidImageError if the bytes don't
    # actually decode as an image, regardless of the declared
    # Content-Type -- decoding doubles as verification.
    compressed = image_processing.compress_image(content, content_type)
    extension = ".webp" if content_type == "image/webp" else ".jpg"

    entity_dir = os.path.join(settings.upload_dir, entity_type)
    os.makedirs(entity_dir, exist_ok=True)
    # Server-generated filename -- never trust the client's original
    # filename (path traversal, collisions).
    filename = f"{uuid.uuid4()}{extension}"
    with open(os.path.join(entity_dir, filename), "wb") as f:
        f.write(compressed)

    if is_primary:
        db.query(Photo).filter(
            Photo.entity_type == entity_type, Photo.entity_id == entity_id, Photo.is_primary.is_(True)
        ).update({"is_primary": False})

    photo = Photo(
        entity_type=entity_type,
        entity_id=entity_id,
        file_url=f"/media/{entity_type}/{filename}",
        caption=caption,
        uploaded_by=uploaded_by,
        is_primary=is_primary,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def list_photos(db: Session, entity_type: str, entity_id: uuid.UUID) -> list[Photo]:
    return (
        db.query(Photo)
        .filter(Photo.entity_type == entity_type, Photo.entity_id == entity_id)
        .order_by(Photo.is_primary.desc(), Photo.uploaded_at.desc())
        .all()
    )


def get_photo(db: Session, photo_id: uuid.UUID) -> Photo | None:
    return db.get(Photo, photo_id)


def delete_photo(db: Session, photo: Photo) -> None:
    file_path = os.path.join(settings.upload_dir, photo.entity_type, os.path.basename(photo.file_url))
    try:
        os.remove(file_path)
    except OSError:
        pass  # already gone -- don't fail the delete over a missing file
    db.delete(photo)
    db.commit()
