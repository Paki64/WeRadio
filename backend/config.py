import os

OBJECT_STORAGE = os.getenv('OBJECT_STORAGE', 'false').lower() in ('true', '1', 'yes')

MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'admin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'password123')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() in ('true', '1', 'yes')
MINIO_BUCKET_LIBRARY = os.getenv('MINIO_BUCKET_LIBRARY', 'weradio-library')

UPLOAD_FOLDER = os.path.abspath('data/library')
HLS_FOLDER = os.path.abspath('data/hls_output')
CACHE_FOLDER = os.path.abspath('data/audio_cache')

SUPPORTED_FORMATS = {'.mp3', '.flac', '.ogg', '.wav', '.aac', '.m4a'}

SEGMENT_DURATION = 2
QUEUE_SIZE = int(os.getenv('WERADIO_QUEUE_SIZE', '100'))
HLS_LIST_SIZE = 20
HLS_CLIENT_BUFFER_DELAY = 10

AAC_BITRATE = '128k'
SAMPLE_RATE = '44100'
AUDIO_CHANNELS = '2'

CONVERSION_TIMEOUT = 120
MAX_UPLOAD_SIZE = 300 * 1024 * 1024
CACHE_MAX_SIZE = 50
METADATA_CACHE_MAX_SIZE = 200

FLASK_HOST = os.getenv('WERADIO_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('WERADIO_PORT', '5000'))
FLASK_DEBUG = os.getenv('WERADIO_DEBUG', 'False').lower() in ('true', '1', 'yes')
FLASK_THREADED = True

STREAMER_MODE = os.getenv('STREAMER', 'true').lower() in ('true', '1', 'yes')

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'password123')
REDIS_DECODE_RESPONSES = True
REDIS_KEY_CURRENT_TRACK = 'weradio:current_track'
REDIS_KEY_QUEUE = 'weradio:queue'
REDIS_KEY_AVAILABLE_TRACKS = 'weradio:available_tracks'
REDIS_KEY_PLAYBACK_TIME = 'weradio:playback_time'

LOG_LEVEL = os.getenv('WERADIO_LOG_LEVEL', 'INFO').upper()
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
