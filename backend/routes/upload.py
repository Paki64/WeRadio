"""
WeRadio - Upload Routes
========================

Flask routes for file upload and queue management:
- /upload - Upload new tracks
- /queue/add - Add track to playback queue

Version: 0.3
"""

import os
import io
import time
import logging
import tempfile
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from config import (
    UPLOAD_FOLDER, MAX_UPLOAD_SIZE, SUPPORTED_FORMATS,
    AAC_BITRATE, SAMPLE_RATE, AUDIO_CHANNELS, CONVERSION_TIMEOUT,
    QUEUE_SIZE, OBJECT_STORAGE
)
from utils import (
    validate_file_path, validate_filename, validate_file_extension,
    clean_metadata_from_filename, convert_to_aac,
    QueueManager, redis_manager, get_metadata, StorageManager
)

logger = logging.getLogger('WeRadio.Routes.Upload')

upload_bp = Blueprint('upload', __name__)

radio = None
storage_manager = None

def init_radio(radio_instance):
    """
    Initializes the radio instance for this blueprint.
    
    Args:
        radio_instance: RadioHLS instance or None for API-only mode
    """
    global radio, storage_manager
    radio = radio_instance
    
    # Get storage manager from radio or create new one
    if radio and hasattr(radio, 'storage_manager'):
        storage_manager = radio.storage_manager
    else:
        storage_manager = StorageManager(use_object_storage=OBJECT_STORAGE)


@upload_bp.route('/queue/add', methods=['POST'])
def add_to_queue():
    """
    Adds a specific track to the playback queue.
    
    Expected JSON: {"filepath": "/path/to/track.mp3"}
    """
    data = request.get_json()
    
    if not data or 'filepath' not in data:
        return jsonify({'error': 'Missing filepath parameter'}), 400
    
    filepath = data['filepath']
    
    if radio:
        # STREAMER mode: add directly to queue
        is_valid, error_msg, rel_filepath = validate_file_path(filepath, radio.upload_folder)
        if not is_valid:
            logger.warning(f"Invalid path: {filepath} - {error_msg}")
            status_code = 403 if error_msg == "Invalid file path" else 404
            return jsonify({'error': error_msg}), status_code
        
        with radio.playlist_lock:
            success, message = QueueManager.add_track_to_queue(
                radio.queue, rel_filepath, radio.available_tracks, QUEUE_SIZE
            )
            
            if not success:
                status_code = 507 if 'full' in message else 400
                return jsonify({'error': message}), status_code
        
        meta = radio._get_track_metadata(rel_filepath)
        logger.info(f"Added to queue: {meta['artist']} - {meta['title']}")
        
        return jsonify({
            'success': True,
            'message': f'Added "{meta["artist"]} - {meta["title"]}" as next track',
            'metadata': meta,
            'queue_length': len(radio.queue)
        })
    
    # API-only mode: publish command via Redis
    logger.info(f"API node: Publishing add_to_queue command for {filepath}")
    redis_manager.add_to_queue(filepath)
    
    # Get metadata from Redis
    available_tracks = redis_manager.get_available_tracks()
    meta = next((t for t in available_tracks if t.get('filepath') == filepath), 
                {'title': filepath, 'artist': 'Unknown', 'duration': 0})
    
    return jsonify({
        'success': True,
        'message': f'Command sent to add "{meta.get("artist", "Unknown")} - {meta.get("title", filepath)}" to queue',
        'metadata': meta
    })


