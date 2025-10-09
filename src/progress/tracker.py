"""Progress tracking with Rich progress bars."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import final

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from src.models.chapter import ChapterInfo
from src.models.upload import UploadResult


@final
class ProgressTracker:
    """Tracks upload progress and maintains upload records."""

    def __init__(self, console: Console | None = None, base_output_dir: Path | None = None) -> None:
        """Initialize the progress tracker.
        
        Args:
            console: Rich console instance. If None, creates a new one.
            base_output_dir: Base directory for manga folders
        """
        self.console = console or Console()
        self.base_output_dir = base_output_dir or Path("mangas")
        self.upload_records: dict[str, dict[str, object]] = {}
        self.current_manga_title: str | None = None

    def set_current_manga(self, manga_title: str) -> None:
        """Set the current manga being processed and load its upload records.
        
        Args:
            manga_title: Title of the manga being processed
        """
        self.current_manga_title = manga_title
        self._load_upload_records()

    def _get_records_file(self) -> Path:
        """Get the upload records file path for the current manga.
        
        Returns:
            Path to the upload records file
        """
        if not self.current_manga_title:
            # Fallback to global records file
            return Path("upload_records.json")
        
        manga_dir = self.base_output_dir / self.current_manga_title
        return manga_dir / "upload_records.json"

    def _load_upload_records(self) -> None:
        """Load existing upload records from file."""
        records_file = self._get_records_file()
        if records_file.exists():
            try:
                with open(records_file, encoding="utf-8") as f:
                    self.upload_records = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                self.console.print(
                    f"[yellow]Warning: Could not load upload records: {e}[/yellow]"
                )
                self.upload_records = {}
        else:
            self.upload_records = {}

    def load_upload_records(self) -> dict:
        """Load and return current upload records.
        
        Returns:
            Dictionary of upload records
        """
        self._load_upload_records()
        return self.upload_records.copy()

    def _save_upload_records(self) -> None:
        """Save upload records to file."""
        records_file = self._get_records_file()
        
        # Ensure the directory exists
        records_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(records_file, "w", encoding="utf-8") as f:
                json.dump(self.upload_records, f, indent=2, ensure_ascii=False)
        except OSError as e:
            self.console.print(
                f"[red]Error: Could not save upload records: {e}[/red]"
            )

    def is_chapter_uploaded(self, chapter_key: str) -> bool:
        """Check if a chapter has already been uploaded.
        
        Args:
            chapter_key: Unique identifier for the chapter (chapter number only)
            
        Returns:
            True if chapter was previously uploaded
        """
        return chapter_key in self.upload_records

    def get_upload_record(self, chapter_key: str) -> dict[str, object] | None:
        """Get upload record for a chapter.
        
        Args:
            chapter_key: Unique identifier for the chapter (chapter number only)
            
        Returns:
            Upload record dict or None if not found
        """
        return self.upload_records.get(chapter_key)

    def record_upload(
        self,
        chapter_info: ChapterInfo,
        upload_result: UploadResult,
        group: str,
    ) -> None:
        """Record a successful upload.
        
        Args:
            chapter_info: Information about the uploaded chapter
            upload_result: Result of the upload operation
            group: Selected group for the chapter
        """
        if not upload_result.success or not upload_result.album_url:
            return

        chapter_key = chapter_info.chapter
        
        self.upload_records[chapter_key] = {
            "album_id": upload_result.album_id,
            "timestamp": datetime.now().isoformat(),
            "image_count": upload_result.total_images,
            "group": group,
            "chapter_title": chapter_info.title,
            "volume": chapter_info.volume,
        }
        
        self._save_upload_records()

    def remove_upload_record(self, chapter_key: str) -> bool:
        """Remove an upload record for a chapter.
        
        Args:
            chapter_key: Chapter number to remove
            
        Returns:
            True if record was removed, False if it didn't exist
        """
        if chapter_key in self.upload_records:
            del self.upload_records[chapter_key]
            self._save_upload_records()
            return True
        return False

    def get_existing_chapters(self) -> list[str]:
        """Get list of already uploaded chapter numbers.
        
        Returns:
            List of chapter numbers that have been uploaded
        """
        return list(self.upload_records.keys())

    def confirm_batch_reupload(self, existing_chapters: list[str]) -> set[str]:
        """Ask user which chapters to re-upload from existing ones.
        
        Args:
            existing_chapters: List of chapter numbers that already exist
            
        Returns:
            Set of chapter numbers to re-upload
        """
        if not existing_chapters:
            return set()

        self.console.print("\n[yellow]The following chapters have already been uploaded:[/yellow]")
        
        # Display existing chapters with their info
        for chapter_num in sorted(existing_chapters):
            record = self.get_upload_record(chapter_num)
            if record:
                self.console.print(
                    f"  [cyan]{chapter_num}[/cyan]: {record.get('chapter_title', 'Unknown')} "
                    f"({record.get('image_count', 0)} images, {record.get('timestamp', 'Unknown date')})"
                )
        
        self.console.print(
            "\n[bold]Enter chapter numbers to re-upload (space-separated, e.g., '1 3 5' or '001 003 005'):[/bold]"
        )
        self.console.print("[dim]Press Enter to skip all existing chapters[/dim]")
        
        response = self.console.input("[bold]Chapters to re-upload: [/bold]").strip()
        
        if not response:
            return set()
        
        # Parse the response
        selected_chapters = set()
        for chapter_input in response.split():
            chapter_input = chapter_input.strip()
            if not chapter_input:
                continue
                
            # Normalize chapter number (handle both "1" and "001" formats)
            try:
                chapter_num = int(chapter_input)
                # Convert to 3-digit format to match our storage
                normalized_chapter = f"{chapter_num:03d}"
                
                # Check if this chapter exists in our records
                if normalized_chapter in existing_chapters:
                    selected_chapters.add(normalized_chapter)
                else:
                    self.console.print(f"[yellow]Warning: Chapter {chapter_input} not found in existing uploads[/yellow]")
            except ValueError:
                self.console.print(f"[red]Error: Invalid chapter number '{chapter_input}'[/red]")
        
        if selected_chapters:
            self.console.print(f"[green]Selected chapters for re-upload: {', '.join(sorted(selected_chapters))}[/green]")
        else:
            self.console.print("[blue]No chapters selected for re-upload[/blue]")
        
        return selected_chapters

    def confirm_reupload(self, chapter_info: ChapterInfo) -> bool:
        """Ask user to confirm re-uploading an existing chapter.
        
        Args:
            chapter_info: Information about the chapter
            
        Returns:
            True if user confirms re-upload
        """
        chapter_key = chapter_info.chapter
        record = self.get_upload_record(chapter_key)
        
        if not record:
            return True

        self.console.print(
            f"\n[yellow]Chapter {chapter_key} ({chapter_info.title}) "
            f"was already uploaded on {record['timestamp']}[/yellow]"
        )
        
        response = self.console.input(
            "[bold]Do you want to re-upload this chapter? (y/N): [/bold]"
        )
        
        return response.lower().strip() in ("y", "yes")

    @contextmanager
    def track_chapter_processing(self, total_chapters: int):
        """Context manager for tracking overall chapter processing progress.
        
        Args:
            total_chapters: Total number of chapters to process
            
        Yields:
            Progress instance for updating chapter progress
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            task_id = progress.add_task(
                "Processing chapters...", total=total_chapters
            )
            yield ChapterProgressContext(progress, task_id)

    @contextmanager
    def track_batch_upload(self, chapter_name: str, total_batches: int):
        """Context manager for tracking batch upload progress.
        
        Args:
            chapter_name: Name of the chapter being uploaded
            total_batches: Total number of batches to upload
            
        Yields:
            Progress instance for updating batch progress
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            task_id = progress.add_task(
                f"Uploading {chapter_name}...", total=total_batches
            )
            yield BatchProgressContext(progress, task_id)

    def display_upload_summary(self, processed_chapters: int, failed_chapters: int) -> None:
        """Display a summary of the upload session.
        
        Args:
            processed_chapters: Number of successfully processed chapters
            failed_chapters: Number of failed chapters
        """
        table = Table(title="Upload Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        
        table.add_row("Chapters Processed", str(processed_chapters))
        table.add_row("Chapters Failed", str(failed_chapters))
        table.add_row("Total Records", str(len(self.upload_records)))
        
        self.console.print("\n")
        self.console.print(table)

    def display_error(self, message: str, exception: Exception | None = None) -> None:
        """Display an error message with optional exception details.
        
        Args:
            message: Error message to display
            exception: Optional exception for additional context
        """
        self.console.print(f"[red]Error: {message}[/red]")
        if exception:
            self.console.print(f"[dim]Details: {exception}[/dim]")

    def display_warning(self, message: str) -> None:
        """Display a warning message.
        
        Args:
            message: Warning message to display
        """
        self.console.print(f"[yellow]Warning: {message}[/yellow]")

    def display_success(self, message: str) -> None:
        """Display a success message.
        
        Args:
            message: Success message to display
        """
        self.console.print(f"[green]Success: {message}[/green]")

    def display_info(self, message: str) -> None:
        """Display an info message.
        
        Args:
            message: Info message to display
        """
        self.console.print(f"[blue]Info: {message}[/blue]")


@final
class ChapterProgressContext:
    """Context for tracking chapter processing progress."""

    def __init__(self, progress: Progress, task_id: TaskID) -> None:
        """Initialize the context.
        
        Args:
            progress: Rich Progress instance
            task_id: Task ID for the progress bar
        """
        self.progress = progress
        self.task_id = task_id

    def update(self, advance: int = 1, description: str | None = None) -> None:
        """Update the chapter progress.
        
        Args:
            advance: Number of chapters to advance
            description: Optional description update
        """
        self.progress.update(self.task_id, advance=advance, description=description)

    def set_description(self, description: str) -> None:
        """Set the progress description.
        
        Args:
            description: New description for the progress bar
        """
        self.progress.update(self.task_id, description=description)


@final
class BatchProgressContext:
    """Context for tracking batch upload progress."""

    def __init__(self, progress: Progress, task_id: TaskID) -> None:
        """Initialize the context.
        
        Args:
            progress: Rich Progress instance
            task_id: Task ID for the progress bar
        """
        self.progress = progress
        self.task_id = task_id

    def update(self, advance: int = 1, description: str | None = None) -> None:
        """Update the batch progress.
        
        Args:
            advance: Number of batches to advance
            description: Optional description update
        """
        self.progress.update(self.task_id, advance=advance, description=description)

    def set_description(self, description: str) -> None:
        """Set the progress description.
        
        Args:
            description: New description for the progress bar
        """
        self.progress.update(self.task_id, description=description)