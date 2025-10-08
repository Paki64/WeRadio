"""
WeRadio - Playback Queue Manager
==================================

Manages the playback queue for track streaming.

Version: 0.1
"""

import os
import logging
import threading
from collections import deque

from config import QUEUE_SIZE
from utils import QueueManager


logger = logging.getLogger('WeRadio.PlaybackQueue')


class PlaybackQueue:
    """
    Manages the playback queue.
    
    Responsibilities:
    - Initialize and maintain playback queue
    - Add/remove tracks from queue
    - Provide queue information
    - Handle auto-refill logic
    """
    
    def __init__(self, track_library):
        """
        Initializes the playback queue.
        
        Args:
            track_library (TrackLibrary): Reference to track library instance
        """
        self.track_library = track_library
        self.queue = deque()
        self.queue_lock = threading.Lock()
        
        # Initialize queue
        self.initialize()
    
    def initialize(self):
        """
        Initializes the playback queue with one random track.
        """
        with self.queue_lock:
            self.queue = QueueManager.initialize_queue(
                self.track_library.available_tracks
            )
    
    def refill_if_empty(self):
        """
        Adds a random track ONLY if the queue is empty.
        """
        with self.queue_lock:
            QueueManager.refill_queue_if_empty(
                self.queue, 
                self.track_library.available_tracks
            )
    
    def get_next_track(self):
        """
        Gets and removes the next track from the queue.
        
        Returns:
            str or None: Relative path to next track, or None if queue is empty
        """
        with self.queue_lock:
            if not self.queue:
                return None
            try:
                return self.queue.popleft()
            except IndexError:
                return None
    
    def add_track(self, track_path):
        """
        Adds a track to the front of the queue (will play next).
        
        Args:
            track_path (str): Relative path to the track
            
        Returns:
            tuple: (success: bool, message: str)
        """
        with self.queue_lock:
            success, message = QueueManager.add_track_to_queue(
                self.queue,
                track_path,
                self.track_library.available_tracks,
                QUEUE_SIZE
            )
            return success, message
    
    def remove_track(self, track_path):
        """
        Removes a track from the queue.
        
        Args:
            track_path (str): Relative path to the track
            
        Returns:
            tuple: (success: bool, message: str)
        """
        with self.queue_lock:
            success, message = QueueManager.remove_track_from_queue(
                self.queue, 
                track_path, 
                self.track_library.available_tracks
            )
            return success, message
    
    def get_info(self):
        """
        Gets formatted information about the current queue.
        
        Returns:
            dict: Queue information with keys 'queue', 'length', 'next_track'
        """
        with self.queue_lock:
            return QueueManager.get_queue_info(
                self.queue, 
                self.track_library.get_track_metadata
            )
    
    def is_track_in_queue(self, track_path):
        """
        Checks if a track is in the queue.
        
        Args:
            track_path (str): Relative path to check
            
        Returns:
            bool: True if track is in queue
        """
        with self.queue_lock:
            return track_path in self.queue
    
    def remove_from_queue_if_present(self, track_path):
        """
        Removes a track from queue if present (no error if not found).
        
        Args:
            track_path (str): Relative path to the track
        """
        with self.queue_lock:
            if track_path in self.queue:
                self.queue.remove(track_path)
                logger.info(f"Removed from queue: {os.path.basename(track_path)}")
    
    def is_empty(self):
        """
        Checks if the queue is empty.
        
        Returns:
            bool: True if queue is empty
        """
        with self.queue_lock:
            return len(self.queue) == 0
    
    def get_length(self):
        """
        Returns the current queue length.
        
        Returns:
            int: Number of tracks in queue
        """
        with self.queue_lock:
            return len(self.queue)
