from flask import Blueprint, jsonify, request, session
from datetime import datetime
import hashlib
import os

auth_bp = Blueprint('auth', __name__)

# Simple admin authentication (placeholder for future expansion)
ADMIN_PASSWORD_HASH = None  # Will be set from environment variable

def init_auth():
    """Initialize authentication system"""
    global ADMIN_PASSWORD_HASH
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')  # Default for development
    ADMIN_PASSWORD_HASH = hashlib.sha256(admin_password.encode()).hexdigest()

@auth_bp.route('/login', methods=['POST'])
def login():
    """Simple admin login (placeholder)"""
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        if not ADMIN_PASSWORD_HASH:
            init_auth()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if password_hash == ADMIN_PASSWORD_HASH:
            session['authenticated'] = True
            session['login_time'] = datetime.now().isoformat()
            
            return jsonify({
                'success': True,
                'message': 'Authentication successful'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid password'
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Login failed: {str(e)}"
        }), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })

@auth_bp.route('/status', methods=['GET'])
def auth_status():
    """Check authentication status"""
    authenticated = session.get('authenticated', False)
    login_time = session.get('login_time')
    
    return jsonify({
        'success': True,
        'data': {
            'authenticated': authenticated,
            'login_time': login_time
        }
    })

# Authentication decorator (for future use)
def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

