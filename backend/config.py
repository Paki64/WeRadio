"""
WeRadio - Configuration Module
================================

Centralizes all configuration parameters for the WeRadio application.
This module contains all constants and settings used throughout the application.

Configuration can be overridden via environment variables:
- WERADIO_PORT: Server port (default: 5000)
- WERADIO_HOST: Server host (default: 0.0.0.0)
- WERADIO_QUEUE_SIZE: Queue size (default: 100)
- WERADIO_DEBUG: Debug mode (default: False)
- STREAMER: Enable streamer mode with HLS/FFmpeg (default: true)
            Set to "false" for API-only nodes in HPA deployments

Version: 0.2
"""

import os

# === FOLDER PATHS ===
UPLOAD_FOLDER = os.path.abspath('data/library')
HLS_FOLDER = os.path.abspath('data/hls_output')
CACHE_FOLDER = os.path.abspath('data/audio_cache')

# === AUDIO FORMATS ===
SUPPORTED_FORMATS = {'.mp3', '.flac', '.ogg', '.wav', '.aac', '.m4a'}

# === HLS STREAMING SETTINGS ===
SEGMENT_DURATION = 2                                      # Duration of each HLS segment in seconds
QUEUE_SIZE = int(os.getenv('WERADIO_QUEUE_SIZE', '100'))  # Maximum queue size (minimum is 1)
HLS_LIST_SIZE = 20                                        # Number of segments in the HLS playlist buffer
HLS_CLIENT_BUFFER_DELAY = 10                              # Estimated client buffering delay in seconds

# === AUDIO ENCODING SETTINGS ===
AAC_BITRATE = '128k'   # Bitrate for AAC encoding
SAMPLE_RATE = '44100'  # Sample rate in Hz
AUDIO_CHANNELS = '2'   # Number of audio channels (stereo)

# === SYSTEM LIMITS ===
CONVERSION_TIMEOUT = 120             # Timeout for audio conversion in seconds
MAX_UPLOAD_SIZE = 300 * 1024 * 1024  # Maximum upload file size (300MB)
CACHE_MAX_SIZE = 50                  # Maximum number of cached audio files
METADATA_CACHE_MAX_SIZE = 200        # Maximum number of metadata entries in cache

# === FLASK SETTINGS ===
FLASK_HOST = os.getenv('WERADIO_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('WERADIO_PORT', '5000'))
FLASK_DEBUG = os.getenv('WERADIO_DEBUG', 'False').lower() in ('true', '1', 'yes')
FLASK_THREADED = True

# === ARCHITECTURE MODE ===
# - true  = Streamer node
# - false = API-only node
STREAMER_MODE = os.getenv('STREAMER', 'true').lower() in ('true', '1', 'yes')

# === REDIS SETTINGS ===
# Redis is used to share state between streamer and API nodes
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
REDIS_DECODE_RESPONSES = True
# Redis keys
REDIS_KEY_CURRENT_TRACK = 'weradio:current_track'
REDIS_KEY_QUEUE = 'weradio:queue'
REDIS_KEY_AVAILABLE_TRACKS = 'weradio:available_tracks'
REDIS_KEY_PLAYBACK_TIME = 'weradio:playback_time'

# === LOGGING SETTINGS ===
LOG_LEVEL = os.getenv('WERADIO_LOG_LEVEL', 'INFO').upper()
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
