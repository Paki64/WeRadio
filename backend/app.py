"""
WeRadio - Main Application Entry Point
=======================================

Version: 0.1
"""

import logging
from flask      import Flask
from flask_cors import CORS

from config import (
    UPLOAD_FOLDER, HLS_FOLDER,
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG, FLASK_THREADED,
    LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT
)
from models import RadioHLS
from routes import (
    streaming_bp, api_bp, upload_bp,
    init_api_radio, init_upload_radio
)


# === LOGGING CONFIGURATION ===
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger('WeRadio')
logger.setLevel(getattr(logging, LOG_LEVEL))
logging.getLogger('werkzeug').setLevel(logging.WARNING)


# === FLASK APPLICATION ===
def create_app():
    """
    Creates and configures the Flask application.
    
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    CORS(app) # Enables Cross-Origin Resource Sharing for all routes
    
    # Initialize RadioHLS
    radio = RadioHLS(UPLOAD_FOLDER, HLS_FOLDER) # Create RadioHLS instance
    
    # Initialize route modules with radio instance
    init_api_radio(radio)
    init_upload_radio(radio)
    
    # Register blueprints
    app.register_blueprint(streaming_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(upload_bp)
    
    logger.info("Flask application initialized")
    
    return app, radio


# === MAIN ENTRY POINT ===
def main():
    """
    Main application entry point.
    """
    app, radio = create_app()
    
    # Start radio streaming
    radio.start_streaming()
    
    # Print banner
    logger.info("=" * 60)
    logger.info("WeRadio Server v0.1")
    logger.info("=" * 60)
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
        radio.stop()
    except Exception as e:
        logger.error(f"Server error: {e}")
        radio.stop()


# Main execution
if __name__ == '__main__':
    main()
