"""
WeRadio - Main Application Entry Point
=======================================

Version: 0.3
"""

import logging
from flask      import Flask
from flask_cors import CORS

from config import (
    UPLOAD_FOLDER, HLS_FOLDER,
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG, FLASK_THREADED,
    LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT,
    STREAMER_MODE
)
from models import RadioHLS
from routes import (
    streaming_bp, api_bp, upload_bp,
    init_api_radio, init_upload_radio
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger('WeRadio')
logger.setLevel(getattr(logging, LOG_LEVEL))
logging.getLogger('werkzeug').setLevel(logging.WARNING)


def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__)
    CORS(app)

    radio = None
    if STREAMER_MODE:
        # Streamer node: HLS + FFmpeg
        radio = RadioHLS(UPLOAD_FOLDER, HLS_FOLDER)
        init_api_radio(radio)
        init_upload_radio(radio)
        app.register_blueprint(streaming_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(upload_bp)
        logger.info("Flask application (STREAMER mode) initialized")
    else:
        # API-only node:
        init_api_radio(None)
        init_upload_radio(None)
        app.register_blueprint(api_bp)
        app.register_blueprint(upload_bp)
        logger.info("Flask application (API-only mode) initialized")

    return app, radio


# === MAIN ENTRY POINT ===
def main():
    """
    Main application entry point.
    """
    app, radio = create_app()

    # Start streaming if STREAMER node
    if radio:
        radio.start_streaming()
    
    # Display startup info
    mode = "STREAMER mode" if radio else "API-only mode"
    logger.info("=" * 60)
    logger.info(f"WeRadio Server v0.2 ({mode})")
    logger.info("=" * 60)
    
    if radio:
        logger.info(f"HLS Playlist: http://localhost:{FLASK_PORT}/playlist.m3u8")
    
    logger.info(f"Status API:   http://localhost:{FLASK_PORT}/status")
    logger.info(f"Tracks API:   http://localhost:{FLASK_PORT}/tracks")
    logger.info(f"Upload API:   http://localhost:{FLASK_PORT}/upload")
    logger.info("=" * 60)

    # Start Flask server
    try:
        app.run(
            host=FLASK_HOST,
            port=FLASK_PORT,
            threaded=FLASK_THREADED,
            debug=FLASK_DEBUG
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if radio:
            radio.stop()
    except Exception as e:
        logger.error(f"Server error: {e}")
        if radio:
            radio.stop()


# Main thread
if __name__ == '__main__':
    main()
