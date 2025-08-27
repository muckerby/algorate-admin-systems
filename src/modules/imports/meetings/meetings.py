from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta, timezone
import requests
import os
from src.shared.import_log import ImportLogService
from src.modules.imports.meetings.meetings_import_service import MeetingsImportService

# Define AEST timezone (UTC+10)
AEST = timezone(timedelta(hours=10))

meetings_bp = Blueprint('meetings', __name__)

@meetings_bp.route('/import/meetings', methods=['POST'])
def import_meetings():
    """Manual trigger for meetings import"""
    try:
        # Get date and test mode from request or use defaults
        data = request.get_json() or {}
        date_str = data.get('date')
        test_mode = data.get('test_mode', False)  # Default to production mode
        
        if date_str:
            # Convert from Australian format DD/MM/YYYY to ISO format
            try:
                date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                iso_date = date_obj.strftime('%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid date format. Use DD/MM/YYYY format.'
                }), 400
        else:
            # Default to tomorrow
            tomorrow = datetime.now() + timedelta(days=1)
            iso_date = tomorrow.strftime('%Y-%m-%d')
            date_str = tomorrow.strftime('%d/%m/%Y')
        
        # Initialize services
        import_service = MeetingsImportService()
        log_service = ImportLogService()
        
        # Determine import mode and trigger type
        import_mode = 'test' if test_mode else 'production'
        
        # Start import log
        log_id = log_service.create_log(
            import_type='meetings',
            trigger_type='manual',
            import_date=iso_date,
            import_mode=import_mode
        )
        
        try:
            # Perform the import with test mode
            result = import_service.import_meetings_for_date(iso_date, test_mode)
            
            # Update log with success
            message = f"Successfully imported {result.get('total_meetings', 0)} meetings"
            if test_mode:
                message += " (TEST MODE)"
            
            log_service.update_log(
                log_id=log_id,
                status='completed',
                records_processed=result.get('total_meetings', 0),
                records_inserted=result.get('inserted', 0),
                records_updated=result.get('updated', 0),
                message=message
            )
            
            return jsonify({
                'success': True,
                'message': f"Import completed for {date_str}" + (" (TEST MODE)" if test_mode else ""),
                'data': result,
                'log_id': log_id,
                'test_mode': test_mode
            })
            
        except Exception as e:
            # Update log with error
            log_service.update_log(
                log_id=log_id,
                status='failed',
                error_message=str(e)
            )
            
            return jsonify({
                'success': False,
                'error': str(e),
                'log_id': log_id,
                'test_mode': test_mode
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Import failed: {str(e)}"
        }), 500

