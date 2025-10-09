"""Folder name parsing utilities."""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console

from src.models.chapter import ChapterInfo
from src.parsers.image_collector import collect_image_files

console = Console()


def parse_volume_chapter_from_folder(folder_name: str) -> tuple[str | None, str | None, str]:
    """
    Parse volume and chapter information from folder names using regex patterns.
    
    Args:
        folder_name: The folder name to parse
        
    Returns:
        tuple: (volume, chapter, title) where volume/chapter may be None if not found
    """
    # Pattern 1: "V1 Ch1 Title" or "Volume 1 Chapter 1 Title"
    pattern1 = r'(?:V|Volume)\s*(\d+)(?:\s+(?:Ch|Chapter)\s*(\d+))?(?:\s+(.+))?'
    match = re.match(pattern1, folder_name, re.IGNORECASE)
    if match:
        volume, chapter, title = match.groups()
        return volume, chapter, title or ""
    
    # Pattern 2: "Ch1 Title" or "Chapter 1 Title" (no volume)
    pattern2 = r'(?:Ch|Chapter)\s*(\d+)(?:\s+(.+))?'
    match = re.match(pattern2, folder_name, re.IGNORECASE)
    if match:
        chapter, title = match.groups()
        return None, chapter, title or ""
    
    # Pattern 3: Just numbers at the start "1 Title" or "01 Title"
    pattern3 = r'^(\d+)(?:\s+(.+))?'
    match = re.match(pattern3, folder_name)
    if match:
        number, title = match.groups()
        # Assume it's a chapter if no volume context
        return None, number, title or ""
    
    # Fallback: Extract any numbers found in the folder name
    numbers = re.findall(r'\d+', folder_name)
    if numbers:
        warning_msg = (
            f"[yellow]Warning: Using fallback parsing for folder '{folder_name}'. "
            f"Extracted numbers: {numbers}[/yellow]"
        )
        console.print(warning_msg)
        # Use first number as chapter, second as volume if available
        if len(numbers) >= 2:
            return numbers[1], numbers[0], folder_name
        else:
            return None, numbers[0], folder_name
    
    # No numbers found - use folder name as title
    warning_msg = (
        f"[yellow]Warning: No volume/chapter numbers found in '{folder_name}'. "
        f"Using folder name as title.[/yellow]"
    )
    console.print(warning_msg)
    return None, None, folder_name


def parse_chapter_info(chapter_folder: Path, volume_hint: str | None = None) -> ChapterInfo:
    """
    Parse a chapter folder and create ChapterInfo object.
    
    Args:
        chapter_folder: Path to the chapter folder
        volume_hint: Optional volume number from parent folder
        
    Returns:
        ChapterInfo: Parsed chapter information
    """
    folder_name = chapter_folder.name
    volume, chapter, title = parse_volume_chapter_from_folder(folder_name)
    
    # Use volume hint if no volume was parsed from folder name
    if volume is None and volume_hint is not None:
        volume = volume_hint
    
    # Collect image files from the chapter folder
    image_files = collect_image_files(chapter_folder)
    
    return ChapterInfo(
        volume=volume or "Unknown",
        chapter=chapter or "Unknown", 
        title=title,
        folder_path=chapter_folder,
        image_files=image_files
    )