"""
WeRadio - Routes Package Initializer
=====================================

Version: 0.4
"""

from .streaming import streaming_bp
from .api import api_bp, init_radio as init_api_radio
from .upload import upload_bp, init_radio as init_upload_radio
from .auth import auth_bp, init_auth

__all__ = [
    'streaming_bp',
    'api_bp',
    'upload_bp',
    'auth_bp',
    'init_api_radio',
    'init_upload_radio',
    'init_auth'
]
