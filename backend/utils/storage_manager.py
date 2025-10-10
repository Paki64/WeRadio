"""
WeRadio - Storage Manager
==========================

Abstraction layer for storage operations supporting both local filesystem
and MinIO object storage.

Version: 0.4
"""

import os
import io
import logging 
from pathlib import Path
from typing import List, Optional, BinaryIO

logger = logging.getLogger('WeRadio.StorageManager')


class StorageManager:
    """
    Abstract storage interface that supports both local filesystem and MinIO.
    """
    
    def __init__(self, use_object_storage: bool = False):
        """
        Initialize storage manager.
        
        Args:
            use_object_storage: If True, use MinIO; if False, use local filesystem
        """
        self.use_object_storage = use_object_storage
        self.minio_client = None
        
        if use_object_storage:
            self._init_minio()
        
        logger.info(f"Storage mode: {'MinIO Object Storage' if use_object_storage else 'Local Filesystem'}")
    
    def _init_minio(self):
        """Initialize MinIO client and create buckets if needed."""
        try:
            from minio import Minio
            from config import (
                MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY,
                MINIO_SECURE, MINIO_BUCKET_LIBRARY
            )
            
            self.minio_client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE
            )
            
            # Store bucket names
            self.bucket_library = MINIO_BUCKET_LIBRARY
            
            # Create buckets if they don't exist
            for bucket in [self.bucket_library]:
                if not self.minio_client.bucket_exists(bucket):
                    self.minio_client.make_bucket(bucket)
                    logger.info(f"Created MinIO bucket: {bucket}")
            
            logger.info(f"Connected to MinIO at {MINIO_ENDPOINT}")
            
        except Exception as e:
            logger.error(f"Failed to initialize MinIO: {e}")
            raise
    
    def _get_bucket(self, folder_type: str) -> Optional[str]:
        """
        Get the MinIO bucket name for a folder type.
        
        Args:
            folder_type: 'library', 'cache', or 'hls'
            
        Returns:
            Bucket name or None
        """
        if not self.use_object_storage:
            return None
        
        bucket_map = {
            'library': self.bucket_library,
        }
        return bucket_map.get(folder_type)
    
    def list_files(self, base_path: str, folder_type: str = 'library', 
                   extensions: Optional[set] = None) -> List[str]:
        """
        List files in a directory or bucket.
        
        Args:
            base_path: Base path for local filesystem (ignored for MinIO)
            folder_type: Type of folder ('library', 'cache', 'hls')
            extensions: Set of file extensions to filter (e.g., {'.mp3', '.aac'})
            
        Returns:
            List of relative file paths
        """
        if self.use_object_storage:
            return self._list_files_minio(folder_type, extensions)
        else:
            return self._list_files_local(base_path, extensions)
    
    def _list_files_local(self, base_path: str, extensions: Optional[set]) -> List[str]:
        """List files from local filesystem."""
        files = []
        base = Path(base_path)
        
        if not base.exists():
            return files
        
        for file in base.rglob('*'):
            if file.is_file():
                if extensions is None or file.suffix.lower() in extensions:
                    try:
                        rel_path = str(file.relative_to(base))
                        files.append(rel_path)
                    except ValueError:
                        files.append(file.name)
        
        return files
    
    def _list_files_minio(self, folder_type: str, extensions: Optional[set]) -> List[str]:
        """List files from MinIO bucket."""
        bucket = self._get_bucket(folder_type)
        if not bucket:
            return []
        
        files = []
        try:
            objects = self.minio_client.list_objects(bucket, recursive=True)
            for obj in objects:
                if extensions is None or any(obj.object_name.lower().endswith(ext) for ext in extensions):
                    files.append(obj.object_name)
        except Exception as e:
            logger.error(f"Error listing files from MinIO bucket {bucket}: {e}")
        
        return files
    
    def read_file(self, filepath: str, base_path: str, folder_type: str = 'library') -> bytes:
        """
        Read file contents.
        
        Args:
            filepath: Relative file path
            base_path: Base path for local filesystem
            folder_type: Type of folder ('library', 'cache', 'hls')
            
        Returns:
            File contents as bytes
        """
        if self.use_object_storage:
            return self._read_file_minio(filepath, folder_type)
        else:
            return self._read_file_local(filepath, base_path)
    
    def _read_file_local(self, filepath: str, base_path: str) -> bytes:
        """Read file from local filesystem."""
        full_path = os.path.join(base_path, filepath)
        with open(full_path, 'rb') as f:
            return f.read()
    
    def _read_file_minio(self, filepath: str, folder_type: str) -> bytes:
        """Read file from MinIO bucket."""
        bucket = self._get_bucket(folder_type)
        try:
            response = self.minio_client.get_object(bucket, filepath)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except Exception as e:
            logger.error(f"Error reading file {filepath} from MinIO: {e}")
            raise
    
    def write_file(self, filepath: str, data: bytes, base_path: str, 
                   folder_type: str = 'library', content_type: str = 'application/octet-stream'):
        """
        Write file contents.
        
        Args:
            filepath: Relative file path
            data: File contents as bytes
            base_path: Base path for local filesystem
            folder_type: Type of folder ('library', 'cache', 'hls')
            content_type: MIME type for MinIO
        """
        if self.use_object_storage:
            self._write_file_minio(filepath, data, folder_type, content_type)
        else:
            self._write_file_local(filepath, data, base_path)
    
    def _write_file_local(self, filepath: str, data: bytes, base_path: str):
        """Write file to local filesystem."""
        full_path = os.path.join(base_path, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(data)
    
    def _write_file_minio(self, filepath: str, data: bytes, folder_type: str, content_type: str):
        """Write file to MinIO bucket."""
        bucket = self._get_bucket(folder_type)
        try:
            data_stream = io.BytesIO(data)
            self.minio_client.put_object(
                bucket,
                filepath,
                data_stream,
                length=len(data),
                content_type=content_type
            )
        except Exception as e:
            logger.error(f"Error writing file {filepath} to MinIO: {e}")
            raise
    
    def delete_file(self, filepath: str, base_path: str, folder_type: str = 'library') -> bool:
        """
        Delete a file.
        
        Args:
            filepath: Relative file path
            base_path: Base path for local filesystem
            folder_type: Type of folder ('library', 'cache', 'hls')
            
        Returns:
            True if successful, False otherwise
        """
        if self.use_object_storage:
            return self._delete_file_minio(filepath, folder_type)
        else:
            return self._delete_file_local(filepath, base_path)
    
    def _delete_file_local(self, filepath: str, base_path: str) -> bool:
        """Delete file from local filesystem."""
        try:
            full_path = os.path.join(base_path, filepath)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {filepath}: {e}")
            return False
    
    def _delete_file_minio(self, filepath: str, folder_type: str) -> bool:
        """Delete file from MinIO bucket."""
        bucket = self._get_bucket(folder_type)
        try:
            self.minio_client.remove_object(bucket, filepath)
            return True
        except Exception as e:
            logger.error(f"Error deleting file {filepath} from MinIO: {e}")
            return False
    
    def file_exists(self, filepath: str, base_path: str, folder_type: str = 'library') -> bool:
        """
        Check if a file exists.
        
        Args:
            filepath: Relative file path
            base_path: Base path for local filesystem
            folder_type: Type of folder ('library', 'cache', 'hls')
            
        Returns:
            True if file exists, False otherwise
        """
        if self.use_object_storage:
            return self._file_exists_minio(filepath, folder_type)
        else:
            return self._file_exists_local(filepath, base_path)
    
    def _file_exists_local(self, filepath: str, base_path: str) -> bool:
        """Check if file exists in local filesystem."""
        full_path = os.path.join(base_path, filepath)
        return os.path.exists(full_path)
    
    def _file_exists_minio(self, filepath: str, folder_type: str) -> bool:
        """Check if file exists in MinIO bucket."""
        bucket = self._get_bucket(folder_type)
        try:
            self.minio_client.stat_object(bucket, filepath)
            return True
        except Exception:
            return False
