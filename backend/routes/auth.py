"""
WeRadio - Authentication Routes
================================

Flask routes for user authentication

Version: 0.4
"""

import logging
from flask import Blueprint, request, jsonify

from utils import require_admin

logger = logging.getLogger('WeRadio.Routes.Auth')

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Global instance init
auth_service = None
user_repo = None


def init_auth(auth_svc, usr_repo):
    """
    Initialize authentication services
    
    Args:
        auth_svc: AuthService Instance
        usr_repo: UserRepository Instance
    """
    global auth_service, user_repo
    auth_service = auth_svc
    user_repo = usr_repo


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login endpoint
    
    Request JSON:
        {
            "username": "mario",
            "password": "password123"
        }
    
    Response:
        {
            "success": true,
            "token": "eyJ...",
            "user": {
                "id": 1,
                "username": "mario",
                "role": "admin"
            }
        }
    """
    # Input insertion and validation
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    # User lookup
    user = user_repo.get_user_by_username(username)
    
    if not user:
        logger.warning(f"Login failed: user not found ({username})")
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Password verification
    if not auth_service.verify_password(password, user['password_hash']):
        logger.warning(f"Login failed: wrong password ({username})")
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Token generation
    token = auth_service.generate_token(
        user['id'],
        user['username'],
        user['role']
    )
    
    # Update last login timestamp
    user_repo.update_last_login(user['id'])
    logger.info(f"User logged in: {username} (role: {user['role']})")
    
    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role']
        }
    })


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    
    Request JSON:
        {
            "username": "mario",
            "email": "mario@example.com",
            "password": "password123"
        }
    
    Response:
        {
            "success": true,
            "user": {...}
        }
    """
    # Input insertion and validation
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({
            'error': 'Username, email and password required'
        }), 400
    
    # Username and email validation
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    if '@' not in email:
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Password hashing
    password_hash = auth_service.hash_password(password)
    
    # User creation
    user = user_repo.create_user(username, email, password_hash, role='user')
    
    if not user:
        return jsonify({
            'error': 'Registration failed',
            'message': 'Username or email already exists'
        }), 409
    
    logger.info(f"New user registered: {username}")
    
    return jsonify({
        'success': True,
        'message': 'User registered successfully',
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role']
        }
    }), 201


@auth_bp.route('/verify', methods=['GET'])
def verify():
    """
    Token verification endpoint
    
    Headers:
        Authorization: Bearer <token>
    
    Response:
        {
            "valid": true,
            "user": {...}
        }
    """
    token = auth_service.extract_token_from_request()
    
    if not token:
        return jsonify({
            'valid': False,
            'error': 'No token provided'
        }), 401
    
    payload = auth_service.verify_token(token)
    
    if not payload:
        return jsonify({
            'valid': False,
            'error': 'Invalid or expired token'
        }), 401
    
    # Get user info from DB
    user = user_repo.get_user_by_id(payload['user_id'])
    
    if not user:
        return jsonify({
            'valid': False,
            'error': 'User not found'
        }), 401
    
    return jsonify({
        'valid': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role']
        }
    })


@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    """
    Update user profile (credentials)
    
    Headers:
        Authorization: Bearer <token>
    
    Request JSON:
        {
            "username": "new_username",  // optional
            "email": "new_email",        // optional
            "password": "new_password"   // optional
        }
    
    Response:
        {
            "success": true,
            "message": "Profile updated successfully",
            "user": {...},
            "token": "new_token"  // if username changed
        }
    """
    # Authentication
    token = auth_service.extract_token_from_request()
    if not token:
        return jsonify({'error': 'Authentication required'}), 401
    
    payload = auth_service.verify_token(token)
    if not payload:
        return jsonify({'error': 'Invalid token'}), 401
    
    user_id = payload['user_id']
    
    # Get current user
    user = user_repo.get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Parse request data
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    updates = {}
    errors = []
    
    # Validate and prepare username update
    new_username = data.get('username')
    if new_username is not None:
        if len(new_username) < 3:
            errors.append('Username must be at least 3 characters')
        else:
            existing = user_repo.get_user_by_username(new_username)
            if existing and existing['id'] != user_id:
                errors.append('Username already taken')
            else:
                updates['username'] = new_username
    
    # Validate and prepare email update
    new_email = data.get('email')
    if new_email is not None:
        if '@' not in new_email:
            errors.append('Invalid email format')
        else:
            existing = user_repo.get_user_by_email(new_email)
            if existing and existing['id'] != user_id:
                errors.append('Email already taken')
            else:
                updates['email'] = new_email
    
    # Validate and prepare password update
    new_password = data.get('password')
    if new_password is not None:
        if len(new_password) < 6:
            errors.append('Password must be at least 6 characters')
        else:
            updates['password_hash'] = auth_service.hash_password(new_password)
    
    if errors:
        return jsonify({'error': '; '.join(errors)}), 400
    
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    # Update user
    user_repo.update_user(user_id, updates)
    
    # Prepare response
    updated_user = {
        'id': user_id,
        'username': updates.get('username', user['username']),
        'email': updates.get('email', user['email']),
        'role': user['role']
    }
    
    response = {
        'success': True,
        'message': 'Profile updated successfully',
        'user': updated_user
    }
    
    # Generate new token if username changed (to reflect in token)
    if 'username' in updates:
        new_token = auth_service.generate_token(user_id, updates['username'], user['role'])
        response['token'] = new_token
    
    logger.info(f"User {user_id} updated profile")
    
    return jsonify(response)



# === ADMIN ROUTES ===

@auth_bp.route('/users', methods=['GET'])
@require_admin()
def list_users():
    """
    Lists all users
    
    Headers:
        Authorization: Bearer <token>
    """
    users = user_repo.get_all_users()
    
    return jsonify({
        'users': users,
        'total': len(users)
    })


@auth_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@require_admin()
def update_user_role(user_id):
    """
    Edit user role
    
    Request JSON:
        {
            "role": "admin"  // admin, user, listener
        }
    """
    # Get current user from token
    token = auth_service.extract_token_from_request()
    payload = auth_service.verify_token(token)
    
    data = request.get_json()
    new_role = data.get('role')
    
    if new_role not in ['admin', 'user', 'listener']:
        return jsonify({'error': 'Invalid role'}), 400
    
    if payload['user_id'] == user_id:
        return jsonify({'error': 'Cannot modify your own role'}), 400
    
    user_repo.update_user_role(user_id, new_role)
    
    logger.info(f"User {user_id} role updated to {new_role}")
    
    return jsonify({
        'success': True,
        'message': f'User role updated to {new_role}'
    })


@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_admin()
def delete_user(user_id):
    """
    Delete a user
    """
    # Get current user from token
    token = auth_service.extract_token_from_request()
    payload = auth_service.verify_token(token)
    
    if payload['user_id'] == user_id:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    
    user_repo.delete_user(user_id)
    
    logger.info(f"User {user_id} deleted")
    
    return jsonify({
        'success': True,
        'message': 'User deleted successfully'
    })