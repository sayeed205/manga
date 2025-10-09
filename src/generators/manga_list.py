"""
Manga list generator for creating RST documentation.
"""

from __future__ import annotations

import base64
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import quote

from rich.console import Console


class MangaListGenerator:
    """Generator for manga-list.rst file with alphabetically organized tables."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the manga list generator.
        
        Args:
            console: Rich console instance for output
        """
        self.console = console or Console()

    def load_env_vars(self) -> Tuple[str, str, str]:
        """Load GitHub username, repo, and branch from .env file.
        
        Returns:
            Tuple of (username, repo, branch)
            
        Raises:
            FileNotFoundError: If .env file not found
            ValueError: If required variables not found
        """
        env_path = Path(".env")
        if not env_path.exists():
            raise FileNotFoundError(".env file not found")
        
        username = None
        repo = None
        branch = None
        
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("GH_USERNAME="):
                    username = line.split("=", 1)[1]
                elif line.startswith("GH_REPO="):
                    repo = line.split("=", 1)[1]
                elif line.startswith("GH_BRANCH="):
                    branch = line.split("=", 1)[1]
        
        if not username or not repo:
            raise ValueError("GH_USERNAME and GH_REPO must be set in .env file")
        
        # Default to 'main' if branch not specified
        if not branch:
            branch = "main"
            self.console.print("[yellow]Warning: GH_BRANCH not found in .env, defaulting to 'main'[/yellow]")
        
        return username, repo, branch

    def get_manga_info(self, mangas_dir: Path | None = None) -> List[Dict]:
        """Extract manga information from all info.json files.
        
        Args:
            mangas_dir: Directory containing manga folders
            
        Returns:
            List of manga information dictionaries
        """
        if mangas_dir is None:
            mangas_dir = Path("mangas")
            
        manga_list = []
        
        if not mangas_dir.exists():
            return manga_list
        
        for manga_dir in mangas_dir.iterdir():
            if manga_dir.is_dir():
                info_file = manga_dir / "info.json"
                if info_file.exists():
                    try:
                        with open(info_file, encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Calculate stats
                        chapters = data.get("chapters", {})
                        chapter_count = len(chapters)
                        
                        # Get unique volumes
                        volumes = set()
                        last_updated_timestamp = 0
                        
                        for chapter_data in chapters.values():
                            if "volume" in chapter_data:
                                volumes.add(chapter_data["volume"])
                            if "last_updated" in chapter_data:
                                timestamp = int(chapter_data["last_updated"])
                                last_updated_timestamp = max(last_updated_timestamp, timestamp)
                        
                        volume_count = len(volumes)
                        
                        # Convert timestamp to readable date with timezone
                        if last_updated_timestamp > 0:
                            last_updated_dt = datetime.fromtimestamp(last_updated_timestamp, tz=timezone.utc)
                            last_updated = last_updated_dt.strftime("%Y-%m-%d %H:%M UTC")
                        else:
                            last_updated = "Unknown"
                        
                        # Get creation date from directory with timezone
                        added_on_dt = datetime.fromtimestamp(manga_dir.stat().st_ctime, tz=timezone.utc)
                        added_on = added_on_dt.strftime("%Y-%m-%d %H:%M UTC")
                        
                        manga_info = {
                            "title": data.get("title", manga_dir.name),
                            "folder_name": manga_dir.name,
                            "added_on": added_on,
                            "last_updated": last_updated,
                            "volume_count": volume_count,
                            "chapter_count": chapter_count
                        }
                        
                        manga_list.append(manga_info)
                        
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        self.console.print(f"[yellow]Warning: Error processing {info_file}: {e}[/yellow]")
                        continue
        
        return manga_list

    def group_mangas_alphabetically(self, manga_list: List[Dict]) -> Dict[str, List[Dict]]:
        """Group mangas by first letter of title.
        
        Args:
            manga_list: List of manga information dictionaries
            
        Returns:
            Dictionary mapping letters to lists of manga
        """
        grouped = defaultdict(list)
        
        for manga in manga_list:
            title = manga["title"]
            # Get first character, handle special characters
            first_char = title[0].upper() if title else "?"
            
            # Group numbers and special characters under "#"
            if not first_char.isalpha():
                first_char = "#"
            
            grouped[first_char].append(manga)
        
        # Sort each group by title
        for group in grouped.values():
            group.sort(key=lambda x: x["title"].lower())
        
        return dict(grouped)

    def _get_cubari_url(self, username: str, repo: str, folder_name: str, branch: str = "main") -> str:
        """Generate Cubari URL using kaguya.py method with URL encoding.
        
        Args:
            username: GitHub username
            repo: GitHub repository name
            folder_name: Manga folder name
            branch: Git branch (defaults to main)
            
        Returns:
            Cubari gist URL with proper URL encoding
        """
        # Create the path for the info.json file
        repo_file_path = f"mangas/{folder_name}/info.json"
        
        # Create the raw path for Cubari gist
        raw_path_for_cubari_gist = f"raw/{username}/{repo}/{branch}/{repo_file_path.replace(os.sep, '/')}"
        
        # URL encode the path first to handle special characters
        url_encoded_path = quote(raw_path_for_cubari_gist, safe='/:')
        
        # Base64 encode the URL-encoded path
        b64_encoded = base64.b64encode(url_encoded_path.encode('utf-8')).decode('utf-8')
        
        # Return the Cubari gist URL
        return f"https://cubari.moe/read/gist/{b64_encoded}/"

    def generate_rst_content(self, grouped_mangas: Dict[str, List[Dict]], username: str, repo: str, branch: str) -> str:
        """Generate the RST content for manga-list.rst.
        
        Args:
            grouped_mangas: Dictionary of grouped manga by letter
            username: GitHub username
            repo: GitHub repository name
            branch: GitHub branch name
            
        Returns:
            RST content as string
        """
        content = []
        
        # Header
        content.append("Manga List")
        content.append("==========")
        content.append("")
        content.append("Complete list of available manga organized alphabetically.")
        content.append("")
        
        # Generate tables for each letter
        for letter in sorted(grouped_mangas.keys()):
            mangas = grouped_mangas[letter]
            
            content.append(f"{letter}")
            content.append("-" * len(letter))
            content.append("")
            
            # Table header
            table_lines = []
            table_lines.append(".. list-table::")
            table_lines.append("   :header-rows: 1")
            table_lines.append("   :widths: 25 12 12 16 16 6 6")
            table_lines.append("")
            table_lines.append("   * - Title")
            table_lines.append("     - Gist")
            table_lines.append("     - Cubari")
            table_lines.append("     - Added On")
            table_lines.append("     - Last Updated")
            table_lines.append("     - Volumes")
            table_lines.append("     - Chapters")
            
            # Table rows
            for manga in mangas:
                title = manga["title"]
                folder_name = manga["folder_name"]
                
                # Generate links using the same method as kaguya.py
                gist_link = f"`info.json <mangas/{folder_name}/info.json>`_"
                cubari_link = f"`Read <{self._get_cubari_url(username, repo, folder_name, branch)}>`_"
                
                table_lines.append(f"   * - {title}")
                table_lines.append(f"     - {gist_link}")
                table_lines.append(f"     - {cubari_link}")
                table_lines.append(f"     - {manga['added_on']}")
                table_lines.append(f"     - {manga['last_updated']}")
                table_lines.append(f"     - {manga['volume_count']}")
                table_lines.append(f"     - {manga['chapter_count']}")
            
            content.extend(table_lines)
            content.append("")
        
        return "\n".join(content)

    def generate_manga_list(self, output_file: Path | None = None, mangas_dir: Path | None = None) -> bool:
        """Generate manga-list.rst file.
        
        Args:
            output_file: Output file path (defaults to manga-list.rst)
            mangas_dir: Directory containing manga folders
            
        Returns:
            True if successful, False otherwise
        """
        if output_file is None:
            output_file = Path("manga-list.rst")
            
        try:
            # Load environment variables
            username, repo, branch = self.load_env_vars()
            
            # Get manga information
            manga_list = self.get_manga_info(mangas_dir)
            
            if not manga_list:
                self.console.print("[yellow]No manga found in mangas/ directory[/yellow]")
                return False
            
            # Group mangas alphabetically
            grouped_mangas = self.group_mangas_alphabetically(manga_list)
            
            # Generate RST content
            rst_content = self.generate_rst_content(grouped_mangas, username, repo, branch)
            
            # Write to file
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(rst_content)
            
            self.console.print(f"[green]✓[/green] Generated {output_file} with {len(manga_list)} manga(s)")
            self.console.print(f"[green]✓[/green] Organized into {len(grouped_mangas)} alphabetical sections")
            
            return True
            
        except Exception as e:
            self.console.print(f"[red]Error generating manga list: {e}[/red]")
            return False