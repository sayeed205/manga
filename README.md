# Manga Upload Script

A Python command-line tool for processing manga folder structures and uploading content to ImgChest image hosting service. The script automates the workflow of organizing manga chapters, batch uploading images, and generating JSON metadata files for manga readers like Mihon (formerly Tachiyomi).

## Features

- **Folder Structure Processing**: Scans manga/volume/chapter/pages directory structures
- **Batch Image Upload**: Uploads images to ImgChest in optimized batches (max 20 per request)
- **Metadata Generation**: Creates JSON files in `mangas/{title}/info.json` format for manga readers
- **Group Management**: Supports scanlation group selection and organization
- **Progress Tracking**: Rich progress bars and upload record keeping
- **Error Recovery**: Graceful error handling with ability to resume failed uploads
- **Cubari Integration**: Generates Cubari-compatible URLs for easy sharing

## Requirements

- Python 3.12 or higher
- ImgChest API key
- **uv package manager (required)**

## Installation

**This project requires uv package manager. Do not use pip.**

```bash
# Install uv (required)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository-url>
cd manga-upload-script

# Install dependencies
uv sync
```

### Why uv is Required

- Fast dependency resolution and installation
- Proper Python version management (3.12 requirement)
- Consistent environment across all systems
- Built-in virtual environment handling

## Configuration

### 1. Get ImgChest API Key

