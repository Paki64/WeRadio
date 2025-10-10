"""
WeRadio - Database Manager
===========================

Manages database connections and queries

Version: v0.4
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import logging
from contextlib import contextmanager

logger = logging.getLogger('WeRadio.Database')


class DatabaseManager:
    """
    Manages the DB connection pool and its queries
    """
    
    def __init__(self, host, port, database, user, password, min_conn=1, max_conn=10):
        """
        Initializes the connection pool
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Username
            password: Password
            min_conn: Min pool connections
            max_conn: Max pool connections
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        
        try:
            self.pool = SimpleConnectionPool(
                min_conn,
                max_conn,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            logger.info(f"Database pool created: {database}@{host}:{port}")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        Pool connection context manager
        """
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            self.pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, cursor_factory=RealDictCursor):
        """
        Context manager for cursor
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(self, query, params=None, fetch=True):
        """
        Execute a query and return the results
        
        Args:
            query: Query SQL
            params: Query parameters
            fetch: return the results
        """
        with self.get_cursor() as cur:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            return None
    
    def execute_one(self, query, params=None):
        """
        Execute a query and return a single result
        """
        with self.get_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()
    
    def close(self):
        """
        Close all connections in the pool
        """
        if self.pool:
            self.pool.closeall()
            logger.info("Database pool closed")


class UserRepository:
    """
    Repository for managing user data
    """
    
    def __init__(self, db_manager):
        """
        Simpleton pattern
        """
        self.db = db_manager
    
    def create_user(self, username, email, password_hash, role='user'):
        """
        Creates a new user
        """
        query = """
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%(username)s, %(email)s, %(password_hash)s, %(role)s)
            RETURNING id, username, email, role, created_at
        """
        try:
            return self.db.execute_one(query, {
                'username': username,
                'email': email,
                'password_hash': password_hash,
                'role': role
            })
        except psycopg2.IntegrityError as e:
            logger.warning(f"User creation failed (duplicate): {e}")
            return None
    
    def get_user_by_username(self, username):
        """
        Find user by username
        """
        query = "SELECT * FROM users WHERE username = %s"
        return self.db.execute_one(query, (username,))
    
    def get_user_by_id(self, user_id):
        """
        Find user by ID
        """
        query = "SELECT * FROM users WHERE id = %s"
        return self.db.execute_one(query, (user_id,))
    
    def update_last_login(self, user_id):
        """
        Update last login timestamp
        """
        query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s"
        self.db.execute_query(query, (user_id,), fetch=False)
    
    def get_all_users(self):
        """
        Returns a list of all users
        """
        query = "SELECT id, username, email, role, created_at, last_login FROM users ORDER BY created_at DESC"
        return self.db.execute_query(query)
    
    def delete_user(self, user_id):
        """
        Deletes a user
        """
        query = "DELETE FROM users WHERE id = %s"
        self.db.execute_query(query, (user_id,), fetch=False)
    
    def update_user_role(self, user_id, new_role):
        """
        Updates a user's role
        """
        query = "UPDATE users SET role = %s WHERE id = %s"
        self.db.execute_query(query, (new_role, user_id), fetch=False)
    
    def get_user_by_email(self, email):
        """
        Find user by email
        """
        query = "SELECT * FROM users WHERE email = %s"
        return self.db.execute_one(query, (email,))
    
    def update_user(self, user_id, updates):
        """
        Updates user fields
        """
        if not updates:
            return
        set_parts = []
        params = []
        for key, value in updates.items():
            set_parts.append(f"{key} = %s")
            params.append(value)
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(set_parts)} WHERE id = %s"
        self.db.execute_query(query, params, fetch=False)


class SessionRepository:
    """
    Session management repository
    """
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_session(self, user_id, token, expires_at):
        """
        Creates a new session
        """
        query = """
            INSERT INTO sessions (user_id, token, expires_at)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        return self.db.execute_one(query, (user_id, token, expires_at))
    
    def get_session(self, token):
        """
        Retrieves a valid session by token
        """
        query = """
            SELECT s.*, u.username, u.email, u.role
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = %s AND s.expires_at > CURRENT_TIMESTAMP
        """
        return self.db.execute_one(query, (token,))
    
    def delete_session(self, token):
        """
        Manages logout (session termination)
        """
        query = "DELETE FROM sessions WHERE token = %s"
        self.db.execute_query(query, (token,), fetch=False)
    
    def delete_expired_sessions(self):
        """
        Cleans expired sessions
        """
        query = "DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP"
        self.db.execute_query(query, fetch=False)
    
    def delete_user_sessions(self, user_id):
        """
        Deletes all sessions for a user
        """
        query = "DELETE FROM sessions WHERE user_id = %s"
        self.db.execute_query(query, (user_id,), fetch=False)