"""Main manga processing orchestration."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import final

from rich.console import Console

from src.metadata.manager import MetadataManager, MangaInfoData
from src.models.chapter import ChapterInfo
from src.parsers.folder_parser import parse_chapter_info, parse_volume_chapter_from_folder
from src.parsers.manga_info import load_manga_info_from_folder
from src.progress.tracker import ProgressTracker, ChapterProgressContext
from src.selectors.group_selector import GroupSelector
from src.uploaders.imgchest import ImgChestUploader


@final
class MangaProcessor:
    """Main orchestrator for processing manga folders and uploading to ImgChest."""

    def __init__(
        self,
        base_manga_dir: Path | None = None,
        output_dir: Path | None = None,
        console: Console | None = None,
    ) -> None:
        """Initialize the manga processor.
        
        Args:
            base_manga_dir: Base directory containing manga folders
            output_dir: Output directory for metadata files
            console: Rich console instance
        """
        self.base_manga_dir = base_manga_dir or Path.cwd()
        self.console = console or Console()
        
        # Initialize components
        self.metadata_manager = MetadataManager(output_dir)
        self.progress_tracker = ProgressTracker(self.console, output_dir)
        self.group_selector = GroupSelector()
        self.uploader = ImgChestUploader()
        
        # Processing statistics
        self.processed_chapters = 0
        self.failed_chapters = 0

    def scan_for_chapters(self, manga_folder: Path) -> list[ChapterInfo]:
        """Scan manga folder structure and identify chapters.
        
        Args:
            manga_folder: Path to the manga folder
            
        Returns:
            List of ChapterInfo objects for found chapters
        """
        chapters: list[ChapterInfo] = []
        
        if not manga_folder.exists() or not manga_folder.is_dir():
            self.progress_tracker.display_warning(
                f"Manga folder not found or not a directory: {manga_folder}"
            )
            return chapters
        
        self.progress_tracker.display_info(f"Scanning folder: {manga_folder}")
        
        try:
            # Get all subdirectories with error handling
            try:
                all_folders = [f for f in manga_folder.iterdir() if f.is_dir()]
            except PermissionError as e:
                self.progress_tracker.display_error(
                    f"Permission denied accessing folder {manga_folder}: {e}"
                )
                return chapters
            except OSError as e:
                self.progress_tracker.display_error(
                    f"OS error accessing folder {manga_folder}: {e}"
                )
                return chapters
            
            if not all_folders:
                self.progress_tracker.display_warning(
                    f"No subdirectories found in {manga_folder}"
                )
                return chapters
            
            # Look for volume folders first
            volume_folders = [
                f for f in all_folders 
                if self._looks_like_volume_folder(f.name)
            ]
            
            if volume_folders:
                # Process volume-based structure
                self.progress_tracker.display_info(
                    f"Found {len(volume_folders)} volume folders"
                )
                for volume_folder in sorted(volume_folders):
                    try:
                        volume_num, _, _ = parse_volume_chapter_from_folder(volume_folder.name)
                        volume_chapters = self._scan_volume_folder(volume_folder, volume_num)
                        chapters.extend(volume_chapters)
                    except Exception as e:
                        self.progress_tracker.display_error(
                            f"Error scanning volume folder {volume_folder}: {e}",
                            e
                        )
                        continue
            else:
                # Process flat chapter structure (no volumes)
                chapter_folders = [
                    f for f in all_folders
                    if self._looks_like_chapter_folder(f.name)
                ]
                
                if not chapter_folders:
                    # If no obvious chapter folders, treat all folders as potential chapters
                    self.progress_tracker.display_warning(
                        "No obvious chapter folders found, treating all folders as chapters"
                    )
                    chapter_folders = all_folders
                
                self.progress_tracker.display_info(
                    f"Found {len(chapter_folders)} chapter folders"
                )
                
                for chapter_folder in sorted(chapter_folders):
                    try:
                        chapter_info = parse_chapter_info(chapter_folder)
                        if chapter_info.image_files:
                            chapters.append(chapter_info)
                        else:
                            self.progress_tracker.display_warning(
                                f"No images found in chapter folder: {chapter_folder}"
                            )
                    except Exception as e:
                        self.progress_tracker.display_error(
                            f"Error parsing chapter folder {chapter_folder}: {e}",
                            e
                        )
                        continue
            
        except Exception as e:
            self.progress_tracker.display_error(
                f"Unexpected error scanning manga folder {manga_folder}: {e}",
                e
            )
            return chapters
        
        self.progress_tracker.display_info(f"Found {len(chapters)} chapters to process")
        return chapters

    def _scan_volume_folder(self, volume_folder: Path, volume_hint: str | None) -> list[ChapterInfo]:
        """Scan a volume folder for chapters.
        
        Args:
            volume_folder: Path to the volume folder
            volume_hint: Volume number hint from folder name
            
        Returns:
            List of ChapterInfo objects for chapters in this volume
        """
        chapters: list[ChapterInfo] = []
        
        try:
            # Check folder accessibility
            if not os.access(volume_folder, os.R_OK):
                self.progress_tracker.display_error(
                    f"No read permission for volume folder: {volume_folder}"
                )
                return chapters
            
            try:
                chapter_folders = [
                    f for f in volume_folder.iterdir()
                    if f.is_dir()
                ]
            except PermissionError as e:
                self.progress_tracker.display_error(
                    f"Permission denied accessing volume folder {volume_folder}: {e}"
                )
                return chapters
            except OSError as e:
                self.progress_tracker.display_error(
                    f"OS error accessing volume folder {volume_folder}: {e}"
                )
                return chapters
            
            if not chapter_folders:
                self.progress_tracker.display_warning(
                    f"No chapter folders found in volume: {volume_folder}"
                )
                return chapters
            
            for chapter_folder in sorted(chapter_folders):
                try:
                    chapter_info = parse_chapter_info(chapter_folder, volume_hint)
                    if chapter_info.image_files:
                        chapters.append(chapter_info)
                    else:
                        self.progress_tracker.display_warning(
                            f"No images found in chapter folder: {chapter_folder}"
                        )
                except Exception as e:
                    self.progress_tracker.display_error(
                        f"Error parsing chapter folder {chapter_folder}: {e}",
                        e
                    )
                    continue
        
        except Exception as e:
            self.progress_tracker.display_error(
                f"Unexpected error scanning volume folder {volume_folder}: {e}",
                e
            )
        
        return chapters

    def _looks_like_volume_folder(self, folder_name: str) -> bool:
        """Check if folder name looks like a volume folder.
        
        Args:
            folder_name: Name of the folder
            
        Returns:
            True if it looks like a volume folder
        """
        volume_keywords = ["volume", "vol", "v"]
        name_lower = folder_name.lower()
        return any(keyword in name_lower for keyword in volume_keywords)

    def _looks_like_chapter_folder(self, folder_name: str) -> bool:
        """Check if folder name looks like a chapter folder.
        
        Args:
            folder_name: Name of the folder
            
        Returns:
            True if it looks like a chapter folder
        """
        chapter_keywords = ["chapter", "ch", "c"]
        name_lower = folder_name.lower()
        return any(keyword in name_lower for keyword in chapter_keywords) or folder_name.isdigit()

    def _save_progress_checkpoint(self, manga_data: MangaInfoData, manga_title: str) -> None:
        """Save progress checkpoint to prevent data loss.
        
        Args:
            manga_data: Current manga metadata
            manga_title: Title of the manga
        """
        try:
            self.metadata_manager.save_manga_info(manga_title, manga_data)
        except Exception as e:
            # Log but don't raise - this is just a checkpoint
            self.progress_tracker.display_warning(
                f"Failed to save progress checkpoint for '{manga_title}': {e}"
            )

    def process_manga_folder(self, manga_folder: Path) -> None:
        """Process a complete manga folder with all its chapters.
        
        Args:
            manga_folder: Path to the manga folder to process
        """
        manga_title = manga_folder.name
        
        # Validate manga folder exists and is accessible
        if not manga_folder.exists():
            self.progress_tracker.display_error(
                f"Manga folder does not exist: {manga_folder}"
            )
            return
        
        if not manga_folder.is_dir():
            self.progress_tracker.display_error(
                f"Path is not a directory: {manga_folder}"
            )
            return
        
        try:
            # Check folder permissions
            if not os.access(manga_folder, os.R_OK):
                self.progress_tracker.display_error(
                    f"No read permission for manga folder: {manga_folder}"
                )
                return
        except Exception as e:
            self.progress_tracker.display_warning(
                f"Could not check permissions for {manga_folder}: {e}"
            )
        
        try:
            # Load manga info from info.json/info.txt in the input folder
            try:
                manga_info = load_manga_info_from_folder(manga_folder)
                manga_title = manga_info['title']  # Use title from info file
                self.progress_tracker.set_current_manga(manga_title)
                self.progress_tracker.display_info(f"Processing manga: {manga_title}")
            except Exception as e:
                self.progress_tracker.display_warning(
                    f"Failed to load manga info from {manga_folder}: {e}. Using folder name."
                )
                from src.parsers.manga_info import MangaInfoDict
                manga_info: MangaInfoDict = {
                    'title': manga_title,
                    'description': '',
                    'artist': '',
                    'author': '',
                    'cover': '',
                    'groups': []
                }
            
            # Scan for chapters with error handling
            try:
                chapters = self.scan_for_chapters(manga_folder)
            except Exception as e:
                self.progress_tracker.display_error(
                    f"Failed to scan chapters in {manga_folder}: {e}",
                    e
                )
                return
            
            if not chapters:
                self.progress_tracker.display_warning(
                    f"No chapters found in {manga_folder}"
                )
                return
            
            # Load or create manga metadata with error handling
            try:
                manga_data = self.metadata_manager.get_or_create_manga_info(manga_title)
                
                # Update manga metadata with info from input folder
                manga_data['title'] = manga_info['title']
                manga_data['description'] = manga_info['description']
                manga_data['artist'] = manga_info['artist']
                manga_data['author'] = manga_info['author']
                manga_data['cover'] = manga_info['cover']
                
            except Exception as e:
                self.progress_tracker.display_error(
                    f"Failed to load/create metadata for '{manga_title}': {e}",
                    e
                )
                return
            
            # Get available groups from input info or use existing metadata
            available_groups = manga_info['groups']
            if not available_groups:
                # Fall back to existing metadata groups (if they exist from old format)
                available_groups = manga_data.get("groups", [])
            
            if not available_groups:
                self.progress_tracker.display_warning(
                    f"No groups defined for manga '{manga_title}'. Using default group."
                )
                available_groups = ["Default"]
            
            # Remove groups field from manga_data if it exists (old format cleanup)
            if "groups" in manga_data:
                del manga_data["groups"]
            
            # Process each chapter with comprehensive error handling
            successful_chapters = 0
            failed_chapters_local = 0
            
            with self.progress_tracker.track_chapter_processing(len(chapters)) as progress:
                for chapter_info in chapters:
                    try:
                        self._process_single_chapter(
                            chapter_info, manga_data, available_groups, progress, manga_title
                        )
                        successful_chapters += 1
                        self.processed_chapters += 1
                        
                        # Save progress checkpoint every 5 chapters
                        if successful_chapters % 5 == 0:
                            self._save_progress_checkpoint(manga_data, manga_title)
                        
                    except KeyboardInterrupt:
                        self.progress_tracker.display_warning(
                            "Processing interrupted by user. Saving progress..."
                        )
                        self._save_progress_checkpoint(manga_data, manga_title)
                        raise
                    except Exception as e:
                        failed_chapters_local += 1
                        self.failed_chapters += 1
                        
                        # Provide detailed error information
                        error_details = f"Chapter: {chapter_info.chapter}, Folder: {chapter_info.folder_path}"
                        self.progress_tracker.display_error(
                            f"Failed to process chapter {chapter_info.chapter}: {e}",
                            e
                        )
                        self.progress_tracker.display_info(f"Error details: {error_details}")
                        
                        progress.update(advance=1, description=f"Failed: {chapter_info.chapter}")
                        
                        # Continue processing other chapters
                        continue
            
            # Final metadata save with error handling
            try:
                self.metadata_manager.save_manga_info(manga_title, manga_data)
                self.progress_tracker.display_success(
                    f"Updated metadata for '{manga_title}' "
                    + f"({successful_chapters} successful, {failed_chapters_local} failed)"
                )
            except Exception as e:
                self.progress_tracker.display_error(
                    f"Failed to save final metadata for '{manga_title}': {e}",
                    e
                )
                # Try to save a backup
                try:
                    backup_path = Path(f"backup_{manga_title}_metadata.json")
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        json.dump(manga_data, f, indent=2, ensure_ascii=False)
                    self.progress_tracker.display_info(
                        f"Saved metadata backup to: {backup_path}"
                    )
                except Exception as backup_e:
                    self.progress_tracker.display_error(
                        f"Failed to save metadata backup: {backup_e}"
                    )
        
        except KeyboardInterrupt:
            self.progress_tracker.display_warning(
                f"Processing of '{manga_title}' interrupted by user"
            )
            raise
        except Exception as e:
            self.progress_tracker.display_error(
                f"Critical error processing manga folder {manga_folder}: {e}",
                e
            )
            # Don't re-raise here to allow processing of other manga folders
            self.failed_chapters += 1

    def _process_single_chapter(
        self,
        chapter_info: ChapterInfo,
        manga_data: MangaInfoData,
        available_groups: list[str],
        progress: ChapterProgressContext,
        manga_title: str,
    ) -> None:
        """Process a single chapter with upload and metadata update.
        
        Args:
            chapter_info: Information about the chapter
            manga_data: Manga metadata dictionary
            available_groups: List of available groups
            progress: Progress context for updates
            manga_title: Title of the manga
        """
        chapter_key = chapter_info.chapter
        progress.set_description(f"Processing: {chapter_key}")
        
        # Validate chapter has images
        if not chapter_info.image_files:
            self.progress_tracker.display_warning(
                f"Chapter {chapter_key} has no images, skipping"
            )
            progress.update(advance=1, description=f"Skipped (no images): {chapter_key}")
            return
        
        # Validate image files exist
        missing_files = [
            img for img in chapter_info.image_files 
            if not img.exists()
        ]
        if missing_files:
            self.progress_tracker.display_warning(
                f"Chapter {chapter_key} has {len(missing_files)} missing image files"
            )
            for missing_file in missing_files[:3]:  # Show first 3 missing files
                self.progress_tracker.display_warning(f"  Missing: {missing_file}")
            if len(missing_files) > 3:
                self.progress_tracker.display_warning(f"  ... and {len(missing_files) - 3} more")
            
            # Remove missing files from the list
            chapter_info.image_files = [
                img for img in chapter_info.image_files 
                if img.exists()
            ]
            
            if not chapter_info.image_files:
                self.progress_tracker.display_warning(
                    f"Chapter {chapter_key} has no valid images after filtering, skipping"
                )
                progress.update(advance=1, description=f"Skipped (no valid images): {chapter_key}")
                return
        
        # Check if chapter was already uploaded
        if self.progress_tracker.is_chapter_uploaded(chapter_key):
            try:
                if not self.progress_tracker.confirm_reupload(chapter_info):
                    progress.update(advance=1, description=f"Skipped: {chapter_key}")
                    return
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.progress_tracker.display_error(
                    f"Error during reupload confirmation for {chapter_key}: {e}"
                )
                progress.update(advance=1, description=f"Skipped (confirmation error): {chapter_key}")
                return
        
        # Select group for this chapter
        try:
            selected_group = self.group_selector.select_group_for_chapter(
                available_groups, f"{chapter_info.volume}-{chapter_key} ({chapter_info.title})"
            )
        except KeyboardInterrupt:
            raise
        except Exception as e:
            self.progress_tracker.display_error(
                f"Group selection failed for {chapter_key}: {e}",
                e
            )
            raise RuntimeError(f"Group selection failed: {e}") from e
        
        # Save progress before upload (in case of critical error during upload)
        try:
            self._save_progress_checkpoint(manga_data, manga_title)
        except Exception as e:
            self.progress_tracker.display_warning(
                f"Failed to save progress checkpoint: {e}"
            )
        
        # Upload chapter images with retry logic
        progress.set_description(f"Uploading: {chapter_key}")
        
        def batch_progress_callback(_current_batch: int, _total_batches: int) -> None:
            """Callback for batch upload progress."""
            # This could be enhanced to show batch progress within the chapter progress
            pass
        
        upload_result = None
        max_upload_retries = 2
        
        for attempt in range(max_upload_retries):
            try:
                upload_result = self.uploader.upload_chapter_images(
                    chapter_info.image_files,
                    f"{chapter_info.volume}-{chapter_key} - {chapter_info.title}",
                    batch_progress_callback
                )
                break  # Success, exit retry loop
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                if attempt < max_upload_retries - 1:
                    self.progress_tracker.display_warning(
                        f"Upload attempt {attempt + 1} failed for {chapter_key}, retrying: {e}"
                    )
                    continue
                else:
                    self.progress_tracker.display_error(
                        f"All upload attempts failed for {chapter_key}: {e}",
                        e
                    )
                    raise RuntimeError(f"Upload failed after {max_upload_retries} attempts: {e}") from e
        
        if not upload_result or not upload_result.success:
            error_msg = upload_result.error_message if upload_result else "Unknown upload error"
            self.progress_tracker.display_error(
                f"Upload failed for {chapter_key}: {error_msg}"
            )
            raise RuntimeError(f"Upload failed: {error_msg}")
        
        # Update metadata with upload information
        try:
            self.metadata_manager.update_chapter_data(
                manga_data,
                chapter_info.chapter,
                chapter_info.title,
                chapter_info.volume,
                upload_result.album_url or "",
                selected_group
            )
        except Exception as e:
            self.progress_tracker.display_error(
                f"Failed to update metadata for {chapter_key}: {e}",
                e
            )
            # Don't raise here - upload succeeded, just metadata update failed
            # We'll try to save it later in the main process
        
        # Record the upload
        try:
            self.progress_tracker.record_upload(
                chapter_info, upload_result, selected_group
            )
        except Exception as e:
            self.progress_tracker.display_warning(
                f"Failed to record upload for {chapter_key}: {e}"
            )
            # Don't raise here - upload succeeded, just record keeping failed
        
        progress.update(advance=1, description=f"Completed: {chapter_info.volume}-{chapter_key}")
        self.progress_tracker.display_success(
            f"Uploaded {chapter_info.volume}-{chapter_key}: {upload_result.album_url}"
        )

    def process_all_manga_folders(self, base_dir: Path | None = None) -> None:
        """Process all manga folders in the base directory.
        
        Args:
            base_dir: Base directory to scan for manga folders
        """
        scan_dir = base_dir or self.base_manga_dir
        
        # Validate base directory
        if not scan_dir.exists():
            self.progress_tracker.display_error(
                f"Base directory does not exist: {scan_dir}"
            )
            return
        
        if not scan_dir.is_dir():
            self.progress_tracker.display_error(
                f"Base path is not a directory: {scan_dir}"
            )
            return
        
        try:
            # Check directory permissions
            if not os.access(scan_dir, os.R_OK):
                self.progress_tracker.display_error(
                    f"No read permission for base directory: {scan_dir}"
                )
                return
        except Exception as e:
            self.progress_tracker.display_warning(
                f"Could not check permissions for {scan_dir}: {e}"
            )
        
        try:
            # Find potential manga folders with error handling
            try:
                all_items = list(scan_dir.iterdir())
            except PermissionError as e:
                self.progress_tracker.display_error(
                    f"Permission denied accessing base directory {scan_dir}: {e}"
                )
                return
            except OSError as e:
                self.progress_tracker.display_error(
                    f"OS error accessing base directory {scan_dir}: {e}"
                )
                return
            
            manga_folders = [
                f for f in all_items
                if f.is_dir() and not f.name.startswith('.') and not f.name.startswith('__')
            ]
            
            if not manga_folders:
                self.progress_tracker.display_warning(
                    f"No manga folders found in {scan_dir}"
                )
                return
            
            self.progress_tracker.display_info(
                f"Found {len(manga_folders)} potential manga folders"
            )
            
            # Process each manga folder with comprehensive error handling
            processed_manga = 0
            failed_manga = 0
            
            for i, manga_folder in enumerate(manga_folders, 1):
                try:
                    self.progress_tracker.display_info(
                        f"Processing manga {i}/{len(manga_folders)}: {manga_folder.name}"
                    )
                    
                    self.process_manga_folder(manga_folder)
                    processed_manga += 1
                    
                except KeyboardInterrupt:
                    self.progress_tracker.display_warning(
                        "Processing interrupted by user. Saving final summary..."
                    )
                    break
                except Exception as e:
                    failed_manga += 1
                    self.progress_tracker.display_error(
                        f"Failed to process manga folder {manga_folder}: {e}",
                        e
                    )
                    # Continue with next manga folder
                    continue
            
            # Display final summary
            self.progress_tracker.display_info(
                f"Processing complete: {processed_manga} manga processed, {failed_manga} failed"
            )
            self.progress_tracker.display_upload_summary(
                self.processed_chapters, self.failed_chapters
            )
            
        except Exception as e:
            self.progress_tracker.display_error(
                f"Critical error during batch processing: {e}",
                e
            )
            # Still try to show summary of what was processed
            self.progress_tracker.display_upload_summary(
                self.processed_chapters, self.failed_chapters
            )

    def test_connections(self) -> bool:
        """Test all external connections and dependencies.
        
        Returns:
            True if all connections are working
        """
        self.progress_tracker.display_info("Testing ImgChest API connection...")
        
        try:
            if self.uploader.test_connection():
                self.progress_tracker.display_success("ImgChest API connection OK")
                return True
            else:
                self.progress_tracker.display_error(
                    "ImgChest API connection failed"
                )
                return False
        except Exception as e:
            self.progress_tracker.display_error(
                f"ImgChest API test failed: {e}",
                e
            )
            return False