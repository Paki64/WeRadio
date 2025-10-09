"""
WeRadio - Silence Generator Utility
====================================

Generates a silent AAC audio file as a fallback for empty libraries.

Version: 0.3
"""

import os
import subprocess
import logging
import tempfile

logger = logging.getLogger('WeRadio.SilenceGenerator')

# Nome del file silenzioso
SILENCE_FILENAME = 'silence_fallback.aac'


class SilenceGenerator:
    """
    Generates and manages a silent fallback audio file.
    """
    
    @staticmethod
    def generate_silence_file(output_path, duration=5, sample_rate='44100', bitrate='128k'):
        """
        Generates a silent AAC audio file using FFmpeg.
        
        Args:
            output_path (str): Path where to save the silent file
            duration (int): Duration in seconds (default: 5)
            sample_rate (str): Sample rate (default: '44100')
            bitrate (str): Audio bitrate (default: '128k')
            
        Returns:
            bool: True if generation successful, False otherwise
        """
        try:
            # Comando FFmpeg per generare audio silenzioso
            cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', f'anullsrc=channel_layout=stereo:sample_rate={sample_rate}',
                '-t', str(duration),
                '-c:a', 'aac',
                '-b:a', bitrate,
                '-y',  # Overwrite if exists
                output_path
            ]
            
            logger.info(f"Generating {duration}s silent AAC file: {output_path}")
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"✓ Silent file generated successfully ({file_size} bytes)")
                return True
            else:
                logger.error(f"FFmpeg failed to generate silence file: {result.stderr.decode()}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout while generating silence file")
            return False
        except Exception as e:
            logger.error(f"Error generating silence file: {e}")
            return False
    
    @staticmethod
    def is_silence_file(filepath):
        """
        Checks if a file is the silence placeholder.
        
        Args:
            filepath (str): Path to check
            
        Returns:
            bool: True if it's the silence placeholder
        """
        filename = os.path.basename(filepath)
        return filename == SILENCE_FILENAME
    
    @staticmethod
    def ensure_silence_exists(library_folder, storage_manager=None):
        """
        Ensures the silence file exists in the library.
        Creates it if missing.
        
        Args:
            library_folder (str): Path to library folder
            storage_manager: Optional StorageManager for object storage
            
        Returns:
            tuple: (success: bool, filepath: str)
        """
        if storage_manager and storage_manager.use_object_storage:
            # Object storage mode
            if storage_manager.file_exists(SILENCE_FILENAME, library_folder, 'library'):
                logger.debug("Silence file already exists in object storage")
                return True, SILENCE_FILENAME
            
            # Generate temporary file and upload
            temp_file = tempfile.NamedTemporaryFile(suffix='.aac', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            try:
                if SilenceGenerator.generate_silence_file(temp_path):
                    with open(temp_path, 'rb') as f:
                        file_data = f.read()
                    
                    success = storage_manager.write_file(
                        SILENCE_FILENAME,   # filepath
                        file_data,          # data
                        library_folder,     # base_path
                        'library'           # folder_type
                    )
                    
                    if success:
                        logger.info(f"✓ Silence file uploaded to object storage")
                        return True, SILENCE_FILENAME
                    else:
                        logger.error("Failed to upload silence file to object storage")
                        return False, None
                else:
                    return False, None
            finally:
                # Cleanup temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            # Local filesystem mode
            silence_path = os.path.join(library_folder, SILENCE_FILENAME)
            
            if os.path.exists(silence_path):
                logger.debug("Silence file already exists")
                return True, SILENCE_FILENAME
            
            if SilenceGenerator.generate_silence_file(silence_path):
                return True, SILENCE_FILENAME
            else:
                return False, None
    
    @staticmethod
    def remove_silence_file(library_folder, storage_manager=None):
        """
        Removes the silence placeholder file.
        
        Args:
            library_folder (str): Path to library folder
            storage_manager: Optional StorageManager for object storage
            
        Returns:
            bool: True if removed or didn't exist, False on error
        """
        try:
            if storage_manager and storage_manager.use_object_storage:
                # Object storage mode
                if storage_manager.file_exists(SILENCE_FILENAME, library_folder, 'library'):
                    success = storage_manager.delete_file(SILENCE_FILENAME, library_folder, 'library')
                    if success:
                        logger.info("✓ Silence file removed from object storage")
                    else:
                        logger.warning("Failed to remove silence file from object storage")
                    return success
                return True 
            else:
                # Local filesystem mode
                silence_path = os.path.join(library_folder, SILENCE_FILENAME)
                
                if os.path.exists(silence_path):
                    os.remove(silence_path)
                    logger.info(f"✓ Silence file removed: {silence_path}")
                
                return True
        except Exception as e:
            logger.error(f"Error removing silence file: {e}")
            return False