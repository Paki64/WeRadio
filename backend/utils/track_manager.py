"""
WeRadio - Track Management Utilities
=====================================

Utilities for managing music track files.

Version: 0.1
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger('WeRadio.TrackManager')


class TrackManager:
    """
    Manages music track files and library operations.
    """
    
    @staticmethod
    def load_tracks(upload_folder, supported_formats):
        """
        Scans the uploads folder and loads all available tracks.
        
        Args:
            upload_folder (str): Path to the upload folder
            supported_formats (set): Set of supported file extensions
            
        Returns:
            list: List of relative paths to all available tracks
        """
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
        
        logger.info(f"{len(files)} tracks found in library")
        return files
    
    @staticmethod
    def delete_track_files(track_path, cache_getter=None):
        """
        Deletes a track file and its cached version.
        
        Args:
            track_path (str): Path to the track to delete
            cache_getter (callable, optional): Function to get cached file path
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Delete original file
            if os.path.exists(track_path):
                os.remove(track_path)
                logger.info(f"Deleted file: {os.path.basename(track_path)}")
            
            # Try to remove cached version if cache_getter provided
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
            
        Returns:
            tuple: (success: bool, message: str)
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
            
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        # track_path should be relative, just check if it's in the library
        if track_path not in available_tracks:
            return False, "Track not in library"
        
        return True, ""
    
    @staticmethod
    def is_track_file(filename, supported_formats):
        """
        Checks if a file is a supported audio track.
        
        Args:
            filename (str): Filename to check
            supported_formats (set): Set of supported extensions
            
        Returns:
            bool: True if file is a supported audio format
        """
        ext = os.path.splitext(filename)[1].lower()
        return ext in supported_formats
