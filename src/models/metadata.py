"""Manga metadata data model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MangaMetadata:
    """Manga metadata structure."""

    title: str
    description: str
    artist: str
    author: str
    cover: str
    groups: list[str]
    chapters: dict[str, object]