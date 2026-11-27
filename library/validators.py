"""Validation for uploaded phrase audio files."""

import os

from django.core.exceptions import ValidationError

MAX_AUDIO_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_AUDIO_EXTENSIONS = ("mp3", "wav", "ogg", "m4a")


def _looks_like(ext, head):
    """Check the first bytes of the file really match the claimed type (the name alone can be faked)."""
    if ext == "mp3":
        return head.startswith(b"ID3") or (len(head) > 1 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0)
    if ext == "wav":
        return head.startswith(b"RIFF") and head[8:12] == b"WAVE"
    if ext == "ogg":
        return head.startswith(b"OggS")
    if ext == "m4a":
        return head[4:8] == b"ftyp"
    return False


def validate_audio_file(upload):
    ext = os.path.splitext(upload.name)[1].lower().lstrip(".")
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise ValidationError(
            "Unsupported audio type. Upload an MP3, WAV, OGG or M4A file.", code="invalid_audio_type"
        )
    if upload.size > MAX_AUDIO_BYTES:
        raise ValidationError(
            f"Audio file is too large ({upload.size / 1024 / 1024:.1f} MB). The limit is 5 MB.", code="audio_too_large"
        )
    position = upload.tell() if hasattr(upload, "tell") else 0
    upload.seek(0)
    head = upload.read(16)
    upload.seek(position)
    if not _looks_like(ext, head):
        raise ValidationError("This file is not a valid audio file of the type its name says.", code="invalid_audio_content")
