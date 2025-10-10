"""
WeRadio - Track Library Manager
================================

Manages the music track library and metadata operations.

Version: 0.4
"""

import os
import io
import logging
import threading
import mutagen

from config import (
    SUPPORTED_FORMATS, CACHE_FOLDER, CACHE_MAX_SIZE,
    METADATA_CACHE_MAX_SIZE, OBJECT_STORAGE
)
from utils import (
    get_metadata, 
    CacheManager, TrackManager, StorageManager, QueueManager,
    SilenceGenerator, SILENCE_FILENAME
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
    
    def __init__(self, upload_folder, cache_folder=CACHE_FOLDER, storage_manager=None):
        """
        Initializes the track library.
        
        Args:
            upload_folder (str): Path to folder containing music tracks
            cache_folder (str): Path to cache folder for processed audio
            storage_manager: Optional StorageManager instance
        """
        self.upload_folder = upload_folder
        self.cache_folder = cache_folder
        
        # Storage manager
        self.storage_manager = storage_manager or StorageManager(use_object_storage=OBJECT_STORAGE)
        
        # Track list
        self.available_tracks = []
        
        # Metadata cache
        self.metadata_cache = {}
        self.metadata_lock = threading.Lock()
        
        # Initialize
        if not self.storage_manager.use_object_storage:
            os.makedirs(self.cache_folder, exist_ok=True)
            os.makedirs(self.upload_folder, exist_ok=True)
        
        self.load_tracks()
    
    def load_tracks(self):
        """
        Scans the uploads folder and loads all available tracks.
        If the library is empty, creates a silence placeholder file.
        """
        self.available_tracks = TrackManager.load_tracks(
            self.upload_folder, 
            SUPPORTED_FORMATS,
            self.storage_manager
        )
        
        # Create silence placeholder as fallback if empty library
        if len(self.available_tracks) == 0:
            logger.info("Library is empty, creating silence placeholder")
            success, silence_file = SilenceGenerator.ensure_silence_exists(
                self.upload_folder,
                self.storage_manager
            )
            
            if success:
                self.available_tracks = TrackManager.load_tracks(
                    self.upload_folder, 
                    SUPPORTED_FORMATS,
                    self.storage_manager
                )
                logger.info(f"✓ Silence placeholder created: {silence_file}")
            else:
                logger.error("Failed to create silence placeholder")
        
        logger.info(f"Loaded {len(self.available_tracks)} tracks")
        return self.available_tracks
    
    def get_track_metadata(self, filepath):
        """
        Gets metadata for a track with caching.
        
        Args:
            filepath (str): Relative path to audio file
        """
        if SilenceGenerator.is_silence_file(filepath):
            return {
                'title': 'Silence',
                'artist': 'WeRadio',
                'duration': 5.0,
                'filepath': filepath
            }
        
        CacheManager.clean_metadata_cache(
            self.metadata_cache, 
            METADATA_CACHE_MAX_SIZE,
            self.metadata_lock
        )
        
        cache_key = f"{self.upload_folder}/{filepath}"
        with self.metadata_lock:
            if cache_key in self.metadata_cache:
                metadata = self.metadata_cache[cache_key].copy()
                metadata['filepath'] = filepath
                return metadata
        
        if self.storage_manager.use_object_storage:
            try:
                data = self.storage_manager.read_file(filepath, self.upload_folder, 'library')
                file_obj = io.BytesIO(data)
                audio = mutagen.File(file_obj)
                
                if audio is None:
                    metadata = {
                        'title': filepath,
                        'artist': 'Unknown',
                        'duration': 0
                    }
                else:
                    title = None
                    artist = None
                    
                    # Common tag formats
                    title_tags = ['title', 'TIT2', '\xa9nam']
                    artist_tags = ['artist', 'TPE1', '\xa9ART']
                    
                    for tag_key in title_tags:
                        if tag_key in audio:
                            value = audio[tag_key]
                            title = str(value[0]) if isinstance(value, list) else str(value)
                            break
                    
                    for tag_key in artist_tags:
                        if tag_key in audio:
                            value = audio[tag_key]
                            artist = str(value[0]) if isinstance(value, list) else str(value)
                            break
                    
                    if not title or title.strip() == '':
                        title = filepath
                    if not artist or artist.strip() == '':
                        artist = 'Unknown'
                    
                    duration = audio.info.length if hasattr(audio.info, 'length') else 0
                    
                    metadata = {
                        'title': title,
                        'artist': artist,
                        'duration': float(duration)
                    }
                
                with self.metadata_lock:
                    self.metadata_cache[cache_key] = metadata
                
            except Exception as e:
                logger.error(f"Error reading metadata from MinIO for {filepath}: {e}")
                metadata = {
                    'title': filepath,
                    'artist': 'Unknown',
                    'duration': 0
                }
        else:
            abs_filepath = os.path.join(self.upload_folder, filepath)
            metadata = get_metadata(abs_filepath, self.metadata_cache, self.metadata_lock)
        
        metadata['filepath'] = filepath
        return metadata
    
    def get_clean_audio(self, filepath):
        """
        Gets a cached or creates a new AAC version of an audio file.
        
        Args:
            filepath (str): Relative file path
        """
        if self.storage_manager.use_object_storage:
            return f"minio://{filepath}"
        else:
            abs_filepath = os.path.join(self.upload_folder, filepath)
            
            return CacheManager.get_cached_audio(
                abs_filepath,
                self.cache_folder,
                self.upload_folder,
                lambda fp: get_metadata(fp, self.metadata_cache, self.metadata_lock),
                CACHE_MAX_SIZE
            )
    
    def remove_track(self, track_path, playback_queue=None):
        """
        Removes a track from the library and deletes its files.
        
        Args:
            track_path (str): Relative path to the track
            playback_queue: Optional PlaybackQueue instance to remove from queue
        """
        if SilenceGenerator.is_silence_file(track_path):
            return {
                'success': False, 
                'message': 'Cannot delete the silence placeholder. Upload a real track first.'
            }
        
        is_valid, error = TrackManager.validate_track_path(track_path, self.available_tracks)
        if not is_valid:
            return {'success': False, 'message': error}
        
        # Delete files first
        if self.storage_manager.use_object_storage:
            # Delete from MinIO
            success, message = TrackManager.delete_track_files(
                track_path,
                lambda fp: self.get_clean_audio(track_path),
                storage_manager=self.storage_manager,
                upload_folder=self.upload_folder,
                cache_folder=self.cache_folder,
                available_tracks=self.available_tracks,
                queue=None
            )
            if not success:
                return {'success': False, 'message': message}
        else:
            # Delete from local filesystem
            abs_track_path = os.path.join(self.upload_folder, track_path)
            success, message = TrackManager.delete_track_files(
                abs_track_path, 
                lambda fp: self.get_clean_audio(track_path),
                available_tracks=self.available_tracks,
                queue=None
            )
            if not success:
                return {'success': False, 'message': message}
        
        # Remove from queue if provided
        if playback_queue:
            playback_queue.remove_from_queue_if_present(track_path)
        
        # Only remove from library if file deletion succeeded
        success, message = TrackManager.remove_from_library(self.available_tracks, track_path)
        if not success:
            return {'success': False, 'message': message}
        
        logger.info(f"Removed from library: {os.path.basename(track_path)}")
        
        cache_key = f"{self.upload_folder}/{track_path}"
        with self.metadata_lock:
            self.metadata_cache.pop(cache_key, None)
        
        return {'success': True, 'message': 'Track removed from library'}
    
    def get_track_count(self):
        """
        Returns the number of tracks in the library.
        """
        return len(self.available_tracks)
    
    def remove_silence_if_exists(self, playback_queue=None):
        """
        Removes the silence placeholder file if it exists.
        Should be called when a real track is added to the library.
        """
        if SILENCE_FILENAME in self.available_tracks:
            logger.info("Removing silence placeholder (real track added)")
            
            # Remove from queue if present
            if playback_queue:
                playback_queue.remove_from_queue_if_present(SILENCE_FILENAME)
            
            success = SilenceGenerator.remove_silence_file(
                self.upload_folder,
                self.storage_manager
            )
            
            if success:
                self.available_tracks = [
                    track for track in self.available_tracks 
                    if track != SILENCE_FILENAME
                ]
                
                cache_key = f"{self.upload_folder}/{SILENCE_FILENAME}"
                with self.metadata_lock:
                    self.metadata_cache.pop(cache_key, None)
                
                logger.info("✓ Silence placeholder removed successfully")
                return True
            else:
                logger.error("Failed to remove silence placeholder file")
                return False
        
        return True