1. Visit [ImgChest](https://imgchest.com/)
2. Create an account or log in
3. Go to your account settings
4. Generate an API key

### 2. Create Environment File

Create a `.env` file in the project root:

```bash
IMGCHEST_API_KEY=your_api_key_here
GH_USERNAME=your_github_username
GH_REPO=your_repository_name
GH_BRANCH=main
```

**Required variables:**
- `IMGCHEST_API_KEY`: Your ImgChest API key for uploading images
- `GH_USERNAME`: Your GitHub username for hosting the info.json files
- `GH_REPO`: Your GitHub repository name where manga metadata is stored
- `GH_BRANCH`: Git branch to use (usually "main")

## Folder Structure

### Expected Input Structure

Your manga folders should follow this structure:

```
manga_folder/
├── info.json              # Required: Manga metadata (see below)
├── Volume 1/
│   ├── Chapter 1/
│   │   ├── 001.jpg
│   │   ├── 002.jpg
│   │   ├── 003.png
│   │   └── ...
│   ├── Chapter 2/
│   │   ├── 001.jpg
│   │   └── ...
│   └── ...
├── Volume 2/
│   ├── Chapter 3/
│   └── ...
└── ...
```

**Supported naming patterns:**
- `Volume 1`, `Vol 1`, `V1`
- `Chapter 1`, `Ch 1`, `C1`
- `V1 Ch1 Title`, `Volume 1 Chapter 1 Title`
- Any folder with extractable numbers

**Supported image formats:**
`.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`, `.tiff`

### Required: Local Manga Metadata

**You must provide manga information by placing an `info.json` file in your manga folder root.** The script requires this file to process the manga:

```json
{
  "title": "Haikyū!! - ハイキュー!!",
  "description": "Ever since he watched the legendary player known as \"the Little Giant\" compete at the high school national volleyball finals, Shōyō Hinata has wanted to be the best volleyball player ever! He decides to join the volleyball club at his middle school, but he must wait until his third year to play in an official tournament. His team is crushed by volleyball prodigy Tobio Kageyama, also known as \"the King of the Court\", in straight sets. Swearing revenge on Kageyama, Hinata graduates middle school and joins Karasuno High School, the school where the Little Giant played. However, upon joining the volleyball club, he finds out that Kageyama is there as well!",
  "artist": "Haruichi Furudate",
  "author": "Haruichi Furudate", 
  "cover": "https://i.pinimg.com/736x/9e/f0/9c/9ef09cc9eb94466f061cb4d62990ca33.jpg",
  "groups": ["danke-Empire"]
}
```

**Required info.json fields:**
- `title`: Manga title (required)
- `description`: Manga synopsis/description (required)
- `artist`: Artist name (required)
- `author`: Author name (required)
- `cover`: URL to cover image (required)
- `groups`: Array of scanlation group names (required)

**Important:** The script will not process manga folders without a valid `info.json` file. All fields are mandatory for proper metadata generation.

### Generated Output Structure

```
mangas/
└── {manga_title}/
    ├── info.json           # Metadata with ImgChest URLs
    └── upload_records.json # Upload history tracking
```

## Usage

### Basic Usage

**All commands must use `uv run` - do not use python directly or pip.**

```bash
# Process all manga folders in current directory
uv run main.py

# Process specific manga folder  
uv run main.py /path/to/manga/folder

# Test API connection
uv run main.py --test

# Dry run (scan without uploading)
uv run main.py --dry-run /path/to/manga

# Verbose output for debugging
uv run main.py --verbose /path/to/manga

# Update existing manga with new chapters
uv run main.py /path/to/additional/chapters

# Process with custom output directory
uv run main.py --output-dir custom_mangas /path/to/manga
```

### Interactive Mode

If you run the script without specifying a folder, it will prompt you:

```bash
uv run main.py
# Enter path to manga folder (or press Enter for current directory):
```

### Command Line Options

```bash
uv run main.py [OPTIONS] [MANGA_FOLDER]

Options:
  --test              Test API connection and exit
  --dry-run          Scan and show what would be processed without uploading
  --output-dir DIR   Output directory for metadata files (default: mangas)
  --verbose, -v      Enable verbose output for debugging
  --help            Show help message
```

## Manga List Management

The script automatically maintains a `manga-list.rst` file that tracks all processed manga:

- **Gist Links**: Direct links to the generated `info.json` files
- **Cubari Links**: Ready-to-use Cubari reader URLs
- **Statistics**: Volume and chapter counts, last updated timestamps
- **Alphabetical Organization**: Automatically sorted by title

### Example Entry

```rst
* - Haikyū!! - ハイキュー!!
  - `info.json <mangas/Haiky%C5%AB%21%21%20-%20%E3%83%8F%E3%82%A4%E3%82%AD%E3%83%A5%E3%83%BC%21%21/info.json>`_
  - `Read <https://cubari.moe/read/gist/your-encoded-url/>`_
  - 2025-10-09 14:55 UTC
  - 2025-10-09 15:52 UTC
  - 3
  - 25
```

## Using with Mihon (Tachiyomi)

### 1. Install Cubari Extension

1. Open Mihon app
2. Go to **Browse** → **Extension**
3. Search for "Cubari" and install it

### 2. Enable Cubari in Settings

1. Go to **Settings** → **Browse**
2. Find **Extension settings**
3. Locate **Cubari** extension
4. Enable **Allow third-party installations** or similar option

### 3. Add Manga to Mihon

#### Method 1: Direct Cubari Link
1. Copy the Cubari link from your `manga-list.rst`
2. Open the link in your browser
3. The page should have an "Open in Tachiyomi/Mihon" button
4. Click it to add the manga to your library

#### Method 2: Manual Addition
1. In Mihon, go to **Browse** → **Cubari**
2. Use the search or add URL feature
3. Paste your Cubari URL: `https://cubari.moe/read/gist/your-encoded-url/`
4. Add to library

### 4. Verify Installation

1. Check that the manga appears in your **Library**
2. Try opening a chapter to ensure images load properly
3. Chapters should display in the correct order with proper titles

## Generated JSON Format

The script generates `info.json` files compatible with Cubari and other manga readers:

```json
{
  "title": "Manga Title",
  "description": "Manga description",
  "artist": "Artist Name",
  "author": "Author Name", 
  "cover": "https://imgchest.com/cover-url",
  "groups": ["Scanlation Group"],
  "chapters": {
    "1": {
      "title": "Chapter 1 Title",
      "volume": "1",
      "groups": {
        "Scanlation Group": "https://imgchest.com/album-url"
      },
      "last_updated": "1696867200"
    }
  }
}
```

## Reading Existing Manga Information

The script can read and update existing `info.json` files to:

### 1. Resume Interrupted Uploads
- Automatically detects existing metadata files
- Skips already uploaded chapters
- Continues from where it left off
- Updates timestamps and chapter counts

### 2. Add New Chapters
- Reads existing manga information (title, author, artist, description)
- Preserves existing chapter data
- Adds new chapters while maintaining continuity
- Updates volume and chapter statistics

### 3. Update Manga Metadata
- Reads current manga information from `mangas/{title}/info.json`
- Allows updating description, author, artist information
- Preserves all existing chapter URLs and data
- Maintains upload history and timestamps

### 4. Merge Multiple Sources
- Can combine chapters from different folder structures
- Maintains chronological chapter ordering
- Handles duplicate chapter detection
- Preserves scanlation group attribution

### Example: Updating Existing Manga

```bash
# Add new chapters to existing manga
uv run main.py /path/to/new/chapters

# The script will:
# 1. Detect existing info.json in mangas/MangaTitle/
# 2. Read current metadata (title, author, description, etc.)
# 3. Scan for new chapters not already in the JSON
# 4. Upload only new content
# 5. Update the info.json with new chapters
# 6. Preserve all existing data and URLs
```

### Metadata Preservation

When reading existing `info.json` files, the script preserves:
- **Manga Information**: Title, description, author, artist, cover
- **Chapter Data**: All existing chapter URLs and metadata  
- **Group Information**: Scanlation group attributions
- **Timestamps**: Original upload dates and last updated times
- **Custom Fields**: Any additional metadata fields you've added

## Troubleshooting

### Common Issues

**API Key Not Found**
```
Error: IMGCHEST_API_KEY not found in environment variables.
```
- Ensure `.env` file exists with your API key
- Check that the key is valid and active

**Permission Errors**
```
Error: No write permission for output directory
```
- Check folder permissions
- Try running with appropriate user permissions
- Ensure the output directory is writable

**Upload Failures**
- Check your internet connection
- Verify ImgChest service status
- Ensure API key has sufficient quota
- Try reducing batch size if timeouts occur

**Folder Structure Not Recognized**
- Ensure folders contain extractable numbers (Volume 1, Ch 1, etc.)
- Check that image files have supported extensions
- Use `--verbose` flag to see detailed parsing information

### Debug Mode

Use verbose mode for detailed troubleshooting:

```bash
uv run main.py --verbose --dry-run /path/to/manga
```

This will show:
- Folder parsing details
- Image file detection
- Upload preparation steps
- Error stack traces

## Development

### Code Quality

Before contributing, ensure code quality:

```bash
# Check linting and style
uv run ruff check

# Check type annotations
uv run basedpyright
```

### Project Structure

```
├── main.py                 # Entry point and CLI
├── src/
│   ├── models/            # Data classes and types
│   ├── parsers/           # Folder parsing utilities
│   ├── uploaders/         # ImgChest API integration
│   ├── metadata/          # JSON metadata management
│   ├── processors/        # Main processing logic
│   ├── selectors/         # Group selection logic
│   └── progress/          # Progress tracking
├── mangas/                # Generated metadata output
├── pyproject.toml         # Project configuration
└── .env                   # API configuration (create this)
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.