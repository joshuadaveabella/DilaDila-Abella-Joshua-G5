"""Validation for uploaded profile photos."""

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

MAX_PHOTO_BYTES = 2 * 1024 * 1024  # 2 MB
ALLOWED_PHOTO_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_PHOTO_PIXELS = 4000  # width and height


def validate_profile_photo(upload):
    if upload.size > MAX_PHOTO_BYTES:
        raise ValidationError(
            f"Photo is too large ({upload.size / 1024 / 1024:.1f} MB). The limit is 2 MB.", code="photo_too_large"
        )
    position = upload.tell() if hasattr(upload, "tell") else 0
    upload.seek(0)
    try:
        with Image.open(upload) as image:
            image_format = image.format
            width, height = image.size
    except (UnidentifiedImageError, OSError):
        raise ValidationError("This file is not a valid image.", code="invalid_image")
    finally:
        upload.seek(position)
    if image_format not in ALLOWED_PHOTO_FORMATS:
        raise ValidationError("Use a JPEG, PNG or WEBP photo.", code="invalid_photo_type")
    if width > MAX_PHOTO_PIXELS or height > MAX_PHOTO_PIXELS:
        raise ValidationError(f"Photo is too large in pixels (max {MAX_PHOTO_PIXELS}×{MAX_PHOTO_PIXELS}).", code="photo_dimensions")
