"""Chapter information data model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ChapterInfo:
    """Information about a manga chapter."""

    volume: str
    chapter: str
    title: str
    folder_path: Path
    image_files: list[Path]