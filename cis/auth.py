# Authentication and User Management for CIS
import os
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import re

try:
    from .database import create_trial_user, get_user_subscription
except ImportError:
    from database import create_trial_user, get_user_subscription

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

class ValidationError(Exception):
    """Raised when validation fails."""
    pass

def hash_password(password: str) -> str:
    """Hash password using PBKDF2."""
    salt = secrets.token_hex(32)
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${pwd_hash.hex()}"

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    try:
        salt, pwd_hash = password_hash.split('$')
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return new_hash.hex() == pwd_hash
    except Exception:
        return False

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.
    
    Requirements:
    - At least 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    return True, "Password is valid"

def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username format."""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 30:
        return False, "Username must not exceed 30 characters"
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, hyphens, and underscores"
    
    return True, "Username is valid"

def register_free_trial(email: str, username: str, password: str, organization: str = None) -> Dict:
    """
    Register a new user for free trial.
    
    Returns:
        Dict with user and subscription info
        
    Raises:
        ValidationError: If input validation fails
        AuthenticationError: If registration fails
    """
    # Validate email
    if not validate_email(email):
        raise ValidationError("Invalid email format")
    
    # Validate username
    valid, msg = validate_username(username)
    if not valid:
        raise ValidationError(msg)
    
    # Validate password
    valid, msg = validate_password(password)
    if not valid:
        raise ValidationError(msg)
    
    # Hash password
    password_hash = hash_password(password)
    
    # Create trial user in database
    try:
        user_data = create_trial_user(email, username, password_hash, organization)
        
        return {
            'success': True,
            'user_id': user_data['user_id'],
            'subscription_id': user_data['subscription_id'],
            'email': user_data['email'],
            'plan': 'free_trial',
            'trial_end_date': user_data['trial_end_date'],
            'days_trial': 14,
            'message': 'Free trial account created successfully! You have 14 days to explore all features.'
        }
    except ValueError as e:
        raise AuthenticationError(str(e))

def generate_api_token(user_id: int, subscription_id: int) -> str:
    """Generate an API token for user."""
    token_data = {
        'user_id': user_id,
        'subscription_id': subscription_id,
        'generated_at': datetime.now().isoformat(),
        'token': secrets.token_urlsafe(32)
    }
    return token_data['token']

def create_session_token(user_id: int, subscription_id: int, expires_in_hours: int = 24) -> Dict:
    """Create a session token for authentication."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=expires_in_hours)
    
    return {
        'token': token,
        'user_id': user_id,
        'subscription_id': subscription_id,
        'expires_at': expires_at.isoformat(),
        'token_type': 'Bearer'
    }

def validate_session_token(token: str) -> Optional[Dict]:
    """Validate a session token (would normally check against database)."""
    # This is a placeholder - in production, validate against session storage
    if not token or len(token) < 20:
        return None
    
    return {
        'valid': True,
        'token': token
    }
