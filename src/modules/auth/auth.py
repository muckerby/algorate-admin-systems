from flask import Blueprint, request, jsonify, session
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user with password (first step)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        password = data.get('password')
        if not password:
            return jsonify({'success': False, 'error': 'Password is required'}), 400
        
        # Get admin password from environment
        admin_password = os.getenv('ADMIN_PASSWORD')
        if not admin_password:
            return jsonify({'success': False, 'error': 'Admin password not configured'}), 500
        
        # Verify password
        if password == admin_password:
            # Set password verification in session
            session['password_verified'] = True
            
            # Check if 2FA is enabled
            has_2fa = bool(session.get('2fa_enabled') or os.getenv('ADMIN_2FA_SECRET'))
            
            if has_2fa:
                # 2FA required - don't set full authentication yet
                return jsonify({
                    'success': True,
                    'requires_2fa': True,
                    'message': 'Password verified. Please enter your 2FA code.'
                })
            else:
                # No 2FA - full authentication
                session['authenticated'] = True
                return jsonify({
                    'success': True,
                    'requires_2fa': False,
                    'message': 'Login successful'
                })
        else:
            return jsonify({'success': False, 'error': 'Invalid password'}), 401
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user"""
    try:
        # Clear all session data
        session.clear()
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@auth_bp.route('/status', methods=['GET'])
def status():
    """Get authentication status"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'authenticated': session.get('authenticated', False),
                'password_verified': session.get('password_verified', False),
                '2fa_verified': session.get('2fa_verified', False),
                '2fa_enabled': bool(session.get('2fa_enabled') or os.getenv('ADMIN_2FA_SECRET'))
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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

