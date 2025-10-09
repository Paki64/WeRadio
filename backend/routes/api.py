"""
WeRadio - API Routes
====================

Flask routes for API endpoints:
- /status - Current playback status
- /tracks - List all available tracks

Version: 0.2
"""

import os
import logging
from flask import Blueprint, jsonify, request
from config import UPLOAD_FOLDER
from utils import redis_manager


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
    
    Returns:
        JSON with current track, queue info, and playback time
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
    
    Returns:
        JSON with list of tracks and their metadata
    """
    # If STREAMER node, use direct data
    if radio:
        track_list = []
        
        with radio.playlist_lock:
            for track in radio.available_tracks:
                meta = radio._get_track_metadata(track)
                # filepath is set by _get_track_metadata
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
    Returns: JSON with success status and message
    """
    data = request.get_json()
    
    if not data or 'filepath' not in data:
        return jsonify({'error': 'Missing filepath'}), 400
    
    filepath = data['filepath']
    
    if radio:
        result = radio.remove_track(filepath)
        return jsonify(result), 200 if result['success'] else 400
    
    # API-only mode: delete file and publish reload command
    full_path = os.path.join(UPLOAD_FOLDER, filepath)
    
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': 'Track not found'}), 404
    
    try:
        os.remove(full_path)
        redis_manager.publish_reload_tracks()
        return jsonify({
            'success': True,
            'message': f'Track "{filepath}" deleted successfully'
        }), 200
    except Exception as e:
        logger.error(f"Failed to delete track: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to delete track: {str(e)}'
        }), 500


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
