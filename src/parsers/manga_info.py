"""Manga metadata parsing utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from rich.console import Console

console = Console()


class MangaInfoDict(TypedDict):
    """Type definition for manga info dictionary."""
    title: str
    description: str
    artist: str
    author: str
    cover: str
    groups: list[str]


def load_manga_info_from_folder(manga_folder: Path) -> MangaInfoDict:
    """Load manga metadata from info.json or info.txt in the manga folder.
    
    Args:
        manga_folder: Path to the manga folder
        
    Returns:
        Dictionary containing manga metadata
    """
    info: MangaInfoDict = {
        'title': manga_folder.name,
        'description': '',
        'artist': '',
        'author': '',
        'cover': '',
        'groups': []
    }
    
    # Try to load from info.json first
    json_file = manga_folder / "info.json"
    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Update info with data from JSON file
            if 'title' in json_data and json_data['title']:
                info['title'] = str(json_data['title'])
            if 'description' in json_data and json_data['description']:
                info['description'] = str(json_data['description'])
            if 'artist' in json_data and json_data['artist']:
                info['artist'] = str(json_data['artist'])
            if 'author' in json_data and json_data['author']:
                info['author'] = str(json_data['author'])
            if 'cover' in json_data and json_data['cover']:
                info['cover'] = str(json_data['cover'])
            
            # Handle groups (can be string or list)
            if 'groups' in json_data:
                groups_data = json_data['groups']
                if isinstance(groups_data, list):
                    info['groups'] = [str(g) for g in groups_data if g]
                elif isinstance(groups_data, str):
                    # Split comma-separated string into list
                    info['groups'] = [g.strip() for g in groups_data.split(',') if g.strip()]
                    
            console.print(f"[green]✓[/green] Loaded manga info from {json_file}")
            return info
            
        except json.JSONDecodeError as e:
            console.print(f"[yellow]Warning: Invalid JSON in {json_file}: {e}[/yellow]")
        except IOError as e:
            console.print(f"[yellow]Warning: Could not read {json_file}: {e}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Warning: Error reading {json_file}: {e}[/yellow]")
    
    # Try to load from info.txt (reference implementation format)
    txt_file = manga_folder / "info.txt"
    if txt_file.exists():
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if ':' in line and not line.startswith('#'):
                        key, value = line.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if key == 'title' and value:
                            info['title'] = value
                        elif key == 'description' and value:
                            info['description'] = value
                        elif key == 'artist' and value:
                            info['artist'] = value
                        elif key == 'author' and value:
                            info['author'] = value
                        elif key == 'cover' and value:
                            info['cover'] = value
                        elif key == 'groups' and value:
                            # Split comma-separated string into list
                            info['groups'] = [g.strip() for g in value.split(',') if g.strip()]
                            
            console.print(f"[green]✓[/green] Loaded manga info from {txt_file}")
            return info
            
        except IOError as e:
            console.print(f"[yellow]Warning: Could not read {txt_file}: {e}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Warning: Error reading {txt_file}: {e}[/yellow]")
    
    # No info file found, use folder name as title
    console.print(f"[yellow]No info.json or info.txt found in {manga_folder}. Using folder name as title.[/yellow]")
    return info