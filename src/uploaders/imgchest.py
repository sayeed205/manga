"""ImgChest API uploader implementation."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable, cast

import requests
from dotenv import load_dotenv
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    RequestException,
    Timeout,
)
from requests_toolbelt.multipart.encoder import MultipartEncoder

from src.models.upload import UploadResult


class ImgChestUploader:
    """Handles ImgChest API integration for image uploads."""

    def __init__(self) -> None:
        """Initialize the ImgChest uploader with API authentication."""
        _ = load_dotenv()
        self.api_key: str | None = os.getenv("IMGCHEST_API_KEY")
        if not self.api_key:
            raise ValueError(
                "IMGCHEST_API_KEY not found in environment variables. "
                + "Please add it to your .env file."
            )

        self.base_url: str = "https://api.imgchest.com/v1"
        self.timeout: int = 30
        self.max_retries: int = 3
        self.retry_delay: float = 1.0

    def _make_request(
        self,
        method: str,
        endpoint: str,
        files: list[tuple[str, tuple[str, bytes, str]]] | None = None,
        data: dict[str, str] | None = None,
    ) -> dict[str, object]:
        """Make an authenticated API request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            files: Files to upload (for multipart requests)
            data: Form data to send

        Returns:
            JSON response from the API

        Raises:
            RequestException: If all retry attempts fail
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Prepare request data
        request_data = data or {}
        response = None

        for attempt in range(self.max_retries):
            try:
                if files:
                    # Use MultipartEncoder for file uploads
                    fields: list[tuple[str, tuple[str, bytes, str] | str]] = list(files)
                    if request_data:
                        # Add form data to fields
                        for key, value in request_data.items():
                            fields.append((key, value))
                    
                    encoder = MultipartEncoder(fields=fields)
                    headers["Content-Type"] = encoder.content_type
                    
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        data=encoder,
                        timeout=self.timeout,
                    )
                else:
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        data=request_data,
                        timeout=self.timeout,
                    )

                # Check for rate limiting
                if response.status_code == 429:
                    retry_after_str = response.headers.get("Retry-After", "60")
                    retry_after = int(retry_after_str)
                    if attempt < self.max_retries - 1:
                        time.sleep(float(retry_after))
                        continue


                
                response.raise_for_status()
                try:
                    json_data = response.json()
                except ValueError as json_err:
                    raise RequestException("Invalid JSON in response") from json_err
                
                if not isinstance(json_data, dict):
                    raise RequestException("Response is not a JSON object")
                
                return cast(dict[str, object], json_data)

            except Timeout as e:
                if attempt < self.max_retries - 1:
                    timeout_sleep: float = self.retry_delay * (2**attempt)
                    time.sleep(timeout_sleep)  # Exponential backoff
                    continue
                raise RequestException(
                    f"Request timed out after {self.max_retries} attempts"
                ) from e

            except ConnectionError as e:
                if attempt < self.max_retries - 1:
                    connection_sleep: float = self.retry_delay * (2**attempt)
                    time.sleep(connection_sleep)
                    continue
                raise RequestException(
                    f"Connection failed after {self.max_retries} attempts"
                ) from e

            except HTTPError as e:
                # Don't retry on client errors (4xx), only server errors (5xx)
                if (
                    response
                    and response.status_code >= 500
                    and attempt < self.max_retries - 1
                ):
                    http_sleep: float = self.retry_delay * (2**attempt)
                    time.sleep(http_sleep)
                    continue
                error_text = response.text if response else "Unknown error"
                status_code = response.status_code if response else "Unknown"
                # Add detailed error info for debugging
                print(f"Debug: HTTPError - Status: {status_code}, URL: {url}")
                print(f"Debug: Response text: {error_text[:200]}...")
                raise RequestException(
                    f"HTTP error {status_code}: {error_text}"
                ) from e

        raise RequestException(f"All {self.max_retries} retry attempts failed")

    def _prepare_image_files(
        self, image_paths: list[Path]
    ) -> list[tuple[str, tuple[str, bytes, str]]]:
        """Prepare image files for multipart upload.

        Args:
            image_paths: List of paths to image files

        Returns:
            List of tuples for multipart encoder

        Raises:
            FileNotFoundError: If any image file doesn't exist
            IOError: If any image file can't be read
        """
        files: list[tuple[str, tuple[str, bytes, str]]] = []

        for image_path in image_paths:
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")

            try:
                with open(image_path, "rb") as f:
                    file_content = f.read()

                # Determine MIME type based on file extension
                extension = image_path.suffix.lower()
                mime_types = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".gif": "image/gif",
                    ".bmp": "image/bmp",
                    ".webp": "image/webp",
                    ".tiff": "image/tiff",
                }
                mime_type = mime_types.get(extension, f"image/{extension[1:]}")

                # Use 'images[]' as the key name (ImgChest expects this format)
                files.append(("images[]", (image_path.name, file_content, mime_type)))

            except IOError as e:
                raise IOError(
                    f"Failed to read image file {image_path}: {e}"
                ) from e

        return files

    def test_connection(self) -> bool:
        """Test the API connection and authentication.

        Returns:
            True if connection and authentication are successful
        """
        try:
            # Test with the /user/me endpoint (note: singular 'user', not 'users')
            response = self._make_request("GET", "/user/me")
            # Check if we got a valid response with user information
            if "data" in response and isinstance(response["data"], dict):
                user_data = response["data"]
                username = user_data.get("name", "Unknown")
                user_id = user_data.get("id", "Unknown")
                print(f"Success: Logged in as '{username}' (ID: {user_id})")
                return True
            return False
        except Exception as e:
            print(f"Debug: API test failed with error: {e}")
            return False

    def create_album(
        self, images: list[Path], album_name: str = ""
    ) -> tuple[str, str]:
        """Create a new album with the first batch of images.

        Args:
            images: List of image file paths (max 20)
            album_name: Optional name for the album

        Returns:
            Tuple of (album_url, album_id)

        Raises:
            ValueError: If more than 20 images provided
            RequestException: If API request fails
        """
        if len(images) > 20:
            raise ValueError(
                f"Cannot upload more than 20 images in one batch. Got {len(images)}"
            )

        if not images:
            raise ValueError("No images provided for album creation")

        files = self._prepare_image_files(images)
        data: dict[str, str] = {}
        if album_name:
            data["album_name"] = album_name

        try:
            response = self._make_request(
                "POST", "/post", files=files, data=data
            )

            # Check for error in response
            if 'error' in response or ('status' in response and response['status'] == 'error'):
                error_msg = response.get('error', response.get('message', 'Unknown API error'))
                raise RequestException(f"API error: {error_msg}")

            # Extract album information from nested data structure
            api_data = response.get("data")
            if not isinstance(api_data, dict):
                raise RequestException("Invalid response: missing or invalid data field")

            album_id = api_data.get("id")
            if not isinstance(album_id, str):
                raise RequestException("Invalid response: missing or invalid post ID")

            album_url = f"https://imgchest.com/p/{album_id}"

            return album_url, album_id

        except Exception as e:
            raise RequestException(f"Failed to create album: {e}") from e

    def add_images_to_album(self, album_id: str, images: list[Path]) -> bool:
        """Add images to an existing album.

        Args:
            album_id: ID of the existing album
            images: List of image file paths (max 20)

        Returns:
            True if images were successfully added

        Raises:
            ValueError: If more than 20 images provided
            RequestException: If API request fails
        """
        if len(images) > 20:
            raise ValueError(
                f"Cannot upload more than 20 images in one batch. Got {len(images)}"
            )

        if not images:
            return True  # Nothing to upload

        files = self._prepare_image_files(images)

        try:
            response = self._make_request("POST", f"/post/{album_id}/add", files=files)
            
            # Check for error in response
            if 'error' in response or ('status' in response and response['status'] == 'error'):
                error_msg = response.get('error', response.get('message', 'Unknown API error'))
                raise RequestException(f"API error: {error_msg}")
            
            return True

        except Exception as e:
            raise RequestException(
                f"Failed to add images to album {album_id}: {e}"
            ) from e

    def delete_album(self, album_id: str) -> bool:
        """Delete an album from ImgChest.

        Args:
            album_id: ID of the album to delete

        Returns:
            True if album was successfully deleted

        Raises:
            RequestException: If API request fails
        """
        try:
            response = self._make_request("DELETE", f"/post/{album_id}")
            
            # Check for error in response
            if 'error' in response or ('status' in response and response['status'] == 'error'):
                error_msg = response.get('error', response.get('message', 'Unknown API error'))
                raise RequestException(f"API error: {error_msg}")
            
            return True

        except Exception as e:
            raise RequestException(f"Failed to delete album {album_id}: {e}") from e

    def upload_chapter_images(
        self,
        images: list[Path],
        chapter_name: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> UploadResult:
        """Upload all images for a chapter in batches.

        Args:
            images: List of all image file paths for the chapter
            chapter_name: Name of the chapter for the album
            progress_callback: Optional callback for progress updates (current_batch, total_batches)

        Returns:
            UploadResult with success status and album information
        """
        if not images:
            return UploadResult(
                success=False,
                album_url=None,
                album_id=None,
                total_images=0,
                error_message="No images provided for upload",
            )

        try:
            # Split images into batches of maximum 20
            batch_size = 20
            batches = [
                images[i : i + batch_size]
                for i in range(0, len(images), batch_size)
            ]
            total_batches = len(batches)

            album_url = None
            album_id = None

            # Process first batch - create album
            if progress_callback:
                progress_callback(1, total_batches)

            first_batch = batches[0]
            album_url, album_id = self.create_album(first_batch, chapter_name)

            # Process remaining batches - add to existing album
            for batch_num, batch in enumerate(batches[1:], start=2):
                if progress_callback:
                    progress_callback(batch_num, total_batches)

                _ = self.add_images_to_album(album_id, batch)

            return UploadResult(
                success=True,
                album_url=album_url,
                album_id=album_id,
                total_images=len(images),
                error_message=None,
            )

        except Exception as e:
            return UploadResult(
                success=False,
                album_url=None,
                album_id=None,
                total_images=len(images),
                error_message=str(e),
            )
