"""
WeRadio - Streaming Routes
===========================

Flask routes for HLS streaming endpoints:
- /playlist.m3u8 - HLS playlist
- /hls/<filename> - HLS segments

Version: 0.1
"""

import os
import logging
from flask import Blueprint, Response, send_file, jsonify

from config import HLS_FOLDER
from utils import validate_filename

logger = logging.getLogger('WeRadio.Routes.Streaming')

streaming_bp = Blueprint('streaming', __name__)


@streaming_bp.route('/playlist.m3u8')
def hls_playlist():
    """
    Serves the HLS playlist file.
    
    Returns:
        Response: M3U8 playlist with modified segment paths
    """
    playlist_path = os.path.join(HLS_FOLDER, 'playlist.m3u8')
    
    if not os.path.exists(playlist_path):
        return jsonify({
            'error': 'Playlist not ready yet',
            'message': 'Stream is starting, please wait a moment'
        }), 503
    
    try:
        file_size = os.path.getsize(playlist_path)
        if file_size == 0:
            return jsonify({
                'error': 'Playlist empty',
                'message': 'Stream is initializing'
            }), 503
        
        # Read and modify playlist content
        with open(playlist_path, 'r') as f:
            content = f.read()
        
        # Replace segment paths with full URLs
        lines = content.split('\n')
        modified_lines = []
        for line in lines:
            if line.endswith('.ts'):
                filename = os.path.basename(line)
                modified_lines.append(f'/hls/{filename}')
            else:
                modified_lines.append(line)
        
        modified_content = '\n'.join(modified_lines)
        
        return Response(
            modified_content,
            mimetype='application/vnd.apple.mpegurl',
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        
    except Exception as e:
        logger.error(f"Error reading playlist: {e}")
        return jsonify({'error': 'Error reading playlist'}), 500


@streaming_bp.route('/hls/<path:filename>')
def hls_segment(filename):
    """
    Serves HLS segment files.
    
    Args:
        filename (str): Name of the segment file
        
    Returns:
        Response: The segment file or error
    """
    # Validate filename to prevent path traversal
    if not validate_filename(filename):
        logger.warning(f"Invalid filename requested: {filename}")
        return jsonify({'error': 'Invalid filename'}), 400
    
    segment_path = os.path.join(HLS_FOLDER, filename)
    
    if not os.path.exists(segment_path):
        logger.debug(f"Segment not found: {filename}")
        return jsonify({'error': 'Segment not found'}), 404
    
    try:
        return send_file(
            segment_path,
            mimetype='video/MP2T',
            as_attachment=False,
            conditional=True
        )
    except Exception as e:
        logger.error(f"Error serving segment {filename}: {e}")
        return jsonify({'error': 'Error serving segment'}), 500
