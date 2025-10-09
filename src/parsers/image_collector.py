"""Image file collection utilities."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

console = Console()

# Supported image file extensions
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}


def collect_image_files(folder_path: Path) -> list[Path]:
    """
    Collect all image files from a folder with supported extensions.
    
    Args:
        folder_path: Path to the folder to scan
        
    Returns:
        list[Path]: List of image file paths, sorted by name
    """
    if not folder_path.exists() or not folder_path.is_dir():
        console.print(f"[red]Warning: Folder does not exist or is not a directory: {folder_path}[/red]")
        return []
    
    image_files: list[Path] = []
    for file_path in folder_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
            image_files.append(file_path)
    
    # Sort files by name for consistent ordering
    image_files.sort(key=lambda x: x.name.lower())
    
    if not image_files:
        console.print(f"[yellow]Warning: No image files found in folder: {folder_path}[/yellow]")
    
    return image_files