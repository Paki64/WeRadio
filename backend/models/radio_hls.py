"""
WeRadio - RadioHLS Coordinator
================================

Main coordinator class that integrates library, queue, and streaming components.

Version: 0.2
Nota: gestito solo dal nodo streamer
"""

import os
import logging
import threading

from config import UPLOAD_FOLDER, HLS_FOLDER
from .track_library import TrackLibrary
from .playback_queue import PlaybackQueue
from .hls_streamer import HLSStreamer
from utils import redis_manager


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
        
        # Redis synchronization
        self._redis_sync_thread = None
        self._redis_sync_running = False
        self._redis_command_thread = None
        self._redis_command_running = False
        
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
        # Start Redis synchronization
        self._start_redis_sync()
        self._start_redis_command_listener()
    
    def stop(self):
        """Stops HLS streaming."""
        self._stop_redis_command_listener()
        self._stop_redis_sync()
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
    
    # === Redis synchronization ===
    
    def _start_redis_sync(self):
        """Starts Redis synchronization thread."""
        if redis_manager.is_connected:
            self._redis_sync_running = True
            self._redis_sync_thread = threading.Thread(target=self._redis_sync_loop, daemon=True)
            self._redis_sync_thread.start()
            logger.info("Redis sync thread started")
            logger.info("Redis synchronization started")
        else:
            logger.warning("Redis not available, synchronization disabled")
    
    def _stop_redis_sync(self):
        """Stops Redis synchronization thread."""
        self._redis_sync_running = False
        if self._redis_sync_thread:
            self._redis_sync_thread.join(timeout=2)
            logger.info("Redis synchronization stopped")
    
    def _redis_sync_loop(self):
        """Synchronization loop that publishes state to Redis."""
        import time
        
        while self._redis_sync_running:
            try:
                # Publish current track metadata
                if self.current_metadata:
                    redis_manager.set_current_track(self.current_metadata)
                
                # Publish playback time
                current_time = self.get_current_playback_time()
                redis_manager.set_playback_time(current_time)
                
                # Publish queue
                queue_list = list(self.queue)
                redis_manager.set_queue(queue_list)
                
                # Publish available tracks with metadata
                tracks_with_meta = []
                for track in self.available_tracks:
                    meta = self._get_track_metadata(track)
                    tracks_with_meta.append(meta)
                redis_manager.set_available_tracks(tracks_with_meta)
                
                # Sleep for 1 second before next update
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in Redis sync loop: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _start_redis_command_listener(self):
        """Starts Redis command listener thread."""
        if redis_manager.is_connected:
            self._redis_command_running = True
            self._redis_command_thread = threading.Thread(target=self._redis_command_loop, daemon=True)
            self._redis_command_thread.start()
            logger.info("Redis command listener started")
    
    def _stop_redis_command_listener(self):
        """Stops Redis command listener thread."""
        self._redis_command_running = False
        if self._redis_command_thread:
            self._redis_command_thread.join(timeout=2)
            logger.info("Redis command listener stopped")
    
    def _redis_command_loop(self):
        """Listens for commands from Redis pub/sub."""
        import json
        
        try:
            # Create a new Redis connection for pub/sub
            import redis
            from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
            
            pubsub_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True
            )
            
            pubsub = pubsub_client.pubsub()
            pubsub.subscribe('weradio:commands')
            
            logger.info("Subscribed to weradio:commands channel")
            
            for message in pubsub.listen():
                if not self._redis_command_running:
                    break
                
                if message['type'] == 'message':
                    try:
                        command = json.loads(message['data'])
                        action = command.get('action')
                        
                        if action == 'add_to_queue':
                            filepath = command.get('filepath')
                            logger.info(f"Redis command: add_to_queue {filepath}")
                            # Usa il metodo interno della coda
                            from utils import QueueManager
                            from config import QUEUE_SIZE
                            with self.playlist_lock:
                                QueueManager.add_track_to_queue(
                                    self.queue,
                                    filepath,
                                    self.available_tracks,
                                    QUEUE_SIZE
                                )
                        
                        elif action == 'remove_from_queue':
                            filepath = command.get('filepath')
                            logger.info(f"Redis command: remove_from_queue {filepath}")
                            self.remove_from_queue(filepath)
                        
                        elif action == 'reload_tracks':
                            logger.info("Redis command: reload_tracks")
                            self.load_available_tracks()
                        
                    except Exception as e:
                        logger.error(f"Error processing Redis command: {e}")
            
        except Exception as e:
            logger.error(f"Error in Redis command listener: {e}")
        finally:
            try:
                pubsub.close()
            except:
                pass