@meetings_bp.route('/import/meetings/status', methods=['GET'])
def get_import_status():
    """Get the status of the last import"""
    try:
        log_service = ImportLogService()
        last_log = log_service.get_last_import_status()
        
        if not last_log:
            return jsonify({
                'success': True,
                'data': {
                    'last_run': None,
                    'status': 'never_run'
                }
            })
        
        # Format dates in Australian format for display
        started_at_display = None
        completed_at_display = None
        target_date_display = None
        
        if last_log.get('started_at'):
            started_dt = datetime.fromisoformat(last_log['started_at'].replace('Z', '+00:00'))
            started_aest = started_dt.astimezone(AEST)
            started_at_display = started_aest.strftime('%d/%m/%Y %I:%M %p AEST')
        
        if last_log.get('completed_at'):
            completed_dt = datetime.fromisoformat(last_log['completed_at'].replace('Z', '+00:00'))
            completed_aest = completed_dt.astimezone(AEST)
            completed_at_display = completed_aest.strftime('%d/%m/%Y %I:%M %p AEST')
        
        if last_log.get('import_date'):
            target_dt = datetime.strptime(last_log['import_date'], '%Y-%m-%d')
            target_date_display = target_dt.strftime('%d/%m/%Y')
        
        return jsonify({
            'success': True,
            'data': {
                'id': last_log.get('id'),
                'status': last_log.get('status'),
                'trigger_type': last_log.get('trigger_type'),
                'started_at': started_at_display,
                'completed_at': completed_at_display,
                'target_date': target_date_display,
                'records_processed': last_log.get('records_processed', 0),
                'records_inserted': last_log.get('records_inserted', 0),
                'records_updated': last_log.get('records_updated', 0),
                'message': last_log.get('message'),
                'error_message': last_log.get('error_message')
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to get status: {str(e)}"
        }), 500

@meetings_bp.route('/import/meetings/logs', methods=['GET'])
def get_import_logs():
    """Get import history logs"""
    try:
        log_service = ImportLogService()
        logs = log_service.get_recent_logs(limit=20)
        
        # Format logs for display
        logs_data = []
        for log in logs:
            started_at_display = None
            completed_at_display = None
            target_date_display = None
            
            if log.get('started_at'):
                started_dt = datetime.fromisoformat(log['started_at'].replace('Z', '+00:00'))
                started_aest = started_dt.astimezone(AEST)
                started_at_display = started_aest.strftime('%d/%m/%Y %I:%M %p AEST')
            
            if log.get('completed_at'):
                completed_dt = datetime.fromisoformat(log['completed_at'].replace('Z', '+00:00'))
                completed_aest = completed_dt.astimezone(AEST)
                completed_at_display = completed_aest.strftime('%d/%m/%Y %I:%M %p AEST')
            
            if log.get('import_date'):
                target_dt = datetime.strptime(log['import_date'], '%Y-%m-%d')
                target_date_display = target_dt.strftime('%d/%m/%Y')
            
            logs_data.append({
                'id': log.get('id'),
                'status': log.get('status'),
                'trigger_type': log.get('trigger_type'),
                'started_at': started_at_display,
                'completed_at': completed_at_display,
                'target_date': target_date_display,
                'records_processed': log.get('records_processed', 0),
                'records_inserted': log.get('records_inserted', 0),
                'records_updated': log.get('records_updated', 0),
                'message': log.get('message'),
                'error_message': log.get('error_message')
            })
        
        return jsonify({
            'success': True,
            'data': {
                'logs': logs_data
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to get logs: {str(e)}"
        }), 500

@meetings_bp.route('/import/meetings/test', methods=['GET', 'POST'])
def test_api_connection():
    """Test API connectivity"""
    try:
        api_key = os.getenv('PUNTING_FORM_API_KEY')
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API key not configured'
            }), 500
        
        # Get date from request or use tomorrow as default
        date_str = None
        if request.method == 'POST':
            data = request.get_json() or {}
            date_str = data.get('date')
        else:
            date_str = request.args.get('date')
        
        if date_str:
            # Convert from Australian format DD/MM/YYYY to ISO format
            try:
                date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                test_date = date_obj.strftime('%Y-%m-%d')
                display_date = date_str
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid date format. Use DD/MM/YYYY format.'
                }), 400
        else:
            # Default to tomorrow
            tomorrow = datetime.now() + timedelta(days=1)
            test_date = tomorrow.strftime('%Y-%m-%d')
            display_date = tomorrow.strftime('%d/%m/%Y')
        
        url = "https://api.puntingform.com.au/v2/form/meetingslist"
        params = {
            "meetingDate": test_date,
            "apiKey": api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            meeting_count = len(data.get('Meetings', []))
            
            return jsonify({
                'success': True,
                'message': f'API connection successful. Found {meeting_count} meetings for {display_date}',
                'data': {
                    'status_code': response.status_code,
                    'meeting_count': meeting_count,
                    'test_date': display_date
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'API returned status {response.status_code}: {response.text}',
                'data': {
                    'status_code': response.status_code,
                    'response_text': response.text
                }
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"API test failed: {str(e)}"
        }), 500



@meetings_bp.route('/admin/clear-test-data', methods=['POST'])
def clear_test_data():
    """Clear only test data from meetings and import_logs tables"""
    try:
        from src.modules.imports.meetings.meetings_import_service import MeetingsImportService
        
        # Initialize the service (which has Supabase access)
        service = MeetingsImportService()
        
        # Get request parameters
        data = request.get_json() or {}
        clear_meetings = data.get('clear_meetings', True)
        clear_logs = data.get('clear_logs', True)
        
        results = {}
        
        # Clear test meetings only
        if clear_meetings:
            try:
                # Delete only test meetings (is_test_data = true)
                meetings_result = service.supabase.table('meetings').delete().eq('is_test_data', True).execute()
                results['meetings_cleared'] = len(meetings_result.data) if meetings_result.data else 0
            except Exception as e:
                results['meetings_error'] = str(e)
        
        # Clear test import logs only
        if clear_logs:
            try:
                # Delete only test import logs (import_mode = 'test')
                logs_result = service.supabase.table('import_logs').delete().eq('import_mode', 'test').execute()
                results['logs_cleared'] = len(logs_result.data) if logs_result.data else 0
            except Exception as e:
                results['logs_error'] = str(e)
        
        return jsonify({
            'success': True,
            'message': 'Test data cleared successfully (production data preserved)',
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to clear test data: {str(e)}"
        }), 500

