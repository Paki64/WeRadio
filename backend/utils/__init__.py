"""
WeRadio - Package Initializer
====================================

Version: 0.1
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
]
