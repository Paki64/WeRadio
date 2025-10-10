"""
WeRadio - Redis Manager
========================

Manages Redis connection and state synchronization between nodes.

Version: 0.4
"""

import json
import logging
import time
import redis
from typing import Optional, Dict, List, Any

from config import (
    REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_DECODE_RESPONSES,
    REDIS_KEY_CURRENT_TRACK, REDIS_KEY_QUEUE, REDIS_KEY_AVAILABLE_TRACKS,
    REDIS_KEY_PLAYBACK_TIME
)

logger = logging.getLogger('WeRadio.RedisManager')

# Reconnection settings
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 2  # seconds


class RedisManager:
    """
    Manages Redis operations for sharing state between nodes.
    Auto-reconnects on connection loss.
    """
    _instance = None
    _redis_client = None
    _last_reconnect_attempt = 0
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Redis client init"""
        if self._redis_client is None:
            self._connect()
    
    def _connect(self) -> bool:
        """
        Establish Redis connection.
        
        Returns:
            bool: True if connected successfully
        """
        try:
            self._redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=REDIS_DECODE_RESPONSES,
                socket_connect_timeout=5,  # Connection timeout
                socket_timeout=5,          # Socket operation timeout
                retry_on_timeout=True,
                health_check_interval=30   # Health check every 30 seconds
            )
            # Test connection
            self._redis_client.ping()
            logger.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}")
            return True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self._redis_client = None
            return False
    
    def _reconnect(self) -> bool:
        """
        Attempt to reconnect to Redis
        """
        current_time = time.time()
        
        # Avoid too frequent reconnection attempts
        if current_time - self._last_reconnect_attempt < RECONNECT_DELAY:
            return False
        
        self._last_reconnect_attempt = current_time
        
        logger.warning("Attempting to reconnect to Redis...")
        
        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            if self._connect():
                logger.info(f"Redis reconnected successfully after {attempt} attempt(s)")
                return True
            
            if attempt < MAX_RECONNECT_ATTEMPTS:
                wait_time = RECONNECT_DELAY * attempt  # Exponential backoff
                logger.warning(f"Reconnection attempt {attempt} failed, retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        logger.error(f"Failed to reconnect to Redis after {MAX_RECONNECT_ATTEMPTS} attempts")
        return False
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected without attempting reconnection."""
        if self._redis_client is None:
            return False
        
        try:
            self._redis_client.ping()
            return True
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis connection lost: {e}")
            self._redis_client = None
            return False
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    def _execute_with_retry(self, operation, *args, **kwargs):
        """
        Execute Redis operation with automatic retry on connection failure.
        
        Args:
            operation: Redis operation function
            *args, **kwargs: Arguments for the operation
        """
        # Two attempts: initial and one retry after reconnect
        if not self.is_connected:
            if not self._reconnect():
                return None
        
        try:
            return operation(*args, **kwargs)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis operation failed: {e}")
            self._redis_client = None
            
            if self._reconnect():
                try:
                    return operation(*args, **kwargs)
                except Exception as retry_error:
                    logger.error(f"Retry operation failed: {retry_error}")
                    return None
            
            return None
        except Exception as e:
            logger.error(f"Redis operation error: {e}")
            return None
    
    # === CURRENT TRACK ===
    
    def set_current_track(self, metadata: Dict[str, Any]) -> bool:
        """
        Set current track metadata.
        
        Args:
            metadata: Dictionary with track metadata (title, artist, duration, etc.)
        """
        result = self._execute_with_retry(
            lambda: self._redis_client.set(
                REDIS_KEY_CURRENT_TRACK,
                json.dumps(metadata),
                ex=3600  # Expire after 1 hour
            )
        )
        return result is not None
    
    def get_current_track(self) -> Optional[Dict[str, Any]]:
        """
        Get current track metadata.
        
        Returns:
            Dictionary with track metadata or None
        """
        data = self._execute_with_retry(
            lambda: self._redis_client.get(REDIS_KEY_CURRENT_TRACK)
        )
        
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding current track: {e}")
        
        return None
    
    # === PLAYBACK TIME ===
    
    def set_playback_time(self, time: float) -> bool:
        """
        Set current playback time.
        
        Args:
            time: Current playback time in seconds
        """
        result = self._execute_with_retry(
            lambda: self._redis_client.set(REDIS_KEY_PLAYBACK_TIME, str(time), ex=3600)
        )
        return result is not None
    
    def get_playback_time(self) -> float:
        """
        Get current playback time.
        """
        data = self._execute_with_retry(
            lambda: self._redis_client.get(REDIS_KEY_PLAYBACK_TIME)
        )
        
        if data:
            try:
                return float(data)
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing playback time: {e}")
        
        return 0.0
    
    # === QUEUE ===
    
    def set_queue(self, queue: List[str]) -> bool:
        """
        Set the playback queue.
        
        Args:
            queue: List of track filepaths
        """
        result = self._execute_with_retry(
            lambda: self._redis_client.set(REDIS_KEY_QUEUE, json.dumps(queue), ex=3600)
        )
        return result is not None
    
    def get_queue(self) -> List[str]:
        """
        Get the playback queue.
        """
        data = self._execute_with_retry(
            lambda: self._redis_client.get(REDIS_KEY_QUEUE)
        )
        
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding queue: {e}")
        
        return []
    
    def add_to_queue(self, filepath: str) -> bool:
        """
        Add a track to the queue (via Redis pub/sub command).
        
        Args:
            filepath: Track filepath to add
        """
        result = self._execute_with_retry(
            lambda: self._redis_client.publish(
                'weradio:commands',
                json.dumps({'action': 'add_to_queue', 'filepath': filepath})
            )
        )
        return result is not None
    
    def remove_from_queue(self, filepath: str) -> bool:
        """
        Remove a track from the queue (via Redis pub/sub command).
        
        Args:
            filepath: Track filepath to remove
        """
        result = self._execute_with_retry(
            lambda: self._redis_client.publish(
                'weradio:commands',
                json.dumps({'action': 'remove_from_queue', 'filepath': filepath})
            )
        )
        return result is not None
    
    # === AVAILABLE TRACKS ===
    
    def set_available_tracks(self, tracks: List[Dict[str, Any]]) -> bool:
        """
        Set the list of available tracks.
        
        Args:
            tracks: List of track metadata dictionaries
        """
        result = self._execute_with_retry(
            lambda: self._redis_client.set(REDIS_KEY_AVAILABLE_TRACKS, json.dumps(tracks), ex=3600)
        )
        return result is not None
    
    def get_available_tracks(self) -> List[Dict[str, Any]]:
        """
        Get the list of available tracks.
        """
        data = self._execute_with_retry(
            lambda: self._redis_client.get(REDIS_KEY_AVAILABLE_TRACKS)
        )
        
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding available tracks: {e}")
        
        return []
    
    def publish_reload_tracks(self) -> bool:
        """
        Publish command to reload tracks from disk.
        """
        result = self._execute_with_retry(
            lambda: self._redis_client.publish(
                'weradio:commands',
                json.dumps({'action': 'reload_tracks'})
            )
        )
        return result is not None


# Singleton instance
redis_manager = RedisManager()
