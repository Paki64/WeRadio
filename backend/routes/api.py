"""
WeRadio - API Routes
====================

Flask routes for API endpoints:
- /status - Current playback status
- /tracks - List all available tracks

Version: 0.3
"""

import os
import logging
from flask import Blueprint, jsonify, request
from config import UPLOAD_FOLDER, OBJECT_STORAGE
from utils import redis_manager, StorageManager


# === Logging Configuration ===

logger = logging.getLogger('WeRadio.Routes.API')


# === API Blueprint ===

api_bp = Blueprint('api', __name__)


# === API Routes ===

radio = None # Radio instance will be set by the main app


def init_radio(radio_instance):
    """
    Initializes the radio instance for this blueprint.
    
    Args:
        radio_instance: RadioHLS instance
    """
    global radio
    radio = radio_instance


@api_bp.route('/status')
def status():
    """
    API endpoint to get current playback status.
    """
    # STREAMER mode: use direct data
    if radio:
        queue_info = radio.get_queue_info()
        current_time = radio.get_current_playback_time()
        
        return jsonify({
            'playing': radio.playing,
            'metadata': radio.current_metadata,
            'current_time': current_time,
            'next_track': queue_info['next_track'],
            'available_tracks': len(radio.available_tracks),
            'queue_length': queue_info['length'],
            'queue': queue_info['queue']
        })
    
    # API-only mode: read from Redis
    if not redis_manager.is_connected:
        return jsonify({'error': 'Redis not available'}), 503
    
    current_track = redis_manager.get_current_track()
    queue = redis_manager.get_queue()
    current_time = redis_manager.get_playback_time()
    available_tracks = redis_manager.get_available_tracks()
    
    # Determine next track metadata
    next_track = None
    if queue and len(queue) > 0:
        next_track_path = queue[0]
        for track in available_tracks:
            if track.get('filepath') == next_track_path:
                next_track = {
                    'title': track.get('title', 'Unknown'),
                    'artist': track.get('artist', 'Unknown'),
                    'from_queue': True
                }
                break
    
    return jsonify({
        'playing': True if current_track else False,
        'metadata': current_track or {},
        'current_time': current_time,
        'next_track': next_track,
        'available_tracks': len(available_tracks),
        'queue_length': len(queue),
        'queue': queue
    })


@api_bp.route('/tracks')
def tracks():
    """
    Lists all available tracks in the library.
    """
    # If STREAMER node, use direct data
    if radio:
        track_list = []
        
        with radio.playlist_lock:
            for track in radio.available_tracks:
                meta = radio._get_track_metadata(track)
                meta['filename'] = os.path.basename(track)
                meta['in_queue'] = track in radio.queue
                track_list.append(meta)
        
        # Sort by title
        track_list.sort(key=lambda x: x['title'].lower())
        
        return jsonify({
            'tracks': track_list,
            'total': len(track_list)
        })
    
    # If API-only node, read from Redis
    if not redis_manager.is_connected:
        return jsonify({'error': 'Redis not available'}), 503
    
    available_tracks = redis_manager.get_available_tracks()
    queue = redis_manager.get_queue()
    
    for track in available_tracks:
        track['in_queue'] = track.get('filepath') in queue
    
    available_tracks.sort(key=lambda x: x.get('title', '').lower())
    
    return jsonify({
        'tracks': available_tracks,
        'total': len(available_tracks)
    })


@api_bp.route('/')
def index():
    """
    Root endpoint - service information.
    
    Returns:
        JSON with service info and available endpoints
    """
    return jsonify({
        'name': 'WeRadio Streaming Service',
        'version': '0.1',
        'endpoints': {
            'playlist': '/playlist.m3u8',
            'status': '/status',
            'tracks': '/tracks',
            'upload': '/upload',
            'queue_add': '/queue/add',
            'queue_remove': '/queue/remove',
            'track_remove': '/track/remove'
        }
    })


@api_bp.route('/track/remove', methods=['POST'])
def remove_track():
    """
    Removes a track from the system completely.
    
    Request body: JSON with 'filepath' field
    """
    data = request.get_json()
    
    if not data or 'filepath' not in data:
        return jsonify({'error': 'Missing filepath'}), 400
    
    filepath = data['filepath']
    
    if radio:
        # STREAMER mode: use radio instance
        result = radio.remove_track(filepath)
        return jsonify(result), 200 if result['success'] else 400
    
    # API-only mode: use TrackManager with Redis data
    from utils import TrackManager
    from collections import deque
    
    if not redis_manager.is_connected:
        return jsonify({'error': 'Redis not available'}), 503
    
    # Get available tracks from Redis
    available_tracks_data = redis_manager.get_available_tracks()
    available_tracks = [track['filepath'] for track in available_tracks_data]
    
    # Get queue from Redis
    queue_list = redis_manager.get_queue()
    queue = deque(queue_list)
    
    if filepath not in available_tracks:
        return jsonify({'success': False, 'message': 'Track not in library'}), 404
    
    # Use TrackManager to delete
    storage_manager = StorageManager(use_object_storage=OBJECT_STORAGE)
    
    if OBJECT_STORAGE:
        # Delete from MinIO
        success, message = TrackManager.delete_track_files(
            filepath,
            cache_getter=None,
            storage_manager=storage_manager,
            upload_folder=UPLOAD_FOLDER,
            cache_folder=None,
            available_tracks=available_tracks,
            queue=queue
        )
    else:
        # Delete from local filesystem
        full_path = os.path.join(UPLOAD_FOLDER, filepath)
        success, message = TrackManager.delete_track_files(
            full_path,
            cache_getter=None,
            storage_manager=None,
            upload_folder=None,
            cache_folder=None,
            available_tracks=available_tracks,
            queue=queue
        )
    
    if not success:
        return jsonify({'success': False, 'message': message}), 400
    
    # Update Redis
    redis_manager.remove_from_queue(filepath)
    redis_manager.publish_reload_tracks()
    
    return jsonify({
        'success': True,
        'message': f'Track "{os.path.basename(filepath)}" deleted successfully'
    }), 200


@api_bp.route('/queue/remove', methods=['POST'])
def remove_from_queue():
    """
    Removes a track from the playback queue only (doesn't delete the file).
    
    Request body: JSON with 'filepath' field
    Returns: JSON with success status and message
    """
    data = request.get_json()
    
    if not data or 'filepath' not in data:
        return jsonify({'error': 'Missing filepath'}), 400
    
    filepath = data['filepath']
    
    if radio:
        result = radio.remove_from_queue(filepath)
        return jsonify(result), 200 if result['success'] else 400
    
    # API-only mode: publish command via Redis
    if not redis_manager.is_connected:
        return jsonify({'error': 'Redis not available'}), 503
    
    success = redis_manager.remove_from_queue(filepath)
    
    if success:
        return jsonify({
            'success': True,
            'message': f'Command to remove "{os.path.basename(filepath)}" from queue sent'
        }), 200
    
    return jsonify({'success': False, 'message': 'Failed to send command'}), 500
