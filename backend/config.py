"""
WeRadio - Core Configuration
=======================================

Version: 0.4
"""

import os

# === FEATURES ===
STREAMER_MODE = os.getenv('STREAMER', 'true').lower() in ('true', '1', 'yes')
OBJECT_STORAGE = os.getenv('OBJECT_STORAGE', 'false').lower() in ('true', '1', 'yes')

# === OBJECT STORAGE ===
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'admin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'password123')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() in ('true', '1', 'yes')
MINIO_BUCKET_LIBRARY = os.getenv('MINIO_BUCKET_LIBRARY', 'weradio-library')

# === LOCAL FOLDERS ===
UPLOAD_FOLDER = os.path.abspath('data/library')
HLS_FOLDER = os.path.abspath('data/hls_output')
CACHE_FOLDER = os.path.abspath('data/audio_cache')

# === SUPPORTED AUDIO FORMATS ===
SUPPORTED_FORMATS = {'.mp3', '.flac', '.ogg', '.wav', '.aac', '.m4a'}

# === HLS STREAMING SETTINGS ===
SEGMENT_DURATION = 2
QUEUE_SIZE = int(os.getenv('WERADIO_QUEUE_SIZE', '100'))
HLS_LIST_SIZE = 20
HLS_CLIENT_BUFFER_DELAY = 10

# === FFMPEG SETTINGS ===
AAC_BITRATE = '128k'
SAMPLE_RATE = '44100'
AUDIO_CHANNELS = '2'
CONVERSION_TIMEOUT = 120
MAX_UPLOAD_SIZE = 300 * 1024 * 1024
CACHE_MAX_SIZE = 50
METADATA_CACHE_MAX_SIZE = 200

# === REDIS SETTINGS ===
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'password123')
REDIS_DECODE_RESPONSES = True
REDIS_KEY_CURRENT_TRACK = 'weradio:current_track'
REDIS_KEY_QUEUE = 'weradio:queue'
REDIS_KEY_AVAILABLE_TRACKS = 'weradio:available_tracks'
REDIS_KEY_PLAYBACK_TIME = 'weradio:playback_time'

# === SECURITY SETTINGS ===
BCRYPT_ROUNDS = 12
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# === POSTGRES SETTINGS ===
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', '5432'))
POSTGRES_DB = os.getenv('POSTGRES_DB', 'weradio')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'weradio_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'weradio_pass')

# === DEFAULT ADMIN USER ===
ROOT_DB_USER = os.getenv('ROOT_DB_USER', 'admin')
ROOT_DB_EMAIL = os.getenv('ROOT_DB_EMAIL', 'admin@weradio.local')
ROOT_DB_PASSWORD = os.getenv('ROOT_DB_PASSWORD', 'admin123')

# === JWT SETTINGS ===
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# === FLASK SETTINGS ===
FLASK_HOST = os.getenv('WERADIO_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('WERADIO_PORT', '5000'))
FLASK_DEBUG = os.getenv('WERADIO_DEBUG', 'False').lower() in ('true', '1', 'yes')
FLASK_THREADED = True

# === LOGGING SETTINGS ===
LOG_LEVEL = os.getenv('WERADIO_LOG_LEVEL', 'INFO').upper()
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
