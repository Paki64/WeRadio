"""
WeRadio - Authentication Service
=================================

Manages user authentication and authorization

Version: 0.4
"""

import jwt
import bcrypt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g

logger = logging.getLogger('WeRadio.Auth')


class AuthService:
    """
    Authentication service
    """
    
    def __init__(self, secret_key, algorithm='HS256', expiration_hours=24):
        """
        Initializes the authentication service
        
        Args:
            secret_key: JWT secret key
            algorithm: JWT algorithm
            expiration_hours: Token expiration time
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours
    
    def hash_password(self, password):
        """
        Hashes the password

        Args:
            password: Cleartext password (to be hashed)
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password, password_hash):
        """
        Verifies the hashed password
        
        Args:
            password: Cleartext password
            password_hash: Hashed password
        """
        try:
            password_bytes = password.encode('utf-8')
            hash_bytes = password_hash.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def generate_token(self, user_id, username, role):
        """
        Generates a JWT token for the user
        
        Args:
            user_id: User ID
            username: Username
            role: User role
        """
        now = datetime.utcnow()
        expiration = now + timedelta(hours=self.expiration_hours)
        
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'iat': now,         # Issued at
            'exp': expiration   # Expiration
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_token(self, token):
        """
        Verifies and decodes a JWT token
        
        Args:
            token: JWT token
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def extract_token_from_request(self):
        """
        Extracts the token from the Flask request
        """
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return None
        
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
        
        return parts[1]


def create_auth_decorator(auth_service_or_getter, required_roles=None):
    """
    Authentication decorator factory

    Args:
        auth_service_or_getter: AuthService instance or callable that returns AuthService instance
        required_roles: List of required roles
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get auth_service dynamically if it's a callable
            if callable(auth_service_or_getter):
                auth_service = auth_service_or_getter()
            else:
                auth_service = auth_service_or_getter

            if auth_service is None:
                # If no auth service, allow the request (for development/testing)
                logger.warning("No auth service configured, allowing request")
                return f(*args, **kwargs)

            token = auth_service.extract_token_from_request()

            if not token:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Missing or invalid token'
                }), 401

            payload = auth_service.verify_token(token)

            if not payload:
                return jsonify({
                    'error': 'Invalid token',
                    'message': 'Token expired or invalid'
                }), 401

            if required_roles:
                user_role = payload.get('role')
                if user_role not in required_roles:
                    return jsonify({
                        'error': 'Forbidden',
                        'message': 'Insufficient permissions'
                    }), 403

            g.current_user = payload

            return f(*args, **kwargs)

        return decorated_function
    return decorator


# Global auth service reference for lazy decorators
_current_auth_service = None

def set_global_auth_service(auth_service):
    """
    Set the global auth service instance for lazy decorators
    
    Args:
        auth_service: AuthService instance
    """
    global _current_auth_service
    _current_auth_service = auth_service

def get_global_auth_service():
    """
    Get the global auth service instance
    
    Returns:
        AuthService instance or None
    """
    return _current_auth_service


# === Predefined decorators ===

def require_auth(auth_service=None):
    """
    Decorator: Authentication required
    
    Args:
        auth_service: AuthService instance (optional, uses global if None)
    """
    if auth_service is None:
        return create_auth_decorator(get_global_auth_service, required_roles=None)
    return create_auth_decorator(auth_service, required_roles=None)


def require_admin(auth_service=None):
    """
    Decorator: Admin role required
    
    Args:
        auth_service: AuthService instance (optional, uses global if None)
    """
    if auth_service is None:
        return create_auth_decorator(get_global_auth_service, required_roles=['admin'])
    return create_auth_decorator(auth_service, required_roles=['admin'])


def require_user_or_admin(auth_service=None):
    """
    Decorator: User or admin role required
    
    Args:
        auth_service: AuthService instance (optional, uses global if None)
    """
    if auth_service is None:
        return create_auth_decorator(get_global_auth_service, required_roles=['user', 'admin'])
    return create_auth_decorator(auth_service, required_roles=['user', 'admin'])