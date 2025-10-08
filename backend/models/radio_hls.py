"""
WeRadio - RadioHLS Coordinator
================================

Main coordinator class that integrates library, queue, and streaming components.

Version: 0.1
"""

import os
import logging

from config import UPLOAD_FOLDER, HLS_FOLDER
from .track_library import TrackLibrary
from .playback_queue import PlaybackQueue
from .hls_streamer import HLSStreamer


logger = logging.getLogger('WeRadio.RadioHLS')


class RadioHLS:
    """
    Main coordinator for HLS radio streaming.
    
    Integrates three components:
    - TrackLibrary: Manages music files and metadata
    - PlaybackQueue: Manages playback order
    - HLSStreamer: Handles FFmpeg streaming
    """
    
    def __init__(self, upload_folder=UPLOAD_FOLDER, hls_folder=HLS_FOLDER):
        """
        Initializes the HLS radio system.
        
        Args:
            upload_folder (str): Path to folder containing music tracks
            hls_folder (str): Path to output folder for HLS segments
        """
        self.upload_folder = upload_folder
        self.hls_folder = hls_folder
        
        # Initialize components
        self.track_library = TrackLibrary(upload_folder)
        self.playback_queue = PlaybackQueue(self.track_library)
        self.hls_streamer = HLSStreamer(hls_folder, self.track_library, self.playback_queue)
        
        logger.info("RadioHLS initialized with modular components")
    
    # === Properties ===
    
    @property
    def available_tracks(self):
        """Returns available tracks from library."""
        return self.track_library.available_tracks
    
    @property
    def queue(self):
        """Returns the playback queue."""
        return self.playback_queue.queue
    
    @property
    def playlist_lock(self):
        """Returns the queue lock."""
        return self.playback_queue.queue_lock
    
    @property
    def playing(self):
        """Returns streaming status."""
        return self.hls_streamer.playing
    
    @property
    def current_metadata(self):
        """Returns current track metadata."""
        return self.hls_streamer.current_metadata
    
    @property
    def ffmpeg_process(self):
        """Returns FFmpeg process."""
        return self.hls_streamer.ffmpeg_process
    
    # === Library operations ===
    
    def load_available_tracks(self):
        """Reloads the track library."""
        return self.track_library.load_tracks()
    
    def _get_track_metadata(self, filepath):
        """Gets metadata for a track (internal compatibility method)."""
        return self.track_library.get_track_metadata(filepath)
    
    # === Streaming operations ===
    
    def start_streaming(self):
        """Starts HLS streaming."""
        self.hls_streamer.start()
    
    def stop(self):
        """Stops HLS streaming."""
        self.hls_streamer.stop()
    
    def get_current_playback_time(self):
        """Gets current playback time."""
        return self.hls_streamer.get_current_playback_time()
    
    # === Queue operations ===
    
    def get_queue_info(self):
        """Gets current queue information."""
        return self.playback_queue.get_info()
    
    # === Track operations ===
    
    def remove_track(self, track_path):
        """
        Removes a track completely: from library, queue, and deletes file.
        Skips to next track if currently playing.
        
        Args:
            track_path (str): Relative path to the track
            
        Returns:
            dict: Response with 'success' and 'message' keys
        """
        try:
            # Remove from library
            success, message = self.track_library.remove_track(track_path)
            if not success:
                return {'success': False, 'message': message}
            
            currently_playing = False
            
            # Remove from queue if present
            self.playback_queue.remove_from_queue_if_present(track_path)
            
            # Skip if currently playing
            if self.hls_streamer.is_currently_playing(track_path):
                currently_playing = True
                self.hls_streamer.skip_current_track()
            
            # Refill queue if empty
            self.playback_queue.refill_if_empty()
            
            response_message = 'Track removed successfully'
            if currently_playing:
                response_message += ' (was playing, skipped to next)'
            
            return {'success': True, 'message': response_message}
            
        except Exception as e:
            logger.error(f"Error removing track: {e}")
            return {'success': False, 'message': str(e)}
    
    def remove_from_queue(self, track_path):
        """
        Removes a track from queue only.
        
        Args:
            track_path (str): Relative path to the track
            
        Returns:
            dict: Response with 'success' and 'message' keys
        """
        try:
            success, message = self.playback_queue.remove_track(track_path)
            
            if not success:
                return {'success': False, 'message': message}
            
            # Refill if queue is empty
            self.playback_queue.refill_if_empty()
            
            return {'success': True, 'message': message}
            
        except Exception as e:
            logger.error(f"Error removing track from queue: {e}")
            return {'success': False, 'message': str(e)}

