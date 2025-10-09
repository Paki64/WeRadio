"""
WeRadio - Queue Management Utilities
=====================================

Utilities for managing playback queue operations.
Handles queue initialization, refilling, and track selection.

Version: 0.2
"""

import logging
import random
import os
from collections import deque

logger = logging.getLogger('WeRadio.QueueManager')


class QueueManager:
    """
    Manages the playback queue for the radio streaming system.
    """
    
    @staticmethod
    def initialize_queue(available_tracks):
        """
        Initializes the playback queue with one random track.
        
        Args:
            available_tracks (list): List of available track paths
            
        Returns:
            deque: New queue with initial track, or empty if no tracks available
        """
        queue = deque()
        
        if len(available_tracks) == 0:
            logger.warning("No tracks available for queue initialization")
            return queue
        
        # Start with just 1 random track
        selected = random.choice(available_tracks)
        queue.append(selected)
        logger.info(f"Queue initialized with 1 track: {os.path.basename(selected)}")
        
        return queue
    
    @staticmethod
    def refill_queue_if_empty(queue, available_tracks):
        """
        Adds a random track if the queue is empty.
        
        Args:
            queue (deque): The current queue
            available_tracks (list): List of available track paths            
        """
        # Only refill if queue is completely empty
        if len(queue) > 0:
            logger.debug(f"Queue not empty ({len(queue)} tracks), skipping auto-refill")
            return False
        
        if len(available_tracks) == 0:
            logger.warning("No tracks available to refill queue")
            return False
        
        # Add one random track when queue is empty
        new_track = random.choice(available_tracks)
        queue.append(new_track)
        logger.info(f"Queue was empty, added random track: {os.path.basename(new_track)}")
        
        return True
    
    @staticmethod
    def get_queue_info(queue, metadata_getter):
        """
        Gets formatted information about the current queue.
        
        Args:
            queue (deque): The current queue
            metadata_getter (callable): Function to get metadata for a track
            
        Returns:
            dict: Queue information with keys 'queue', 'length', 'next_track'
        """
        queue_list = []
        for track in queue:
            meta = metadata_getter(track)
            display_name = f"{meta['artist']} - {meta['title']}" if meta['title'] != 'Unknown' else os.path.basename(track)
            queue_list.append(display_name)
        
        next_track_info = metadata_getter(list(queue)[0]) if queue else None
        
        return {
            'queue': queue_list,
            'length': len(queue),
            'next_track': next_track_info
        }
    
    @staticmethod
    def add_track_to_queue(queue, track_path, available_tracks, max_queue_size):
        """
        Adds a track to the front of the queue (will play next).
        
        Args:
            queue (deque): The current queue
            track_path (str): Path to the track to add
            available_tracks (list): List of available tracks
            max_queue_size (int): Maximum allowed queue size
            
        Returns:
            tuple: (success: bool, message: str)
        """
        # Check queue limit
        if len(queue) >= max_queue_size:
            return False, f"Queue is full (max: {max_queue_size})"
        
        # Verify track exists in library
        if track_path not in available_tracks:
            return False, "Track not in library"
        
        # Avoid duplicates
        if track_path in queue:
            return False, "Track already in queue"
        
        # Add to front of queue (will play next)
        queue.appendleft(track_path)
        logger.info(f"Added to queue: {os.path.basename(track_path)}")
        
        return True, "Track added to queue"
    
    @staticmethod
    def remove_track_from_queue(queue, track_path, available_tracks):
        """
        Removes a track from the queue only (keeps file in library).
        
        Args:
            queue (deque): The current queue
            track_path (str): Path to the track to remove
            available_tracks (list): List of available tracks
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if track_path not in available_tracks:
            return False, "Track not in library"
        
        if track_path not in queue:
            return False, "Track not in queue"
        
        queue.remove(track_path)
        logger.info(f"Removed from queue: {os.path.basename(track_path)}")
        
        return True, "Track removed from queue"
