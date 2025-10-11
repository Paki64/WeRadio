"""
WeRadio - Main Application Entry Point
=======================================

Version: 0.4
"""

import logging
from flask      import Flask
from flask_cors import CORS

from config import (
    UPLOAD_FOLDER, HLS_FOLDER,
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG, FLASK_THREADED,
    LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT,
    STREAMER_MODE, 
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, 
    POSTGRES_USER, POSTGRES_PASSWORD,
    JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS,
    ROOT_DB_USER, ROOT_DB_EMAIL, ROOT_DB_PASSWORD
)
from models import RadioHLS
from routes import (
    streaming_bp, api_bp, upload_bp,
    init_api_radio, init_upload_radio,
    auth_bp, init_auth
)
from utils import (
    DatabaseManager, UserRepository, AuthService
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

    # === DATABASE SETUP ===
    try:
        db_manager = DatabaseManager(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            min_conn=2,
            max_conn=10
        )
        logger.info("✓ Database connection established")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        logger.warning("Application will start WITHOUT authentication")
        db_manager = None
    
    # === AUTH SETUP ===
    auth_service = None
    user_repo = None
    
    if db_manager:
        auth_service = AuthService(
            secret_key=JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
            expiration_hours=JWT_EXPIRATION_HOURS
        )
        user_repo = UserRepository(db_manager)
        
        # Init auth routes
        init_auth(auth_service, user_repo)
        
        # Set global auth service for lazy decorators
        from utils.auth_service import set_global_auth_service
        set_global_auth_service(auth_service)
        
        # Registra blueprint auth
        app.register_blueprint(auth_bp)
        logger.info("✓ Authentication system enabled")
    else:
        logger.warning("✗ Authentication system DISABLED (DB unavailable)")
    
    # === RADIO SETUP ===
    radio = None
    if STREAMER_MODE:
        # Streamer node: Manages streaming to clients or API-only nodes
        radio = RadioHLS(UPLOAD_FOLDER, HLS_FOLDER)
        init_api_radio(radio)
        init_upload_radio(radio)
        
        app.register_blueprint(streaming_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(upload_bp)
        logger.info("Flask application (STREAMER mode) initialized")
    else:
        # API-only node: Does not handle streaming
        init_api_radio(None)
        init_upload_radio(None)
        app.register_blueprint(streaming_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(upload_bp)
        logger.info("Flask application (API-only mode) initialized")

    return app, radio, db_manager


# === DATABASE INITIALIZATION ===

def initialize_database():
    """
    Creates necessary database tables if they do not exist.
    """
    try:
        from utils.db_manager import DatabaseManager
        
        db = DatabaseManager(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        
        # Create tables if they don't exist
        create_tables_sql = """
        -- Tabella utenti
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        
        -- Tabella sessioni (opzionale se usi JWT)
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            token VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Indici
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
        CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
        """
        
        db.execute_query(create_tables_sql, fetch=False)
        logger.info("✓ Database tables created/verified")
        
        # Creates a default admin user if missing
        from utils.auth_service import AuthService
        
        auth_svc = AuthService(JWT_SECRET_KEY)
        user_repo = UserRepository(db)
        

        admin_user = user_repo.get_user_by_username(ROOT_DB_USER)
        if not admin_user:
            password_hash = auth_svc.hash_password(ROOT_DB_PASSWORD) 
            user_repo.create_user(ROOT_DB_USER, ROOT_DB_EMAIL, password_hash, 'admin')
            logger.info(f"✓ Admin user created (username: {ROOT_DB_USER}, password: {ROOT_DB_PASSWORD})")
            logger.info("  You can now login and change its credentials")

        db.close()
        
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        raise



# === MAIN ENTRY POINT ===
def main():
    """
    Main application entry point.
    """
    # For the first run, ensure database tables exist
    try:
        initialize_database()
    except Exception as e:
        logger.error(f"Could not initialize database: {e}")
        logger.warning("Continuing without database...")
    
    app, radio, db_manager = create_app()

    # Start streaming if STREAMER node
    if radio:
        radio.start_streaming()
    
    # Display startup info
    mode = "STREAMER mode" if radio else "API-only mode"
    auth_status = "ENABLED" if db_manager else "DISABLED"
    
    logger.info("=" * 70)
    logger.info(f"WeRadio Server v0.4 ({mode})")
    logger.info(f"Authentication: {auth_status}")
    logger.info("=" * 70)
    logger.info("PUBLIC ENDPOINTS:")
    logger.info(f"  HLS Playlist: http://localhost:{FLASK_PORT}/playlist.m3u8")
    logger.info(f"  Status API:   http://localhost:{FLASK_PORT}/status")
    logger.info(f"  Tracks API:   http://localhost:{FLASK_PORT}/tracks")
    
    if db_manager:
        logger.info("")
        logger.info("AUTHENTICATION ENDPOINTS:")
        logger.info(f"  Login:        http://localhost:{FLASK_PORT}/auth/login")
        logger.info(f"  Register:     http://localhost:{FLASK_PORT}/auth/register")
        logger.info(f"  Verify:       http://localhost:{FLASK_PORT}/auth/verify")
        logger.info("")
        logger.info("PROTECTED ENDPOINTS (require auth):")
        logger.info(f"  Upload:       http://localhost:{FLASK_PORT}/upload")
        logger.info(f"  Queue Add:    http://localhost:{FLASK_PORT}/queue/add")
        logger.info(f"  Queue Remove: http://localhost:{FLASK_PORT}/queue/remove")
        logger.info(f"  Track Remove: http://localhost:{FLASK_PORT}/track/remove (admin only)")
    
    logger.info("=" * 70)
    
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
