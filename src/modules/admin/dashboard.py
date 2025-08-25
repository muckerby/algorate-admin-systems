from flask import Blueprint, jsonify
from datetime import datetime
from src.shared.import_log import ImportLog

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get overall dashboard statistics"""
    try:
        # Get import statistics
        total_imports = ImportLog.query.count()
        successful_imports = ImportLog.query.filter_by(status='completed').count()
        failed_imports = ImportLog.query.filter_by(status='failed').count()
        
        # Get recent activity
        recent_imports = ImportLog.query.order_by(ImportLog.started_at.desc()).limit(5).all()
        
        # Calculate success rate
        success_rate = (successful_imports / total_imports * 100) if total_imports > 0 else 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_imports': total_imports,
                'successful_imports': successful_imports,
                'failed_imports': failed_imports,
                'success_rate': round(success_rate, 1),
                'recent_activity': [log.to_dict() for log in recent_imports]
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
        # Basic health checks
        health_status = {
            'database': 'healthy',  # Could add actual DB ping
            'api_connectivity': 'unknown',  # Could add API test
            'last_import': None,
            'system_uptime': datetime.now().isoformat()
        }
        
        # Get last import status
        last_import = ImportLog.query.order_by(ImportLog.started_at.desc()).first()
        if last_import:
            health_status['last_import'] = {
                'status': last_import.status,
                'started_at': last_import.started_at.isoformat() if last_import.started_at else None,
                'import_type': last_import.import_type
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

