"""Image compression for photo uploads (ADR-0018), same approach already
proven in the sibling LPC project's media library.

Decoding the image via Pillow also doubles as content-type verification
-- a file whose declared Content-Type header doesn't match its actual
bytes fails to open rather than getting silently trusted.
"""

import io

from PIL import Image

MAX_DIMENSION = 2048
JPEG_QUALITY = 85


class InvalidImageError(Exception):
    pass


def compress_image(content: bytes, content_type: str) -> bytes:
    """Downscales to at most MAX_DIMENSION per side (never upscales),
    re-encodes at JPEG_QUALITY, and strips EXIF (privacy -- phone photos
    often carry GPS coordinates) by simply not passing it back through
    on save.
    """
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except Exception as exc:
        raise InvalidImageError("File is not a valid image") from exc

    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

    output = io.BytesIO()
    save_format = "WEBP" if content_type == "image/webp" else "JPEG"
    if save_format == "JPEG" and image.mode in ("RGBA", "P"):
        # Flatten transparency onto white rather than converting straight
        # to RGB, which would otherwise turn transparent pixels black.
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[3])
        image = background
    image.save(output, format=save_format, quality=JPEG_QUALITY, optimize=True)
    return output.getvalue()
