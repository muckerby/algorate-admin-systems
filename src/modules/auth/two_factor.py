import pyotp
import qrcode
import io
import base64
from flask import Blueprint, jsonify, request, session
import os

two_factor_bp = Blueprint('two_factor', __name__)

class TwoFactorService:
    """Service for handling Two-Factor Authentication"""
    
    @staticmethod
    def generate_secret():
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(secret, user_email="admin@algorated.com.au"):
        """Generate QR code for authenticator app setup"""
        # Create TOTP URI
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name="Algorated Admin"
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 string
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{qr_code_data}"
    
    @staticmethod
    def verify_token(secret, token):
        """Verify TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # Allow 1 window tolerance
    
    @staticmethod
    def get_current_token(secret):
        """Get current TOTP token (for testing)"""
        totp = pyotp.TOTP(secret)
        return totp.now()

@two_factor_bp.route('/setup', methods=['POST'])
def setup_2fa():
    """Setup 2FA for admin user"""
    try:
        # Check if user is authenticated with password
        if not session.get('password_verified'):
            return jsonify({
                'success': False,
                'error': 'Password authentication required first'
            }), 401
        
        # Generate new secret
        secret = TwoFactorService.generate_secret()
        
        # Generate QR code
        qr_code = TwoFactorService.generate_qr_code(secret)
        
        # Store secret in session temporarily (until verified)
        session['temp_2fa_secret'] = secret
        
        return jsonify({
            'success': True,
            'data': {
                'secret': secret,
                'qr_code': qr_code,
                'manual_entry_key': secret
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to setup 2FA: {str(e)}"
        }), 500

@two_factor_bp.route('/verify-setup', methods=['POST'])
def verify_2fa_setup():
    """Verify 2FA setup with first token"""
    try:
        data = request.get_json() or {}
        token = data.get('token', '').strip()
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Token is required'
            }), 400
        
        # Get temporary secret from session
        secret = session.get('temp_2fa_secret')
        if not secret:
            return jsonify({
                'success': False,
                'error': '2FA setup not initiated'
            }), 400
        
        # Verify token
        if TwoFactorService.verify_token(secret, token):
            # Save secret as environment variable (in production, store in database)
            # For now, we'll store in session as confirmed
            session['2fa_secret'] = secret
            session['2fa_enabled'] = True
            session.pop('temp_2fa_secret', None)
            
            return jsonify({
                'success': True,
                'message': '2FA setup completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid token. Please try again.'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to verify 2FA setup: {str(e)}"
        }), 500

@two_factor_bp.route('/verify', methods=['POST'])
def verify_2fa():
    """Verify 2FA token during login"""
    try:
        data = request.get_json() or {}
        token = data.get('token', '').strip()
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Token is required'
            }), 400
        
        # Check if user has password verified
        if not session.get('password_verified'):
            return jsonify({
                'success': False,
                'error': 'Password authentication required first'
            }), 401
        
        # Get 2FA secret (in production, get from database)
        secret = session.get('2fa_secret') or os.getenv('ADMIN_2FA_SECRET')
        if not secret:
            return jsonify({
                'success': False,
                'error': '2FA not configured'
            }), 400
        
        # Verify token
        if TwoFactorService.verify_token(secret, token):
            session['2fa_verified'] = True
            session['authenticated'] = True
            
            return jsonify({
                'success': True,
                'message': 'Authentication successful'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid token. Please try again.'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to verify 2FA: {str(e)}"
        }), 500

@two_factor_bp.route('/status', methods=['GET'])
def get_2fa_status():
    """Get 2FA status for current user"""
    try:
        # Check if 2FA is enabled
        is_enabled = bool(session.get('2fa_enabled') or os.getenv('ADMIN_2FA_SECRET'))
        is_verified = session.get('2fa_verified', False)
        password_verified = session.get('password_verified', False)
        
        return jsonify({
            'success': True,
            'data': {
                'enabled': is_enabled,
                'verified': is_verified,
                'password_verified': password_verified,
                'authenticated': session.get('authenticated', False)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to get 2FA status: {str(e)}"
        }), 500

@two_factor_bp.route('/disable', methods=['POST'])
def disable_2fa():
    """Disable 2FA (admin only)"""
    try:
        # Check if user is fully authenticated
        if not session.get('authenticated'):
            return jsonify({
                'success': False,
                'error': 'Full authentication required'
            }), 401
        
        # Clear 2FA settings
        session.pop('2fa_secret', None)
        session.pop('2fa_enabled', None)
        session.pop('2fa_verified', None)
        
        return jsonify({
            'success': True,
            'message': '2FA disabled successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to disable 2FA: {str(e)}"
        }), 500