@upload_bp.route('/upload', methods=['POST'])
def upload():
    """
    Uploads a new track to the library.
    Converts to AAC format and adds metadata.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    if not validate_filename(file.filename):
        return jsonify({'error': 'Invalid filename'}), 400
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_UPLOAD_SIZE:
        return jsonify({
            'error': f'File too large. Max size: {MAX_UPLOAD_SIZE / (1024*1024):.0f}MB'
        }), 413
    
    # Validate file extension
    if not validate_file_extension(file.filename, SUPPORTED_FORMATS):
        return jsonify({
            'error': f'Format not supported. Allowed: {", ".join(SUPPORTED_FORMATS)}'
        }), 400
    
    temp_filename = secure_filename(file.filename)
    temp_file = tempfile.NamedTemporaryFile(suffix=os.path.splitext(temp_filename)[1], delete=False)
    temp_filepath = temp_file.name
    temp_file.close()
    
    try:
        file.save(temp_filepath)
    except Exception as e:
        logger.error(f"Failed to save upload: {e}")
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
    
    logger.info(f"Upload received: {temp_filename}")
    
    try:
        # Extract metadata from uploaded file
        try:
            meta_before = get_metadata(temp_filepath)
            logger.debug(f"Original metadata: {meta_before['artist']} - {meta_before['title']}")
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            meta_before = {'title': temp_filename, 'artist': 'Unknown', 'duration': 0}
        
        if not meta_before['title'] or meta_before['title'] in [temp_filename, 'Unknown', '']:
            meta_before['title'] = clean_metadata_from_filename(temp_filename)
        
        if not meta_before['artist'] or meta_before['artist'] in ['Unknown', '']:
            meta_before['artist'] = 'Unknown Artist'
        
        base_name = os.path.splitext(temp_filename)[0]
        final_filename = f"{base_name}.aac"
        
        # Check if file exists and add timestamp if needed
        if storage_manager and storage_manager.use_object_storage:
            # Check in MinIO
            if storage_manager.file_exists(final_filename, UPLOAD_FOLDER, 'library'):
                final_filename = f"{base_name}_{int(time.time())}.aac"
            final_filepath = tempfile.NamedTemporaryFile(suffix='.aac', delete=False).name
        else:
            # Check in local filesystem
            final_filepath = os.path.join(UPLOAD_FOLDER, final_filename)
            if os.path.exists(final_filepath):
                final_filename = f"{base_name}_{int(time.time())}.aac"
                final_filepath = os.path.join(UPLOAD_FOLDER, final_filename)
        
        logger.info(f"Converting: {temp_filename} → {final_filename}")
        
        # Convert to AAC
        success, error = convert_to_aac(
            temp_filepath,
            final_filepath,
            meta_before,
            AAC_BITRATE,
            SAMPLE_RATE,
            AUDIO_CHANNELS,
            CONVERSION_TIMEOUT
        )
        
        # Remove temp file
        try:
            os.remove(temp_filepath)
        except:
            pass
        
        if not success:
            # Clean up conversion output if exists
            if os.path.exists(final_filepath):
                os.remove(final_filepath)
            return jsonify({
                'error': 'Conversion failed',
                'details': error
            }), 500
        
        logger.info(f"Conversion completed: {final_filename}")
        
        # Upload to storage
        if storage_manager and storage_manager.use_object_storage:
            # Upload to MinIO
            try:
                with open(final_filepath, 'rb') as f:
                    data = f.read()
                
                storage_manager.write_file(
                    final_filename,
                    data,
                    UPLOAD_FOLDER,
                    'library',
                    'audio/aac'
                )
                
                # Remove local temp file
                os.remove(final_filepath)
                logger.info(f"Uploaded to MinIO: {final_filename}")
                
            except Exception as e:
                logger.error(f"Failed to upload to MinIO: {e}")
                if os.path.exists(final_filepath):
                    os.remove(final_filepath)
                return jsonify({'error': f'Failed to upload to storage: {str(e)}'}), 500
        
        # Reload available tracks and get final metadata
        if radio:
            radio.load_available_tracks()
            radio.track_library.remove_silence_if_exists()
            
            rel_final_path = final_filename
            meta_after = radio._get_track_metadata(rel_final_path)
            
            # If the queue is empty and nothing is playing, add and start playback immediately
            if radio.playback_queue.is_empty() and not radio.playing:
                logger.info("Queue empty and nothing playing - starting playback with uploaded track")
                with radio.playlist_lock:
                    radio.playback_queue.queue.append(rel_final_path)

        else:
            redis_manager.publish_reload_tracks()
            if storage_manager and storage_manager.use_object_storage:
                meta_after = get_metadata(final_filepath) if os.path.exists(final_filepath) else meta_before
            else:
                meta_after = get_metadata(os.path.join(UPLOAD_FOLDER, final_filename))
        
        logger.info(f"Final metadata: {meta_after['artist']} - {meta_after['title']}")
        
        return jsonify({
            'success': True,
            'message': 'Track uploaded and converted successfully',
            'filename': final_filename,
            'metadata': meta_after
        })
        
    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except:
                pass
        
        logger.error(f"Upload error: {e}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500
