from flask import Blueprint, jsonify
from datetime import datetime
from src.shared.import_log import ImportLogService

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get overall dashboard statistics"""
    try:
        log_service = ImportLogService()
        
        # Get import statistics
        logs = log_service.get_recent_logs(limit=100)  # Get more logs for stats
        total_imports = len(logs)
        successful_imports = len([log for log in logs if log.get('status') == 'completed'])
        failed_imports = len([log for log in logs if log.get('status') == 'failed'])
        
        # Get recent activity (last 5)
        recent_imports = logs[:5]
        
        # Calculate success rate
        success_rate = (successful_imports / total_imports * 100) if total_imports > 0 else 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_imports': total_imports,
                'successful_imports': successful_imports,
                'failed_imports': failed_imports,
                'success_rate': round(success_rate, 1),
                'recent_activity': recent_imports
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to get dashboard stats: {str(e)}"
        }), 500

@admin_bp.route('/system/health', methods=['GET'])
def get_system_health():
    """Get system health status"""
    try:
        log_service = ImportLogService()
        
        # Basic health checks
        health_status = {
            'database': 'healthy',  # Could add actual DB ping
            'api_connectivity': 'unknown',  # Could add API test
            'last_import': None,
            'system_uptime': datetime.now().isoformat()
        }
        
        # Get last import status
        recent_logs = log_service.get_recent_logs(limit=1)
        if recent_logs:
            last_import = recent_logs[0]
            health_status['last_import'] = {
                'status': last_import.get('status'),
                'started_at': last_import.get('started_at'),
                'import_type': last_import.get('import_type')
            }
        
        return jsonify({
            'success': True,
            'data': health_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to get system health: {str(e)}"
        }), 500

