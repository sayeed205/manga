#!/usr/bin/env python3
"""
Manga Upload Script

A command-line tool for processing manga folder structures and uploading content to ImgChest.
Processes manga/volume/chapter/pages directory structures, uploads images in batches,
and generates JSON metadata files for manga readers.

Usage:
    uv run main.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

# Load environment variables from .env file
_ = load_dotenv()

# Initialize Rich console for output
console = Console()


@dataclass
class ChapterInfo:
    """Information about a manga chapter."""

    volume: str
    chapter: str
    title: str
    folder_path: Path
    image_files: list[Path]


@dataclass
class UploadResult:
    """Result of an image upload operation."""

    success: bool
    album_url: str | None
    album_id: str | None
    total_images: int
    error_message: str | None


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


def validate_environment() -> bool:
    """
    Validate that required environment variables are set.

    Returns:
        bool: True if environment is valid, False otherwise
    """
    api_key = os.getenv("IMGCHEST_API_KEY")
    if not api_key:
        console.print(
            "[red]Error: IMGCHEST_API_KEY not found in environment variables.[/red]"
        )
        console.print("Please create a .env file with your ImgChest API key:")
        console.print("IMGCHEST_API_KEY=your_api_key_here")
        return False

    console.print("[green]✓[/green] ImgChest API key loaded successfully")
    return True


def main():
    """Main entry point for the manga upload script."""
    console.print("[bold blue]Manga Upload Script[/bold blue]")
    console.print("Processing manga folders and uploading to ImgChest...\n")

    # Validate environment setup
    if not validate_environment():
        sys.exit(1)

    console.print(
        "[yellow]Script setup complete. Ready for implementation.[/yellow]"
    )

    # TODO: Implement main processing logic in subsequent tasks
    # This will include:
    # - Folder scanning and chapter detection
    # - ImgChest upload integration
    # - Metadata management
    # - Progress tracking


if __name__ == "__main__":
    main()
