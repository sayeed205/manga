"""Upload result data model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UploadResult:
    """Result of an image upload operation."""

    success: bool
    album_url: str | None
    album_id: str | None
    total_images: int
    error_message: str | None