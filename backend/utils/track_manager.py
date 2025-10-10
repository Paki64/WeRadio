"""
WeRadio - Track Management Utilities
=====================================

Utilities for managing music track files.

Version: 0.4
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger('WeRadio.TrackManager')


class TrackManager:
    """
    Manages music track files and library operations.
    """
    
    @staticmethod
    def load_tracks(upload_folder, supported_formats, storage_manager=None):
        """
        Scans the uploads folder and loads all available tracks.
        
        Args:
            upload_folder (str): Path to the upload folder
            supported_formats (set): Set of supported file extensions
            storage_manager: Optional StorageManager instance for object storage
            
        Returns:
            list: List of relative paths to all available tracks
        """
        if storage_manager and storage_manager.use_object_storage:
            # Use MinIO storage
            files = storage_manager.list_files(upload_folder, 'library', supported_formats)
            logger.info(f"{len(files)} tracks found in MinIO library")
            return files
        else:
            # Use local filesystem
            files = []
            upload_path = Path(upload_folder)
            
            for file in upload_path.rglob('*'):
                if file.suffix.lower() in supported_formats:
                    # Store relative path from upload_folder
                    try:
                        rel_path = str(file.relative_to(upload_path))
                        files.append(rel_path)
                    except ValueError:
                        # Fallback to absolute if relative fails
                        logger.warning(f"Could not compute relative path for {file}, using filename only")
                        files.append(file.name)
            
            logger.info(f"{len(files)} tracks found in local library")
            return files
    
    @staticmethod
    def delete_track_files(track_path, cache_getter=None, storage_manager=None, 
                          upload_folder=None, cache_folder=None, available_tracks=None, queue=None):
        """
        Deletes a track file and its cached version.
        
        Args:
            track_path (str): Path to the track to delete (relative or absolute)
            cache_getter (callable, optional): Function to get cached file path
            storage_manager: Optional StorageManager instance
            upload_folder (str): Upload folder path (for storage manager)
            cache_folder (str): Cache folder path (for storage manager)
            available_tracks (list, optional): List of available tracks to check library size
            queue (deque, optional): Playback queue to remove track from before deletion
        """
        # Prevent deletion if this is the last track in the library
        if available_tracks is not None and len(available_tracks) <= 1:
            logger.warning("Cannot delete the last track in the library")
            return False, "Cannot delete the last track in the library"
        
        # Remove track from queue if present
        if queue is not None and available_tracks is not None:
            from .queue_manager import QueueManager
            if track_path in queue:
                success, message = QueueManager.remove_track_from_queue(queue, track_path, available_tracks)
                if success:
                    logger.info(f"Track removed from queue before deletion: {os.path.basename(track_path)}")
                else:
                    logger.warning(f"Could not remove track from queue: {message}")
        
        try:
            if storage_manager and storage_manager.use_object_storage:
                # Delete from MinIO
                rel_path = track_path.replace('minio://', '') if track_path.startswith('minio://') else track_path
                
                success = storage_manager.delete_file(rel_path, upload_folder, 'library')
                if success:
                    logger.info(f"Deleted file from MinIO: {rel_path}")
                    
                    # Remove cached version
                    if cache_getter:
                        try:
                            cached_file = cache_getter(track_path)
                            cached_rel = cached_file.replace('minio://', '') if cached_file.startswith('minio://') else os.path.basename(cached_file)
                            storage_manager.delete_file(cached_rel, cache_folder, 'cache')
                            logger.debug(f"Deleted cached file from MinIO: {cached_rel}")
                        except Exception as e:
                            logger.debug(f"Could not delete cached file: {e}")
                    
                    return True, "File deleted successfully"
                else:
                    return False, "Failed to delete file from MinIO"
            else:
                # Delete from local filesystem
                if os.path.exists(track_path):
                    os.remove(track_path)
                    logger.info(f"Deleted file: {os.path.basename(track_path)}")
                
                if cache_getter:
                    try:
                        cached_file = cache_getter(track_path)
                        if os.path.exists(cached_file) and cached_file != track_path:
                            os.remove(cached_file)
                            logger.debug(f"Deleted cached file: {os.path.basename(cached_file)}")
                    except Exception as e:
                        logger.debug(f"Could not delete cached file: {e}")
                
                return True, "File deleted successfully"
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False, f"Error deleting file: {str(e)}"
    
    @staticmethod
    def remove_from_library(available_tracks, track_path):
        """
        Removes a track from the available tracks list.
        
        Args:
            available_tracks (list): List of available tracks
            track_path (str): Path to the track to remove
        """
        if track_path not in available_tracks:
            return False, "Track not in library"
        
        available_tracks.remove(track_path)
        logger.info(f"Removed from library: {os.path.basename(track_path)}")
        
        return True, "Track removed from library"
    
    @staticmethod
    def validate_track_path(track_path, available_tracks):
        """
        Validates that a track path exists and is in the library.
        
        Args:
            track_path (str): Path to validate
            available_tracks (list): List of available tracks
        """
        # track_path should be relative, just check if it's in the library
        if track_path not in available_tracks:
            return False, "Track not in library"
        
        return True, ""

