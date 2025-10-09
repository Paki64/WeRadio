"""
WeRadio - Audio Processing Utilities
=====================================

Utilities for audio file processing, metadata extraction, and conversion.

Version: 0.3
"""

import os
import re
import logging
import subprocess
import mutagen

from .cache_manager import CacheManager

logger = logging.getLogger('WeRadio.AudioProcessor')


def get_metadata(filepath, metadata_cache=None, metadata_lock=None):
    """
    Extracts metadata from an audio file.
    Thread-safe when cache and lock are provided.
    
    Args:
        filepath (str): Path to the audio file
        metadata_cache (dict): Cache dictionary for metadata
        metadata_lock (threading.Lock): Lock for thread-safe cache access
    """
    # Cache check
    if metadata_cache is not None and metadata_lock is not None:
        with metadata_lock:
            if filepath in metadata_cache:
                return metadata_cache[filepath].copy()
    
    filename = os.path.basename(filepath)
    
    try:
        audio = mutagen.File(filepath)
        if audio is None:
            metadata = {
                'title': filename,
                'artist': 'Unknown',
                'duration': 0
            }
            if metadata_cache is not None and metadata_lock is not None:
                with metadata_lock:
                    metadata_cache[filepath] = metadata
            return metadata
        
        title = None
        artist = None
        
        # Common tag formats
        title_tags = ['title', 'TIT2', '\xa9nam']
        artist_tags = ['artist', 'TPE1', '\xa9ART']
        
        for tag_key in title_tags:
            if tag_key in audio:
                value = audio[tag_key]
                title = str(value[0]) if isinstance(value, list) else str(value)
                break
        
        for tag_key in artist_tags:
            if tag_key in audio:
                value = audio[tag_key]
                artist = str(value[0]) if isinstance(value, list) else str(value)
                break
        
        # Fallback to filename if no title found
        if not title or title.strip() == '':
            title = filename
        if not artist or artist.strip() == '':
            artist = 'Unknown'
        
        duration = audio.info.length if hasattr(audio.info, 'length') else 0
        
        metadata = {
            'title': title,
            'artist': artist,
            'duration': float(duration)
        }
        
        # Cache update
        if metadata_cache is not None and metadata_lock is not None:
            with metadata_lock:
                metadata_cache[filepath] = metadata
        
        return metadata
        
    except Exception as e:
        logger.error(f"Metadata error for {filename}: {e}")
        metadata = {
            'title': filename,
            'artist': 'Unknown',
            'duration': 0
        }
        if metadata_cache is not None and metadata_lock is not None:
            with metadata_lock:
                metadata_cache[filepath] = metadata
        return metadata


def clean_metadata_from_filename(filename):
    """
    Extracts a fallback title from a filename, in case of missing tag.
    
    Args:
        filename (str): The filename to clean
    """
    clean_title = os.path.splitext(filename)[0]
    clean_title = clean_title.replace('_', ' ').replace('temp_', '').strip()
    clean_title = re.sub(r'^\d+[\s_-]+', '', clean_title)  # Remove leading numbers
    return clean_title


def convert_to_aac(input_path, output_path, metadata, bitrate='128k', 
                   sample_rate='44100', channels='2', timeout=120):
    """
    Converts an audio file to AAC format with metadata.
    
    Args:
        input_path (str): Path to the input audio file
        output_path (str): Path to the output AAC file
        metadata (dict): Dictionary with 'title' and 'artist' keys
        bitrate (str): AAC bitrate (default: '128k')
        sample_rate (str): Sample rate in Hz (default: '44100')
        channels (str): Number of audio channels (default: '2')
        timeout (int): Conversion timeout in seconds (default: 120)
    """
    try:
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vn',  # No video
            '-c:a', 'aac',
            '-b:a', bitrate,
            '-ar', sample_rate,
            '-ac', channels,
            '-f', 'ipod',
        ]
        
        # Add title and artist metadata to converted file if available
        if metadata.get('title') and metadata['title'] not in ['Unknown', os.path.basename(input_path)]:
            cmd.extend(['-metadata', f"title={metadata['title']}"])
        if metadata.get('artist') and metadata['artist'] != 'Unknown':
            cmd.extend(['-metadata', f"artist={metadata['artist']}"])
        
        cmd.extend(['-y', output_path])
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        
        if result.returncode != 0:
            error = result.stderr.decode('utf-8', errors='ignore')[-500:]
            logger.error(f"FFmpeg conversion failed: {error}")
            return False, f"Conversion failed: {error}"
        
        if not os.path.exists(output_path):
            return False, "Output file not created"
        
        logger.info(f"Successfully converted: {os.path.basename(output_path)}")
        return True, ""
        
    except subprocess.TimeoutExpired:
        logger.error(f"Conversion timeout for {input_path}")
        return False, "Conversion timeout (file too large?)"
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return False, str(e)
