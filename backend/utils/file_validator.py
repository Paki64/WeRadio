"""
WeRadio - File Validation Utilities
====================================

Security utilities for validating file paths and filenames.

Version: 0.3
"""

import os
import logging

logger = logging.getLogger('WeRadio.FileValidator')


def validate_file_path(filepath, base_folder):
    """
    Validates a file path to ensure it's within the allowed base folder.
    Prevents path traversal attacks.
    
    Args:
        filepath (str): The file path to validate
        base_folder (str): The base folder that the file must be within
    """
    try:
        # Unallowed characters check
        if '\\' in filepath or '\0' in filepath or '..' in filepath:
            logger.warning(f"Invalid characters in path: {filepath}")
            return False, "Invalid file path", None
        
        # Normalize paths
        abs_base_folder = os.path.abspath(base_folder)
        
        if not os.path.isabs(filepath):
            abs_filepath = os.path.abspath(os.path.join(base_folder, filepath))
        else:
            abs_filepath = os.path.abspath(filepath)
        
        if not abs_filepath.startswith(abs_base_folder):
            logger.warning(f"Path traversal attempt detected: {filepath}")
            return False, "Invalid file path", None
        
        # Check existence
        if not os.path.exists(abs_filepath):
            return False, "File not found", None
        
        rel_path = os.path.relpath(abs_filepath, abs_base_folder)
        return True, "", rel_path
        
    except Exception as e:
        logger.error(f"Error validating path {filepath}: {e}")
        return False, str(e), None


def validate_filename(filename):
    """
    Validates a filename to prevent directory traversal.
    
    Args:
        filename (str): The filename to validate
        
    Returns:
        bool: True if filename is safe, False otherwise
        
    Example:
        if not validate_filename('../../etc/passwd'):
            print("Invalid filename!")
    """
    if not filename:
        return False
    
    # Check for path traversal attempts
    dangerous_chars = ['..', '/', '\\']
    for char in dangerous_chars:
        if char in filename:
            logger.warning(f"Dangerous filename detected: {filename}")
            return False
    
    return True


def validate_file_extension(filename, allowed_extensions):
    """
    Validates that a file has an allowed extension.
    
    Args:
        filename (str): The filename to check
        allowed_extensions (set): Set of allowed extensions (e.g., {'.mp3', '.flac'})
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions
