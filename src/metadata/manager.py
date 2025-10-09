"""Metadata manager for JSON file operations."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TypedDict


class ChapterGroupData(TypedDict):
    """Type definition for chapter group data."""
    
    title: str
    volume: str
    groups: dict[str, str]
    last_updated: str


class MangaInfoData(TypedDict):
    """Type definition for manga info data."""
    
    title: str
    description: str
    artist: str
    author: str
    cover: str
    chapters: dict[str, ChapterGroupData]


class MetadataManager:
    """Manages manga metadata JSON files and operations."""

    def __init__(self, base_output_dir: Path | None = None) -> None:
        """Initialize MetadataManager.
        
        Args:
            base_output_dir: Base directory for manga metadata files
        """
        self.base_output_dir: Path = base_output_dir or Path("mangas")
        self.base_output_dir.mkdir(exist_ok=True)

    def load_manga_info(self, manga_title: str) -> MangaInfoData:
        """Load manga metadata from JSON file.
        
        Args:
            manga_title: Title of the manga
            
        Returns:
            Dictionary containing manga metadata
            
        Raises:
            FileNotFoundError: If metadata file doesn't exist
            json.JSONDecodeError: If JSON file is corrupted
            OSError: If file cannot be read due to permissions or I/O error
        """
        manga_dir = self.base_output_dir / manga_title
        info_file = manga_dir / "info.json"
        
        if not info_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {info_file}")
        
        try:
            with info_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                # Validate basic structure - we'll trust the JSON structure for now
                # In a production system, you'd want more thorough validation
                return data  # type: ignore[return-value]
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in metadata file {info_file}: {e.msg}",
                e.doc,
                e.pos
            ) from e
        except OSError as e:
            raise OSError(f"Failed to read metadata file {info_file}: {e}") from e

    def save_manga_info(self, manga_title: str, data: MangaInfoData) -> None:
        """Save manga metadata to JSON file with proper formatting.
        
        Args:
            manga_title: Title of the manga
            data: Manga metadata dictionary to save
            
        Raises:
            OSError: If file cannot be written due to permissions or I/O error
            TypeError: If data cannot be serialized to JSON
        """
        manga_dir = self.base_output_dir / manga_title
        manga_dir.mkdir(parents=True, exist_ok=True)
        
        info_file = manga_dir / "info.json"
        
        try:
            with info_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise OSError(f"Failed to write metadata file {info_file}: {e}") from e
        except TypeError as e:
            raise TypeError(f"Cannot serialize data to JSON: {e}") from e

    def update_chapter_data(
        self,
        manga_data: MangaInfoData,
        chapter_number: str,
        chapter_title: str,
        volume: str,
        album_url: str,
        group: str
    ) -> None:
        """Update chapter data with ImgChest URL and group information.
        
        Args:
            manga_data: Existing manga metadata dictionary
            chapter_number: Chapter number as string
            chapter_title: Title of the chapter
            volume: Volume number as string
            album_url: ImgChest album URL
            group: Selected scanlation group
        """
        # Initialize chapters dict if it doesn't exist
        if "chapters" not in manga_data:
            manga_data["chapters"] = {}
        
        # Get existing chapter data or create new
        existing_chapter = manga_data["chapters"].get(chapter_number)
        
        # Create chapter data structure
        existing_groups = existing_chapter["groups"].copy() if existing_chapter else {}
        
        # Convert ImgChest URL to proxy format
        proxy_url = self._convert_to_proxy_url(album_url)
        
        chapter_data: ChapterGroupData = {
            "title": chapter_title,
            "volume": volume,
            "last_updated": str(int(datetime.now().timestamp())),  # Unix timestamp as string
            "groups": existing_groups
        }
        
        # Add group and URL
        chapter_data["groups"][group] = proxy_url
        
        # Save updated chapter data
        manga_data["chapters"][chapter_number] = chapter_data

    def _convert_to_proxy_url(self, imgchest_url: str) -> str:
        """Convert ImgChest URL to proxy format.
        
        Args:
            imgchest_url: Original ImgChest URL (e.g., https://imgchest.com/p/vj4jew6w978)
            
        Returns:
            Proxy URL format (e.g., /proxy/api/imgchest/chapter/vj4jew6w978)
        """
        # Extract the album ID from the ImgChest URL
        # Format: https://imgchest.com/p/{album_id}
        if "/p/" in imgchest_url:
            album_id = imgchest_url.split("/p/")[-1]
            return f"/proxy/api/imgchest/chapter/{album_id}"
        
        # If URL format is unexpected, return as-is
        return imgchest_url

    def create_default_manga_metadata(
        self,
        title: str,
        description: str = "",
        artist: str = "",
        author: str = "",
        cover: str = ""
    ) -> MangaInfoData:
        """Create default manga metadata structure.
        
        Args:
            title: Manga title
            description: Manga description
            artist: Artist name
            author: Author name
            cover: Cover image URL
            
        Returns:
            Dictionary with default manga metadata structure
        """
        return {
            "title": title,
            "description": description,
            "artist": artist,
            "author": author,
            "cover": cover,
            "chapters": {}
        }

    def get_or_create_manga_info(self, manga_title: str) -> MangaInfoData:
        """Get existing manga info or create default structure.
        
        Args:
            manga_title: Title of the manga
            
        Returns:
            Dictionary containing manga metadata
        """
        try:
            return self.load_manga_info(manga_title)
        except FileNotFoundError:
            # Create default metadata if file doesn't exist
            return self.create_default_manga_metadata(manga_title)

    def manga_exists(self, manga_title: str) -> bool:
        """Check if manga metadata file exists.
        
        Args:
            manga_title: Title of the manga
            
        Returns:
            True if metadata file exists, False otherwise
        """
        manga_dir = self.base_output_dir / manga_title
        info_file = manga_dir / "info.json"
        return info_file.exists()