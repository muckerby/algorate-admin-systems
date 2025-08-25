from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import requests
import os
from src.shared.import_log import ImportLog, db
from src.modules.imports.meetings.meetings_import_service import MeetingsImportService

meetings_bp = Blueprint('meetings', __name__)

@meetings_bp.route('/import/meetings', methods=['POST'])
def import_meetings():
    """Manual trigger for meetings import"""
    try:
        # Get date from request or use tomorrow as default
        data = request.get_json() or {}
        date_str = data.get('date')
        
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
        
        # Initialize import service
        import_service = MeetingsImportService()
        
        # Start import log
        log = ImportLog(
            import_type='meetings',
            trigger_type='manual',
            status='running',
            started_at=datetime.now(),
            target_date=iso_date
        )
        db.session.add(log)
        db.session.commit()
        
        try:
            # Perform the import
            result = import_service.import_meetings_for_date(iso_date)
            
            # Update log with success
            log.status = 'completed'
            log.completed_at = datetime.now()
            log.records_processed = result.get('total_meetings', 0)
            log.records_inserted = result.get('inserted', 0)
            log.records_updated = result.get('updated', 0)
            log.message = f"Successfully imported {result.get('total_meetings', 0)} meetings"
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f"Import completed for {date_str}",
                'data': result,
                'log_id': log.id
            })
            
        except Exception as e:
            # Update log with error
            log.status = 'failed'
            log.completed_at = datetime.now()
            log.error_message = str(e)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': str(e),
                'log_id': log.id
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
        # Get the most recent import log
        last_log = ImportLog.query.filter_by(import_type='meetings').order_by(ImportLog.started_at.desc()).first()
        
        if not last_log:
            return jsonify({
                'success': True,
                'data': {
                    'last_run': None,
                    'status': 'never_run'
                }
            })
        
        # Format dates in Australian format for display
        started_at_display = last_log.started_at.strftime('%d/%m/%Y %I:%M %p AEST') if last_log.started_at else None
        completed_at_display = last_log.completed_at.strftime('%d/%m/%Y %I:%M %p AEST') if last_log.completed_at else None
        target_date_display = datetime.strptime(last_log.target_date, '%Y-%m-%d').strftime('%d/%m/%Y') if last_log.target_date else None
        
        return jsonify({
            'success': True,
            'data': {
                'id': last_log.id,
                'status': last_log.status,
                'trigger_type': last_log.trigger_type,
                'started_at': started_at_display,
                'completed_at': completed_at_display,
                'target_date': target_date_display,
                'records_processed': last_log.records_processed,
                'records_inserted': last_log.records_inserted,
                'records_updated': last_log.records_updated,
                'message': last_log.message,
                'error_message': last_log.error_message
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
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Query logs with pagination
        logs_query = ImportLog.query.filter_by(import_type='meetings').order_by(ImportLog.started_at.desc())
        logs_paginated = logs_query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format logs for display
        logs_data = []
        for log in logs_paginated.items:
            started_at_display = log.started_at.strftime('%d/%m/%Y %I:%M %p AEST') if log.started_at else None
            completed_at_display = log.completed_at.strftime('%d/%m/%Y %I:%M %p AEST') if log.completed_at else None
            target_date_display = datetime.strptime(log.target_date, '%Y-%m-%d').strftime('%d/%m/%Y') if log.target_date else None
            
            logs_data.append({
                'id': log.id,
                'status': log.status,
                'trigger_type': log.trigger_type,
                'started_at': started_at_display,
                'completed_at': completed_at_display,
                'target_date': target_date_display,
                'records_processed': log.records_processed,
                'records_inserted': log.records_inserted,
                'records_updated': log.records_updated,
                'message': log.message,
                'error_message': log.error_message
            })
        
        return jsonify({
            'success': True,
            'data': {
                'logs': logs_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': logs_paginated.total,
                    'pages': logs_paginated.pages,
                    'has_next': logs_paginated.has_next,
                    'has_prev': logs_paginated.has_prev
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Failed to get logs: {str(e)}"
        }), 500

@meetings_bp.route('/import/meetings/test', methods=['GET'])
def test_api_connection():
    """Test API connectivity"""
    try:
        api_key = os.getenv('PUNTING_FORM_API_KEY')
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API key not configured'
            }), 500
        
        # Test with tomorrow's date
        tomorrow = datetime.now() + timedelta(days=1)
        test_date = tomorrow.strftime('%Y-%m-%d')
        
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
                'message': f'API connection successful. Found {meeting_count} meetings for {tomorrow.strftime("%d/%m/%Y")}',
                'data': {
                    'status_code': response.status_code,
                    'meeting_count': meeting_count,
                    'test_date': tomorrow.strftime('%d/%m/%Y')
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

