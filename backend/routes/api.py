"""
WeRadio - API Routes
====================

Flask routes for API endpoints:
- /status - Current playback status
- /tracks - List all available tracks

Version: 0.1
"""

import os
import logging
from flask import Blueprint, jsonify, request


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
    if not radio:
        return jsonify({'error': 'Radio not initialized'}), 500
    
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


@api_bp.route('/tracks')
def tracks():
    """
    Lists all available tracks in the library.
    
    Returns:
        JSON with list of tracks and their metadata
    """
    if not radio:
        return jsonify({'error': 'Radio not initialized'}), 500
    
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
    
    Request body:
        JSON with 'filepath' field
        
    Returns:
        JSON with success status and message
    """
    if not radio:
        return jsonify({'error': 'Radio not initialized'}), 500
    
    data = request.get_json()
    
    if not data or 'filepath' not in data:
        return jsonify({'error': 'Missing filepath'}), 400
    
    filepath = data['filepath']
    result = radio.remove_track(filepath)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@api_bp.route('/queue/remove', methods=['POST'])
def remove_from_queue():
    """
    Removes a track from the playback queue only (doesn't delete the file).
    
    Request body:
        JSON with 'filepath' field
        
    Returns:
        JSON with success status and message
    """
    if not radio:
        return jsonify({'error': 'Radio not initialized'}), 500
    
    data = request.get_json()
    
    if not data or 'filepath' not in data:
        return jsonify({'error': 'Missing filepath'}), 400
    
    filepath = data['filepath']
    result = radio.remove_from_queue(filepath)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400
