"""
Meeting Status Management Routes

API endpoints for managing meeting status and archiving
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, date
from .meeting_status_service import MeetingStatusService
from ...auth.auth import require_auth

meeting_status_bp = Blueprint('meeting_status', __name__)

@meeting_status_bp.route('/api/meetings/status/summary', methods=['GET'])
@require_auth
def get_status_summary():
    """Get summary of meeting statuses"""
    try:
        service = MeetingStatusService()
        result = service.get_meeting_status_summary()
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['summary']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@meeting_status_bp.route('/api/meetings/status/archive', methods=['POST'])
@require_auth
def archive_old_meetings():
    """Archive meetings older than specified date"""
    try:
        data = request.get_json() or {}
        cutoff_date_str = data.get('cutoff_date')
        
        # Parse cutoff date if provided
        cutoff_date = None
        if cutoff_date_str:
            try:
                cutoff_date = datetime.strptime(cutoff_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid date format. Use YYYY-MM-DD format.'
                }), 400
        
        service = MeetingStatusService()
        result = service.archive_old_meetings(cutoff_date)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'data': {
                    'archived_count': result['archived_count'],
                    'cutoff_date': result['cutoff_date'],
                    'archived_meetings': result.get('archived_meetings', [])
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@meeting_status_bp.route('/api/meetings/status/toggle', methods=['POST'])
@require_auth
def toggle_meeting_status():
    """Toggle status of a specific meeting"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request data required'
            }), 400
        
        meeting_id = data.get('meeting_id')
        new_status = data.get('status')
        
        if not meeting_id:
            return jsonify({
                'success': False,
                'error': 'meeting_id is required'
            }), 400
        
        if not new_status or new_status not in ['active', 'archived']:
            return jsonify({
                'success': False,
                'error': 'status must be "active" or "archived"'
            }), 400
        
        service = MeetingStatusService()
        result = service.toggle_meeting_status(meeting_id, new_status)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'data': result.get('meeting')
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@meeting_status_bp.route('/api/meetings/status/<status>', methods=['GET'])
@require_auth
def get_meetings_by_status(status):
    """Get meetings filtered by status"""
    try:
        # Validate status parameter
        if status not in ['active', 'archived', 'all']:
            return jsonify({
                'success': False,
                'error': 'Invalid status. Must be "active", "archived", or "all"'
            }), 400
        
        # Get pagination parameters
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
        offset = int(request.args.get('offset', 0))
        
        service = MeetingStatusService()
        result = service.get_meetings_by_status(status, limit, offset)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'meetings': result['meetings'],
                    'count': result['count'],
                    'status_filter': status,
                    'pagination': {
                        'limit': limit,
                        'offset': offset
                    }
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid pagination parameters'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

