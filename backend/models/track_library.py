"""
WeRadio - Track Library Manager
================================

Manages the music track library and metadata operations.

Version: 0.2
"""

import os
import logging
import threading

from config import (
    SUPPORTED_FORMATS, CACHE_FOLDER, CACHE_MAX_SIZE,
    METADATA_CACHE_MAX_SIZE
)
from utils import (
    get_metadata, 
    CacheManager, TrackManager
)


logger = logging.getLogger('WeRadio.TrackLibrary')


class TrackLibrary:
    """
    Manages the music track library.
    
    Responsibilities:
    - Load and track available music files
    - Manage metadata cache
    - Handle track addition/removal
    - Provide audio file caching
    """
    
    def __init__(self, upload_folder, cache_folder=CACHE_FOLDER):
        """
        Initializes the track library.
        
        Args:
            upload_folder (str): Path to folder containing music tracks
            cache_folder (str): Path to cache folder for processed audio
        """
        self.upload_folder = upload_folder
        self.cache_folder = cache_folder
        
        # Track list
        self.available_tracks = []
        
        # Metadata cache
        self.metadata_cache = {}
        self.metadata_lock = threading.Lock()
        
        # Initialize
        os.makedirs(self.cache_folder, exist_ok=True)
        os.makedirs(self.upload_folder, exist_ok=True)
        self.load_tracks()
    
    def load_tracks(self):
        """
        Scans the uploads folder and loads all available tracks.
        
        Returns:
            list: List of relative paths to available tracks
        """
        self.available_tracks = TrackManager.load_tracks(
            self.upload_folder, 
            SUPPORTED_FORMATS
        )
        logger.info(f"Loaded {len(self.available_tracks)} tracks")
        return self.available_tracks
    
    def get_track_metadata(self, filepath):
        """
        Gets metadata for a track with caching.
        
        Args:
            filepath (str): Relative path to audio file
            
        Returns:
            dict: Metadata with keys 'title', 'artist', 'duration', 'filepath'
        """
        abs_filepath = os.path.join(self.upload_folder, filepath)
        
        CacheManager.clean_metadata_cache(
            self.metadata_cache, 
            METADATA_CACHE_MAX_SIZE,
            self.metadata_lock
        )
        
        metadata = get_metadata(abs_filepath, self.metadata_cache, self.metadata_lock)
        metadata['filepath'] = filepath
        
        return metadata
    
    def get_clean_audio(self, filepath):
        """
        Gets a cached or creates a new AAC version of an audio file.
        
        Args:
            filepath (str): Relative file path
            
        Returns:
            str: Absolute path to cleaned/cached file
        """
        abs_filepath = os.path.join(self.upload_folder, filepath)
        
        return CacheManager.get_cached_audio(
            abs_filepath,
            self.cache_folder,
            self.upload_folder,
            lambda fp: get_metadata(fp, self.metadata_cache, self.metadata_lock),
            CACHE_MAX_SIZE
        )
    
    def remove_track(self, track_path):
        """
        Removes a track from the library and deletes its files.
        
        Args:
            track_path (str): Relative path to the track
            
        Returns:
            tuple: (success: bool, message: str)
        """
        # Validate track
        is_valid, error = TrackManager.validate_track_path(track_path, self.available_tracks)
        if not is_valid:
            return False, error
        
        # Remove from library
        TrackManager.remove_from_library(self.available_tracks, track_path)
        logger.info(f"Removed from library: {os.path.basename(track_path)}")
        
        # Delete files
        abs_track_path = os.path.join(self.upload_folder, track_path)
        TrackManager.delete_track_files(abs_track_path, lambda fp: self.get_clean_audio(track_path))
        
        # Clean metadata cache
        with self.metadata_lock:
            self.metadata_cache.pop(abs_track_path, None)
        
        return True, "Track removed from library"
    
    def is_track_in_library(self, track_path):
        """
        Checks if a track is in the library.
        
        Args:
            track_path (str): Relative path to check
            
        Returns:
            bool: True if track is in library
        """
        return track_path in self.available_tracks
    
    def get_track_count(self):
        """
        Returns the number of tracks in the library.
        
        Returns:
            int: Number of tracks
        """
        return len(self.available_tracks)
