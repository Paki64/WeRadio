"""
WeRadio - Cache Management Utilities
====================================

Utilities for managing caches.

Version: 0.4
"""

import os
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger('WeRadio.CacheManager')


class CacheManager:
    """
    Manages cache cleanup for both file-based and in-memory caches.
    """
    
    @staticmethod
    def clean_file_cache(cache_folder, max_size, file_pattern='*.aac'):
        """
        Cleans a file-based cache by removing oldest files.
        
        Args:
            cache_folder (str): Path to the cache folder
            max_size (int): Maximum number of files to keep
            file_pattern (str): Glob pattern for cache files
        """
        try:
            cache_files = list(Path(cache_folder).glob(file_pattern))
            
            if len(cache_files) <= max_size:
                return 0

            cache_files.sort(key=lambda f: f.stat().st_atime)
            
            to_remove = len(cache_files) - max_size
            removed_count = 0
            
            for f in cache_files[:to_remove]:
                try:
                    f.unlink()
                    removed_count += 1
                    logger.debug(f"Removed cached file: {f.name}")
                except Exception as e:
                    logger.error(f"Failed to remove {f.name}: {e}")
            
            if removed_count > 0:
                logger.info(f"File cache cleaned: removed {removed_count} files")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning file cache: {e}")
            return 0
    
    @staticmethod
    def clean_metadata_cache(cache_dict, max_size, cache_lock=None):
        """
        Cleans an in-memory metadata cache by removing oldest entries.
        
        Args:
            cache_dict (dict): The cache dictionary to clean
            max_size (int): Maximum number of entries to keep
            cache_lock (threading.Lock, optional): Lock for thread-safe access
        """
        try:
            if cache_lock:
                with cache_lock:
                    return CacheManager._clean_dict_cache(cache_dict, max_size)
            else:
                return CacheManager._clean_dict_cache(cache_dict, max_size)
                
        except Exception as e:
            logger.error(f"Error cleaning metadata cache: {e}")
            return 0
    
    @staticmethod
    def _clean_dict_cache(cache_dict, max_size):
        """
        Internal method to clean a dictionary cache.
        
        Args:
            cache_dict (dict): The cache dictionary
            max_size (int): Maximum number of entries
        """
        if len(cache_dict) <= max_size:
            return 0
        
        to_remove = len(cache_dict) - max_size
        keys_to_remove = list(cache_dict.keys())[:to_remove]
        
        for key in keys_to_remove:
            del cache_dict[key]
        
        logger.info(f"Metadata cache cleaned: removed {to_remove} entries")
        return to_remove
    
    # === Audio Cache Specific Methods ===
    
    @staticmethod
    def get_cached_audio(filepath, cache_folder, upload_folder, 
                         metadata_getter, cache_max_size=50):
        """
        Gets a cached or creates a new AAC version of an audio file.
        
        Args:
            filepath (str): Original file path
            cache_folder (str): Cache folder path
            upload_folder (str): Upload folder path
            metadata_getter (callable): Function to get metadata
            cache_max_size (int): Maximum number of cached files
        """
        from .audio_processor import convert_to_aac
        
        if filepath.endswith('.aac') and upload_folder in filepath:
            logger.debug(f"File already clean: {os.path.basename(filepath)}")
            return filepath
        
        # Generate cache filename using hash
        file_hash = hashlib.md5(filepath.encode()).hexdigest()
        cached_file = os.path.join(cache_folder, f"{file_hash}.aac")
        
        if os.path.exists(cached_file):
            # Update access timestamp
            Path(cached_file).touch()
            logger.debug(f"Using cached file: {os.path.basename(cached_file)}")
            return cached_file
        
        logger.info(f"Converting audio file to cache: {os.path.basename(filepath)}")
        
        CacheManager.clean_file_cache(cache_folder, cache_max_size)
        
        meta = metadata_getter(filepath)
        success, error = convert_to_aac(filepath, cached_file, meta)
        
        if success:
            logger.info(f"Cached successfully: {os.path.basename(cached_file)}")
            return cached_file
        else:
            logger.warning(f"Conversion failed, using original: {error}")
            return filepath
    
    @staticmethod
    def get_cache_path_for_file(filepath, cache_folder):
        """
        Gets the cache file path for a given original file.
        
        Args:
            filepath (str): Original file path
            cache_folder (str): Cache folder path
        """
        file_hash = hashlib.md5(filepath.encode()).hexdigest()
        return os.path.join(cache_folder, f"{file_hash}.aac")

