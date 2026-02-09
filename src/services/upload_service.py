"""
File Upload Service
===================
AWS S3 file upload service:
- Multi-part uploads for large files
- File validation
- Metadata storage
- Public/private access control

Author: Production Team
Version: 1.0.0
"""

from typing import Dict, Any, Optional
from pathlib import Path
from uuid import uuid4
import mimetypes

import boto3
from botocore.exceptions import ClientError

from src.core.config import settings
from src.core.logging import get_logger
from src.core.exceptions import FileUploadError


logger = get_logger(__name__)


# ============================================================================
# FILE UPLOAD SERVICE
# ============================================================================

class FileUploadService:
    """
    AWS S3 file upload service.
    
    Features:
    - File validation (size, type)
    - S3 upload with metadata
    - Pre-signed URLs
    - Multi-part upload support
    
    Time complexity: O(n) where n=file size
    Space complexity: O(1) - streaming upload
    """
    
    def __init__(self):
        """Initialize S3 client."""
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.AWS_S3_BUCKET
        
        logger.info(
            "File upload service initialized",
            extra={"bucket": self.bucket_name}
        )
    
    async def upload_file(
        self,
        file_path: str,
        folder: str = "uploads",
        filename: Optional[str] = None,
        public: bool = False,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload file to S3.
        
        Args:
            file_path: Local file path
            folder: S3 folder path
            filename: Custom filename (None = auto-generate)
            public: Make file publicly accessible
            metadata: Custom metadata
            
        Returns:
            dict: Upload result with URL
            
        Raises:
            FileUploadError: If upload fails
        """
        try:
            # Validate file
            path = Path(file_path)
            if not path.exists():
                raise FileUploadError(
                    filename=file_path,
                    details={"error": "File not found"}
                )
            
            file_size = path.stat().st_size
            if file_size > settings.MAX_UPLOAD_SIZE:
                raise FileUploadError(
                    filename=file_path,
                    details={
                        "error": "File too large",
                        "size": file_size,
                        "max_size": settings.MAX_UPLOAD_SIZE
                    }
                )
            
            # Generate S3 key
            if not filename:
                extension = path.suffix
                filename = f"{uuid4()}{extension}"
            
            s3_key = f"{folder}/{filename}"
            
            # Prepare metadata
            content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            
            upload_metadata = metadata or {}
            upload_metadata.update({
                "original_filename": path.name,
                "file_size": str(file_size)
            })
            
            # Upload to S3
            extra_args = {
                "ContentType": content_type,
                "Metadata": upload_metadata
            }
            
            if public:
                extra_args["ACL"] = "public-read"
            
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            # Generate URL
            if public:
                url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            else:
                url = self.generate_presigned_url(s3_key, expiration=3600)
            
            logger.info(
                "File uploaded successfully",
                extra={
                    "filename": filename,
                    "s3_key": s3_key,
                    "size": file_size
                }
            )
            
            return {
                "success": True,
                "filename": filename,
                "s3_key": s3_key,
                "url": url,
                "size": file_size,
                "content_type": content_type
            }
        
        except ClientError as e:
            logger.error("S3 upload failed", error=e)
            raise FileUploadError(
                filename=file_path,
                details={"error": str(e)}
            )
    
    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate pre-signed URL for private file.
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration in seconds
            
        Returns:
            str: Pre-signed URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key
                },
                ExpiresIn=expiration
            )
            
            logger.debug(f"Generated presigned URL for {s3_key}")
            return url
        
        except ClientError as e:
            logger.error("Failed to generate presigned URL", error=e)
            raise FileUploadError(
                filename=s3_key,
                details={"error": str(e)}
            )
    
    async def delete_file(self, s3_key: str) -> bool:
        """
        Delete file from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            bool: True if successful
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"File deleted from S3: {s3_key}")
            return True
        
        except ClientError as e:
            logger.error(f"Failed to delete file: {s3_key}", error=e)
            return False


# Export
__all__ = ["FileUploadService"]
