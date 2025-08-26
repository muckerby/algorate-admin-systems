from flask import Blueprint, jsonify, request
import os
from supabase import create_client, Client

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/clear-data', methods=['POST'])
def clear_test_data():
    """Clear test data from meetings and import_logs tables"""
    try:
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_key:
            return jsonify({
                'success': False,
                'error': 'Supabase credentials not configured'
            }), 500
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Get request parameters
        data = request.get_json() or {}
        clear_meetings = data.get('clear_meetings', True)
        clear_logs = data.get('clear_logs', True)
        
        results = {}
        
        # Clear meetings table
        if clear_meetings:
            try:
                meetings_result = supabase.table('meetings').delete().neq('meeting_id', 0).execute()
                results['meetings_cleared'] = len(meetings_result.data) if meetings_result.data else 0
            except Exception as e:
                results['meetings_error'] = str(e)
        
        # Clear import_logs table
        if clear_logs:
            try:
                logs_result = supabase.table('import_logs').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                results['logs_cleared'] = len(logs_result.data) if logs_result.data else 0
            except Exception as e:
                results['logs_error'] = str(e)
        
        return jsonify({
            'success': True,
            'message': 'Data clearing completed',
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to clear data: {str(e)}"
        }), 500

@admin_bp.route('/admin/data-stats', methods=['GET'])
def get_data_stats():
    """Get current data statistics"""
    try:
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_key:
            return jsonify({
                'success': False,
                'error': 'Supabase credentials not configured'
            }), 500
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Get counts
        meetings_count = len(supabase.table('meetings').select('meeting_id').execute().data)
        logs_count = len(supabase.table('import_logs').select('id').execute().data)
        
        return jsonify({
            'success': True,
            'data': {
                'meetings_count': meetings_count,
                'import_logs_count': logs_count
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to get stats: {str(e)}"
        }), 500

