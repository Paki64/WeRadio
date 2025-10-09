"""
WeRadio - HLS Streamer
=======================

Manages HLS streaming with FFmpeg.

Version: 0.2
"""

import os
import time
import logging
import subprocess
import shutil
import threading

from config import (
    SEGMENT_DURATION, HLS_LIST_SIZE, HLS_CLIENT_BUFFER_DELAY
)


logger = logging.getLogger('WeRadio.HLSStreamer')


class HLSStreamer:
    """
    Manages HLS streaming using FFmpeg.
    
    Responsibilities:
    - Handle FFmpeg streaming process
    - Manage HLS segments and playlist
    - Track playback state and timing
    - Clean up old segments
    """
    
    def __init__(self, hls_folder, track_library, playback_queue):
        """
        Initializes the HLS streamer.
        
        Args:
            hls_folder (str): Path to output folder for HLS segments
            track_library (TrackLibrary): Reference to track library
            playback_queue (PlaybackQueue): Reference to playback queue
        """
        self.hls_folder = hls_folder
        self.track_library = track_library
        self.playback_queue = playback_queue
        
        # Streaming state
        self.current_segment_number = 0
        self.track_segment_start = 0
        self.playing = False
        self.stream_thread = None
        self.ffmpeg_process = None
        self.track_start_time = None
        
        # Default track metadata
        self.current_metadata = {
            'title': 'Unknown',
            'artist': 'Unknown',
            'duration': 0
        }
        
        # Initialize HLS folder
        self._initialize_hls_folder()
    
    def _initialize_hls_folder(self):
        """Creates/cleans HLS output folder."""
        if os.path.exists(self.hls_folder):
            shutil.rmtree(self.hls_folder)
        os.makedirs(self.hls_folder, exist_ok=True)
        logger.info("HLS folder initialized")
    
    def start(self):
        """
        Starts the HLS streaming system.
        """
        if self.playing:
            logger.warning("Streaming already active")
            return
        
        if self.track_library.get_track_count() == 0:
            logger.warning("No tracks available for streaming")
            return
        
        self.playing = True
        self.stream_thread = threading.Thread(target=self._streaming_loop, daemon=True)
        self.stream_thread.start()
        
        logger.info("HLS streaming started")
    
    def stop(self):
        """
        Stops the streaming system.
        """
        logger.info("Stopping HLS streaming...")
        self.playing = False
        
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("FFmpeg didn't stop gracefully, killing...")
                self.ffmpeg_process.kill()
        
        logger.info("HLS streaming stopped")
    
    def get_current_playback_time(self):
        """
        Calculates current playback time with client buffer adjustment.
        
        Returns:
            float: Current time in seconds (adjusted for client delay)
        """
        if self.track_start_time and self.playing:
            elapsed = time.time() - self.track_start_time
            duration = self.current_metadata.get('duration', 0)
            
            # Subtract client buffer delay
            adjusted_time = max(0, elapsed - HLS_CLIENT_BUFFER_DELAY)
            
            return min(adjusted_time, duration) if duration > 0 else adjusted_time
        return 0
    
    def skip_current_track(self):
        """
        Skips the currently playing track.
        
        Returns:
            bool: True if skip was successful
        """
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
            logger.info("Skipped current track")
            return True
        return False
    
    def is_currently_playing(self, track_path):
        """
        Checks if a specific track is currently playing.
        
        Args:
            track_path (str): Relative path to check
            
        Returns:
            bool: True if this track is currently playing
        """
        return (self.ffmpeg_process and 
                self.ffmpeg_process.poll() is None and
                self.current_metadata.get('filepath') == track_path)
    
    def _streaming_loop(self):
        """
        Main streaming loop that processes tracks with FFmpeg.
        Runs in a background thread.
        """
        while self.playing:
            # Check if queue is empty
            if self.playback_queue.is_empty():
                logger.warning("Queue empty, attempting reload...")
                if self.track_library.get_track_count() > 0:
                    self.playback_queue.initialize()
            
            # Check again after reload attempt
            if self.playback_queue.is_empty():
                logger.warning("Still no tracks available, waiting...")
                time.sleep(5)
                continue
            
            # Get next track
            track = self.playback_queue.get_next_track()
            if not track:
                logger.warning("Failed to get next track, retrying...")
                time.sleep(1)
                continue
            
            if not self.playing:
                break
            
            logger.info(f"Next from queue: {os.path.basename(track)}")
            
            # Get metadata and prepare track
            meta = self.track_library.get_track_metadata(track)
            logger.info(f"Preparing: {meta['artist']} - {meta['title']}")
            
            clean_track = self.track_library.get_clean_audio(track)
            self.playback_queue.refill_if_empty()
            
            # Stream the track
            self._stream_track(clean_track, meta)
    
    def _cleanup_old_segments(self, current_start_number):
        """
        Removes old segment files that are no longer needed.
        
        Args:
            current_start_number (int): The segment number where the new track will start
        """
        try:
            if not os.path.exists(self.hls_folder):
                return
            
            playlist_path = os.path.join(self.hls_folder, 'playlist.m3u8')
            if not os.path.exists(playlist_path):
                logger.debug("Playlist not found, skipping cleanup")
                return
            
            # Read playlist and extract referenced segments
            with open(playlist_path, 'r') as f:
                playlist_content = f.read()
            
            segments_in_playlist = set()
            for line in playlist_content.splitlines():
                line = line.strip()
                if line.startswith('segment_') and line.endswith('.ts'):
                    segments_in_playlist.add(line)
            
            # Get all segment files on disk
            all_segment_files = set(f for f in os.listdir(self.hls_folder) 
                                   if f.startswith('segment_') and f.endswith('.ts'))
            
            # Find segments to remove (on disk but not in playlist)
            segments_to_remove = all_segment_files - segments_in_playlist
            
            cleaned_count = 0
            for segment_file in segments_to_remove:
                try:
                    segment_path = os.path.join(self.hls_folder, segment_file)
                    os.remove(segment_path)
                    cleaned_count += 1
                    logger.debug(f"Cleaned up old segment: {segment_file}")
                except OSError as e:
                    logger.warning(f"Error cleaning segment {segment_file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old segments")
                    
        except Exception as e:
            logger.error(f"Error during segment cleanup: {e}")
    
    def _stream_track(self, track_path, metadata):
        """
        Streams a single track using FFmpeg.
        
        Args:
            track_path (str): Absolute path to the audio file
            metadata (dict): Track metadata
        """
        try:
            segment_filename = os.path.join(self.hls_folder, 'segment_%03d.ts')
            playlist_filename = os.path.join(self.hls_folder, 'playlist.m3u8')
            ffmpeg_log = os.path.join(self.hls_folder, 'ffmpeg.log')
            
            start_number = self.current_segment_number
            self.track_segment_start = start_number
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-re',
                '-i', track_path,
                '-c:a', 'copy',
                '-f', 'hls',
                '-hls_time', str(SEGMENT_DURATION),
                '-hls_list_size', str(HLS_LIST_SIZE),
                '-hls_flags', 'delete_segments+append_list+omit_endlist',
                '-hls_segment_type', 'mpegts',
                '-hls_segment_filename', segment_filename,
                '-start_number', str(start_number),
                '-hls_allow_cache', '0',
                playlist_filename
            ]
            
            logger.debug("Starting FFmpeg for track...")
            
            # Start FFmpeg process
            with open(ffmpeg_log, 'w') as log_file:
                self.ffmpeg_process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
                
                # Update current metadata
                self.current_metadata = metadata
                self.track_start_time = time.time()
                logger.info(f"Now Playing: {metadata['artist']} - {metadata['title']}")
                
                # Wait for initial segments
                time.sleep(SEGMENT_DURATION * 3)
                
                # Clean up old segments
                self._cleanup_old_segments(start_number)
                
                # Wait for FFmpeg to complete
                self.ffmpeg_process.wait()
            
            logger.info("Track completed")
            
            # Small delay
            time.sleep(1.5)
            
            # Update segment counter
            try:
                segments_in_track = int(metadata.get('duration', 180) / SEGMENT_DURATION) + 1
                self.current_segment_number += segments_in_track
                logger.debug(f"Next start: {self.current_segment_number}")
            except Exception as e:
                logger.warning(f"Error calculating next segment number: {e}")
                self.current_segment_number += 1
            
        except Exception as e:
            logger.error(f"FFmpeg error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            time.sleep(2)
