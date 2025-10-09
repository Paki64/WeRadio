"""
WeRadio - Upload Routes
========================

Flask routes for file upload and queue management:
- /upload - Upload new tracks
- /queue/add - Add track to playback queue

Version: 0.2 - Redis integration for API nodes
"""

import os
import time
import logging
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from config import (
    UPLOAD_FOLDER, MAX_UPLOAD_SIZE, SUPPORTED_FORMATS,
    AAC_BITRATE, SAMPLE_RATE, AUDIO_CHANNELS, CONVERSION_TIMEOUT,
    QUEUE_SIZE
)
from utils import (
    validate_file_path, validate_filename, validate_file_extension,
    clean_metadata_from_filename, convert_to_aac,
    QueueManager, redis_manager, get_metadata
)

logger = logging.getLogger('WeRadio.Routes.Upload')

upload_bp = Blueprint('upload', __name__)

# Radio instance will be set by the main app
radio = None


def init_radio(radio_instance):
    """
    Initializes the radio instance for this blueprint.
    
    Args:
        radio_instance: RadioHLS instance
    """
    global radio
    radio = radio_instance


@upload_bp.route('/queue/add', methods=['POST'])
def add_to_queue():
    """
    Adds a specific track to the playback queue.
    
    Expected JSON: {"filepath": "/path/to/track.mp3"}
    
    Returns: JSON with success status and metadata
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
    
    Returns:
        JSON with success status and track metadata
    """
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    # Validate filename
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
    
    # Save temporary file
    temp_filename = secure_filename(file.filename)
    temp_filepath = os.path.join(UPLOAD_FOLDER, f"temp_{int(time.time())}_{temp_filename}")
    
    try:
        file.save(temp_filepath)
    except Exception as e:
        logger.error(f"Failed to save upload: {e}")
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
        
        # Clean metadata if missing
        if not meta_before['title'] or meta_before['title'] in [temp_filename, 'Unknown', '']:
            meta_before['title'] = clean_metadata_from_filename(temp_filename)
        
        if not meta_before['artist'] or meta_before['artist'] in ['Unknown', '']:
            meta_before['artist'] = 'Unknown Artist'
        
        # Generate final filename
        base_name = os.path.splitext(temp_filename)[0]
        final_filename = f"{base_name}.aac"
        final_filepath = os.path.join(UPLOAD_FOLDER, final_filename)
        
        # Add timestamp if file already exists
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
        
        # Remove temporary file
        try:
            os.remove(temp_filepath)
        except:
            pass
        
        if not success:
            return jsonify({
                'error': 'Conversion failed',
                'details': error
            }), 500
        
        logger.info(f"Conversion completed: {final_filename}")
        
        # Reload available tracks and get final metadata
        if radio:
            radio.load_available_tracks()
            rel_final_path = os.path.relpath(final_filepath, UPLOAD_FOLDER)
            meta_after = radio._get_track_metadata(rel_final_path)
        else:
            redis_manager.publish_reload_tracks()
            meta_after = get_metadata(final_filepath)
        
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
