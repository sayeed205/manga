#!/usr/bin/env python3
"""
Manga Upload Script

A command-line tool for processing manga folder structures and uploading content to ImgChest.
Processes manga/volume/chapter/pages directory structures, uploads images in batches,
and generates JSON metadata files for manga readers.

Usage:
    uv run main.py [manga_folder]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

from processors.manga_processor import MangaProcessor

# Load environment variables from .env file
_ = load_dotenv()

# Initialize Rich console for output
console = Console()


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


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Process manga folders and upload to ImgChest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run main.py                    # Process all manga folders in current directory
  uv run main.py /path/to/manga     # Process specific manga folder
  uv run main.py --test             # Test API connection only
        """
    )
    
    _ = parser.add_argument(
        "manga_folder",
        nargs="?",
        type=Path,
        help="Path to manga folder to process (optional, defaults to current directory)"
    )
    
    _ = parser.add_argument(
        "--test",
        action="store_true",
        help="Test API connection and exit"
    )
    
    _ = parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("mangas"),
        help="Output directory for metadata files (default: mangas)"
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point for the manga upload script."""
    console.print("[bold blue]Manga Upload Script[/bold blue]")
    console.print("Processing manga folders and uploading to ImgChest...\n")

    # Parse command-line arguments
    args = parse_arguments()

    # Validate environment setup
    if not validate_environment():
        sys.exit(1)

    # Initialize manga processor
    try:
        manga_folder: Path | None = getattr(args, 'manga_folder', None)
        output_dir: Path = getattr(args, 'output_dir', Path("mangas"))
        
        processor = MangaProcessor(
            base_manga_dir=manga_folder,
            output_dir=output_dir,
            console=console
        )
    except Exception as e:
        console.print(f"[red]Failed to initialize processor: {e}[/red]")
        sys.exit(1)

    # Handle test mode
    test_mode: bool = getattr(args, 'test', False)
    if test_mode:
        console.print("[blue]Testing API connection...[/blue]")
        if processor.test_connections():
            console.print("[green]All connections working properly![/green]")
            sys.exit(0)
        else:
            console.print("[red]Connection test failed![/red]")
            sys.exit(1)

    try:
        # Process manga folders
        manga_folder_path: Path | None = getattr(args, 'manga_folder', None)
        
        if manga_folder_path is None:
            # Prompt user for folder path
            console.print("\n[blue]No manga folder specified.[/blue]")
            folder_input = console.input(
                "[bold]Enter path to manga folder (or press Enter for current directory): [/bold]"
            ).strip()
            
            if folder_input:
                manga_folder_path = Path(folder_input)
                if not manga_folder_path.exists():
                    console.print(f"[red]Error: Folder does not exist: {manga_folder_path}[/red]")
                    sys.exit(1)
                if not manga_folder_path.is_dir():
                    console.print(f"[red]Error: Path is not a directory: {manga_folder_path}[/red]")
                    sys.exit(1)
                
                # Process the specified folder
                console.print(f"[green]Processing folder: {manga_folder_path}[/green]")
                processor.process_manga_folder(manga_folder_path)
            else:
                # Use current directory and process all manga folders
                console.print("[green]Processing all manga folders in current directory[/green]")
                processor.process_all_manga_folders()
        
        elif manga_folder_path.exists():
            # Process specific manga folder provided as argument
            processor.process_manga_folder(manga_folder_path)
        else:
            console.print(f"[red]Error: Specified folder does not exist: {manga_folder_path}[/red]")
            sys.exit(1)
        
        console.print("\n[green]Processing completed successfully![/green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Processing interrupted by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Critical error during processing: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()