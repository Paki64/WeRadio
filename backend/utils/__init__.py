"""
WeRadio - Package Initializer
====================================

Version: 0.3
"""

from .audio_processor import (
    get_metadata,
    clean_metadata_from_filename,
    convert_to_aac
)

from .file_validator import (
    validate_file_path,
    validate_filename,
    validate_file_extension
)

from .cache_manager import CacheManager
from .queue_manager import QueueManager
from .track_manager import TrackManager
from .redis_manager import redis_manager
from .storage_manager import StorageManager
from .silence_generator import SilenceGenerator, SILENCE_FILENAME

__all__ = [
    # Audio processing
    'get_metadata',
    'clean_metadata_from_filename',
    'convert_to_aac',
    
    # File validation
    'validate_file_path',
    'validate_filename',
    'validate_file_extension',
    
    # Cache management
    'CacheManager',
    
    # Queue management
    'QueueManager',
    
    # Track management
    'TrackManager',
    
    # Redis management
    'redis_manager',
    
    # Storage management
    'StorageManager',
    
    # Silence generation
    'SilenceGenerator',
    'SILENCE_FILENAME',
]
