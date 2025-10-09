"""Upload record tracking for manga chapters."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TypedDict


class UploadRecord(TypedDict):
    """Type definition for upload record data."""
    
    album_url: str
    album_id: str
    timestamp: str
    image_count: int
    group: str


class UploadRecordManager:
    """Manages upload records to track processed chapters and avoid duplicates."""

    def __init__(self, record_file: Path | None = None) -> None:
        """Initialize UploadRecordManager.
        
        Args:
            record_file: Path to the upload records JSON file
        """
        self.record_file: Path = record_file or Path("upload_records.json")
        self._records: dict[str, UploadRecord] = {}
        self._load_records()

    def _load_records(self) -> None:
        """Load existing upload records from JSON file."""
        if not self.record_file.exists():
            self._records = {}
            return
        
        try:
            with self.record_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                # Validate that loaded data is a dictionary
                if isinstance(data, dict):
                    self._records = data  # type: ignore[assignment]
                else:
                    self._records = {}
        except (json.JSONDecodeError, OSError) as e:
            # If file is corrupted or unreadable, start with empty records
            print(f"Warning: Could not load upload records from {self.record_file}: {e}")
            self._records = {}

    def _save_records(self) -> None:
        """Save upload records to JSON file.
        
        Raises:
            OSError: If file cannot be written due to permissions or I/O error
            TypeError: If records cannot be serialized to JSON
        """
        try:
            with self.record_file.open("w", encoding="utf-8") as f:
                json.dump(self._records, f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise OSError(f"Failed to write upload records to {self.record_file}: {e}") from e
        except TypeError as e:
            raise TypeError(f"Cannot serialize upload records to JSON: {e}") from e

    def record_upload(
        self,
        chapter_name: str,
        album_url: str,
        album_id: str,
        image_count: int,
        group: str
    ) -> None:
        """Record a successful upload.
        
        Args:
            chapter_name: Name/identifier of the chapter
            album_url: ImgChest album URL
            album_id: ImgChest album ID
            image_count: Number of images uploaded
            group: Scanlation group name
        """
        record: UploadRecord = {
            "album_url": album_url,
            "album_id": album_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "image_count": image_count,
            "group": group
        }
        
        self._records[chapter_name] = record
        self._save_records()

    def is_chapter_uploaded(self, chapter_name: str) -> bool:
        """Check if a chapter has already been uploaded.
        
        Args:
            chapter_name: Name/identifier of the chapter
            
        Returns:
            True if chapter has been uploaded, False otherwise
        """
        return chapter_name in self._records

    def get_upload_record(self, chapter_name: str) -> UploadRecord | None:
        """Get upload record for a specific chapter.
        
        Args:
            chapter_name: Name/identifier of the chapter
            
        Returns:
            Upload record if exists, None otherwise
        """
        return self._records.get(chapter_name)

    def get_all_records(self) -> dict[str, UploadRecord]:
        """Get all upload records.
        
        Returns:
            Dictionary of all upload records
        """
        return self._records.copy()

    def remove_record(self, chapter_name: str) -> bool:
        """Remove an upload record.
        
        Args:
            chapter_name: Name/identifier of the chapter
            
        Returns:
            True if record was removed, False if it didn't exist
        """
        if chapter_name in self._records:
            del self._records[chapter_name]
            self._save_records()
            return True
        return False

    def confirm_reupload(self, chapter_name: str) -> bool:
        """Ask user for confirmation to re-upload an existing chapter.
        
        Args:
            chapter_name: Name/identifier of the chapter
            
        Returns:
            True if user confirms re-upload, False otherwise
        """
        record = self.get_upload_record(chapter_name)
        if not record:
            return True  # No existing record, proceed with upload
        
        print(f"\nChapter '{chapter_name}' has already been uploaded:")
        print(f"  URL: {record['album_url']}")
        print(f"  Group: {record['group']}")
        print(f"  Images: {record['image_count']}")
        print(f"  Date: {record['timestamp']}")
        
        while True:
            response = input("Do you want to re-upload this chapter? (y/n): ").lower().strip()
            if response in ('y', 'yes'):
                return True
            elif response in ('n', 'no'):
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")

    def get_upload_summary(self) -> dict[str, int]:
        """Get summary statistics of uploads.
        
        Returns:
            Dictionary with upload statistics
        """
        if not self._records:
            return {"total_chapters": 0, "total_images": 0, "unique_groups": 0}
        
        total_images = sum(record["image_count"] for record in self._records.values())
        unique_groups = len(set(record["group"] for record in self._records.values()))
        
        return {
            "total_chapters": len(self._records),
            "total_images": total_images,
            "unique_groups": unique_groups
        }