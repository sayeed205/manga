"""ImgChest API uploader implementation."""

from __future__ import annotations

import mimetypes
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
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor

from src.models.upload import UploadResult


class PayloadTooLargeError(RequestException):
    """Exception raised when payload is too large (413 error)."""
    pass


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
        data: Any = None, 
        files: dict | None = None,
        headers: dict | None = None
    ) -> requests.Response:
        """Make an API request with error handling.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body (can be dict or MultipartEncoderMonitor)
            files: Files to upload (legacy, used if data is not a monitor)
            headers: Additional headers
            
        Returns:
            Response object
            
        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        request_headers = {"Authorization": f"Bearer {self.api_key}"}
        
        if headers:
            request_headers.update(headers)
            
        # If data is a MultipartEncoder(Monitor), we must set Content-Type
        if hasattr(data, "content_type"):
            request_headers["Content-Type"] = data.content_type

        try:
            response = requests.request(
                method, 
                url, 
                data=data, 
                files=files, 
                headers=request_headers,
                timeout=300  # 5 minutes timeout for large uploads
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            # Add response text to error for debugging
            if e.response is not None:
                raise requests.exceptions.HTTPError(
                    f"{e} - Response: {e.response.text}", response=e.response
                ) from e
            raise

    def test_connection(self) -> bool:
        """Test the API connection and authentication.
        
        Returns:
            True if connection and authentication are successful
        """
        try:
            # Test with the /user/me endpoint
            response = self._make_request("GET", "/user/me")
            result = response.json()
            
            # Check if we got a valid response with user information
            if "data" in result and isinstance(result["data"], dict):
                user_data = result["data"]
                username = user_data.get("name", "Unknown")
                user_id = user_data.get("id", "Unknown")
                print(f"Success: Logged in as '{username}' (ID: {user_id})")
                return True
            return False
        except Exception as e:
            print(f"Debug: API test failed with error: {e}")
            return False

    def create_album(
        self, 
        images: list[Path], 
        title: str = "", 
        max_batch_size: int = 20,
        progress_callback: Callable[[int], None] | None = None
    ) -> tuple[str, str]:
        """Create a new album (post) with images.
        
        Args:
            images: List of image paths
            title: Title of the album
            max_batch_size: Maximum images per batch (ignored here as we handle batching upstream)
            progress_callback: Callback for upload progress (bytes uploaded)
            
        Returns:
            Tuple of (album_url, album_id)
        """
        # Prepare fields for MultipartEncoder
        fields = []
        if title:
            fields.append(("title", title))
        
        fields.append(("privacy", "public")) # Default to public
        
        # Add images
        for img_path in images:
            mime_type = mimetypes.guess_type(img_path)[0] or "application/octet-stream"
            fields.append((
                "images[]", 
                (img_path.name, open(img_path, "rb"), mime_type)
            ))

        encoder = MultipartEncoder(fields=fields)
        
        # Wrap with monitor if callback provided
        if progress_callback:
            monitor = MultipartEncoderMonitor(
                encoder, 
                lambda monitor: progress_callback(monitor.bytes_read)
            )
            data = monitor
        else:
            data = encoder

        response = self._make_request("POST", "/post", data=data)
        result = response.json()
        
        data = result.get("data", {})
        album_id = data.get("id")
        album_url = data.get("links", {}).get("url") or data.get("url")
        
        if not album_url and album_id:
            album_url = f"https://imgchest.com/p/{album_id}"
            
        return album_url, album_id

    def add_images_to_album(
        self, 
        album_id: str, 
        images: list[Path], 
        max_batch_size: int = 20,
        progress_callback: Callable[[int], None] | None = None
    ) -> None:
        """Add images to an existing album.
        
        Args:
            album_id: ID of the album
            images: List of image paths
            max_batch_size: Maximum images per batch
            progress_callback: Callback for upload progress (bytes uploaded)
        """
        # Prepare fields for MultipartEncoder
        fields = []
        
        # Add images
        for img_path in images:
            mime_type = mimetypes.guess_type(img_path)[0] or "application/octet-stream"
            fields.append((
                "images[]", 
                (img_path.name, open(img_path, "rb"), mime_type)
            ))

        encoder = MultipartEncoder(fields=fields)
        
        # Wrap with monitor if callback provided
        if progress_callback:
            monitor = MultipartEncoderMonitor(
                encoder, 
                lambda monitor: progress_callback(monitor.bytes_read)
            )
            data = monitor
        else:
            data = encoder

        self._make_request("POST", f"/post/{album_id}/add", data=data)

    def delete_album(self, album_id: str) -> bool:
        """Delete an album.
        
        Args:
            album_id: ID of the album to delete
            
        Returns:
            True if successful
        """
        self._make_request("DELETE", f"/post/{album_id}")
        return True

    def upload_chapter_images(
        self,
        images: list[Path],
        chapter_name: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> UploadResult:
        """Upload images for a chapter, handling batching and errors.
        
        Args:
            images: List of image paths to upload
            chapter_name: Name of the chapter (for album title)
            progress_callback: Callback(uploaded_bytes, total_bytes)
            
        Returns:
            UploadResult object
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
            # Batch images by size (5MB limit)
            max_batch_size_bytes = 5 * 1024 * 1024  # 5MB
            album_url = None
            album_id = None
            processed_images = 0
            
            # Calculate file sizes first
            image_sizes = []
            total_bytes = 0
            for img_path in images:
                try:
                    size = img_path.stat().st_size
                    if size > max_batch_size_bytes:
                        return UploadResult(
                            success=False,
                            album_url=None,
                            album_id=None,
                            total_images=len(images),
                            error_message=f"Image {img_path.name} ({size/1024/1024:.2f}MB) exceeds the 5MB batch limit",
                        )
                    image_sizes.append((img_path, size))
                    total_bytes += size
                except OSError as e:
                    return UploadResult(
                        success=False,
                        album_url=None,
                        album_id=None,
                        total_images=len(images),
                        error_message=f"Failed to get size of {img_path}: {e}",
                    )

            # Create batches based on size
            batches = []
            current_batch = []
            current_batch_size = 0
            
            for img_path, size in image_sizes:
                # If adding this image would exceed the limit, start a new batch
                # But always ensure at least one image per batch (checked above that single image < limit)
                if current_batch and (current_batch_size + size > max_batch_size_bytes):
                    batches.append((current_batch, current_batch_size))
                    current_batch = []
                    current_batch_size = 0
                
                current_batch.append(img_path)
                current_batch_size += size
            
            if current_batch:
                batches.append((current_batch, current_batch_size))

            total_batches = len(batches)
            uploaded_bytes = 0
            
            # Process batches
            for i, (batch, batch_size) in enumerate(batches):
                try:
                    # Define callback for this batch
                    # We need to capture the current uploaded_bytes state
                    start_bytes = uploaded_bytes
                    
                    def batch_monitor(bytes_read: int):
                        if progress_callback:
                            progress_callback(start_bytes + bytes_read, total_bytes)

                    if album_id is None:
                        # First batch - create album
                        album_url, album_id = self.create_album(
                            batch, 
                            chapter_name, 
                            max_batch_size=9999,
                            progress_callback=batch_monitor
                        )
                    else:
                        # Add to existing album
                        self.add_images_to_album(
                            album_id, 
                            batch, 
                            max_batch_size=9999,
                            progress_callback=batch_monitor
                        )
                    
                    processed_images += len(batch)
                    uploaded_bytes += batch_size
                    
                    # Ensure we report full completion of this batch
                    if progress_callback:
                        progress_callback(uploaded_bytes, total_bytes)
                        
                except Exception as e:
                    # If we fail, we stop here
                    # If we created an album, we return what we have so far
                    # but mark as failed
                    return UploadResult(
                        success=False,
                        album_url=album_url,
                        album_id=album_id,
                        total_images=len(images),
                        error_message=f"Failed at batch {i+1}/{total_batches}: {e}",
                    )

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
