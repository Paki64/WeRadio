"""
WeRadio - Cache Management Utilities
====================================

Utilities for managing caches.

Version: 0.2
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
            
        Returns:
            int: Number of files removed
        """
        try:
            cache_files = list(Path(cache_folder).glob(file_pattern))
            
            if len(cache_files) <= max_size:
                return 0
            
            # Sort by access time (oldest first)
            cache_files.sort(key=lambda f: f.stat().st_atime)
            
            # Calculate how many to remove
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
            
        Returns:
            int: Number of entries removed
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
            
        Returns:
            int: Number of entries removed
        """
        if len(cache_dict) <= max_size:
            return 0
        
        # Remove oldest 20% (using insertion order)
        to_remove = len(cache_dict) - max_size
        keys_to_remove = list(cache_dict.keys())[:to_remove]
        
        for key in keys_to_remove:
            del cache_dict[key]
        
        logger.info(f"Metadata cache cleaned: removed {to_remove} entries")
        return to_remove
    
    @staticmethod
    def get_cache_stats(cache_folder=None, cache_dict=None, file_pattern='*.aac'):
        """
        Gets statistics about cache usage.
        
        Args:
            cache_folder (str, optional): Path to file cache folder
            cache_dict (dict, optional): In-memory cache dictionary
            file_pattern (str): Glob pattern for cache files
            
        Returns:
            dict: Cache statistics
        """
        stats = {}
        
        if cache_folder:
            try:
                cache_files = list(Path(cache_folder).glob(file_pattern))
                total_size = sum(f.stat().st_size for f in cache_files)
                stats['file_cache'] = {
                    'count': len(cache_files),
                    'total_size_mb': round(total_size / (1024 * 1024), 2)
                }
            except Exception as e:
                logger.error(f"Error getting file cache stats: {e}")
                stats['file_cache'] = {'error': str(e)}
        
        if cache_dict is not None:
            stats['metadata_cache'] = {
                'count': len(cache_dict)
            }
        
        return stats
    
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
            
        Returns:
            str: Path to the cached/cleaned file
        """
        from .audio_processor import convert_to_aac
        
        # .aac files in uploads are already clean
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
        
        # Clean cache if needed
        CacheManager.clean_file_cache(cache_folder, cache_max_size)
        
        # Get metadata and convert
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
            
        Returns:
            str: Path to the cached file (may not exist yet)
        """
        file_hash = hashlib.md5(filepath.encode()).hexdigest()
        return os.path.join(cache_folder, f"{file_hash}.aac")
    
    @staticmethod
    def is_file_cached(filepath, cache_folder):
        """
        Checks if a file has a cached version.
        
        Args:
            filepath (str): Original file path
            cache_folder (str): Cache folder path
            
        Returns:
            bool: True if cached version exists
        """
        cached_path = CacheManager.get_cache_path_for_file(filepath, cache_folder)
        return os.path.exists(cached_path)
    
    @staticmethod
    def remove_from_cache(filepath, cache_folder):
        """
        Removes a file's cached version.
        
        Args:
            filepath (str): Original file path
            cache_folder (str): Cache folder path
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            cached_path = CacheManager.get_cache_path_for_file(filepath, cache_folder)
            
            if not os.path.exists(cached_path):
                return True, "No cached version found"
            
            os.remove(cached_path)
            logger.info(f"Removed from cache: {os.path.basename(cached_path)}")
            return True, "Cached file removed"
            
        except Exception as e:
            logger.error(f"Error removing from cache: {e}")
            return False, f"Error: {str(e)}"
    
    @staticmethod
    def clear_all_cache(cache_folder):
        """
        Clears all files from the audio cache.
        
        Args:
            cache_folder (str): Path to cache folder
            
        Returns:
            tuple: (success: bool, files_removed: int)
        """
        try:
            cache_files = list(Path(cache_folder).glob('*.aac'))
            removed = 0
            
            for cache_file in cache_files:
                try:
                    cache_file.unlink()
                    removed += 1
                except Exception as e:
                    logger.error(f"Failed to remove {cache_file.name}: {e}")
            
            logger.info(f"Cache cleared: {removed} files removed")
            return True, removed
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False, 0
