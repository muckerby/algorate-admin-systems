"""
Flask routes for ratings polling management
"""

from flask import Blueprint, jsonify, request
from src.modules.imports.meetings.ratings_polling_service import RatingsPollingService
from src.modules.auth.auth import require_auth

ratings_polling_bp = Blueprint('ratings_polling', __name__)

@ratings_polling_bp.route('/ratings/check-updates', methods=['POST'])
@require_auth
def check_ratings_updates():
    """Check for ratings updates without triggering refresh"""
    try:
        data = request.get_json() or {}
        days_back = data.get('days_back', 7)
        
        if days_back < 1 or days_back > 30:
            return jsonify({
                'success': False,
                'error': 'days_back must be between 1 and 30'
            }), 400
        
        polling_service = RatingsPollingService()
        result = polling_service.check_ratings_updates(days_back)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to check ratings updates: {str(e)}"
        }), 500

@ratings_polling_bp.route('/ratings/refresh', methods=['POST'])
@require_auth
def trigger_ratings_refresh():
    """Manually trigger ratings refresh for specific meetings"""
    try:
        data = request.get_json() or {}
        meetings_to_update = data.get('meetings_to_update', [])
        
        if not meetings_to_update:
            return jsonify({
                'success': False,
                'error': 'No meetings specified for refresh'
            }), 400
        
        polling_service = RatingsPollingService()
        result = polling_service.trigger_ratings_refresh(meetings_to_update)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to refresh ratings: {str(e)}"
        }), 500

@ratings_polling_bp.route('/ratings/poll', methods=['POST'])
@require_auth
def run_ratings_polling():
    """Run complete ratings polling cycle"""
    try:
        data = request.get_json() or {}
        days_back = data.get('days_back', 7)
        auto_refresh = data.get('auto_refresh', True)
        
        if days_back < 1 or days_back > 30:
            return jsonify({
                'success': False,
                'error': 'days_back must be between 1 and 30'
            }), 400
        
        polling_service = RatingsPollingService()
        result = polling_service.run_ratings_polling_cycle(days_back, auto_refresh)
        
        return jsonify({
            'success': result.get('polling_completed', False),
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to run ratings polling: {str(e)}"
        }), 500

@ratings_polling_bp.route('/ratings/status', methods=['GET'])
@require_auth
def get_ratings_status():
    """Get current ratings status and statistics"""
    try:
        polling_service = RatingsPollingService()
        
        # Get recent meetings with ratings info
        recent_meetings = polling_service.supabase.table('meetings').select(
            'pf_meeting_id, track_name, meeting_date, ratings_updated, status'
        ).gte('meeting_date', '2025-08-20').order('meeting_date', desc=True).limit(50).execute()
        
        # Calculate statistics
        total_meetings = len(recent_meetings.data) if recent_meetings.data else 0
        meetings_with_ratings = 0
        meetings_without_ratings = 0
        
        for meeting in recent_meetings.data or []:
            if meeting.get('ratings_updated'):
                meetings_with_ratings += 1
            else:
                meetings_without_ratings += 1
        
        return jsonify({
            'success': True,
            'data': {
                'total_recent_meetings': total_meetings,
                'meetings_with_ratings': meetings_with_ratings,
                'meetings_without_ratings': meetings_without_ratings,
                'ratings_coverage_percent': round((meetings_with_ratings / total_meetings * 100) if total_meetings > 0 else 0, 1),
                'recent_meetings': recent_meetings.data[:10] if recent_meetings.data else []
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to get ratings status: {str(e)}"
        }), 500

