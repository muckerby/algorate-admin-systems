from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from croniter import croniter
import json
from .task_scheduler import get_scheduler
from ...modules.auth.auth import require_auth
import os
from supabase import create_client, Client

scheduler_bp = Blueprint('scheduler', __name__)

# Initialize Supabase client lazily
def get_supabase_client():
    """Get Supabase client with lazy initialization"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase credentials not configured")
    
    return create_client(supabase_url, supabase_key)

@scheduler_bp.route('/scheduler/tasks', methods=['GET'])
@require_auth
def get_scheduled_tasks():
    """Get all scheduled tasks"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('scheduled_tasks').select('*').order('created_at', desc=True).execute()
        
        # Format tasks for frontend
        tasks = []
        for task in result.data:
            formatted_task = {
                'id': task['id'],
                'task_name': task['task_name'],
                'task_type': task['task_type'],
                'cron_schedule': task.get('cron_schedule'),
                'config': task.get('config', {}),
                'is_active': task['is_active'],
                'last_run_at': task.get('last_run_at'),
                'last_run_status': task.get('last_run_status'),
                'last_run_log': task.get('last_run_log'),
                'next_run_at': task.get('next_run_at'),
                'created_at': task['created_at'],
                'updated_at': task['updated_at']
            }
            
            # Add human-readable schedule description
            formatted_task['schedule_description'] = _get_schedule_description(task)
            
            tasks.append(formatted_task)
        
        return jsonify({
            'success': True,
            'tasks': tasks
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scheduler_bp.route('/scheduler/tasks', methods=['POST'])
@require_auth
def create_scheduled_task():
    """Create a new scheduled task"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['task_name', 'task_type', 'cron_schedule']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate cron expression if provided
        if data.get('cron_schedule'):
            try:
                croniter(data['cron_schedule'])
            except Exception:
                return jsonify({
                    'success': False,
                    'error': 'Invalid cron expression'
                }), 400
        
        # Prepare task data
        task_data = {
            'task_name': data['task_name'],
            'task_type': data['task_type'],
            'cron_schedule': data['cron_schedule'],
            'config': data.get('config', {}),
            'is_active': data.get('is_active', True)
        }
        
        # Calculate next run time
        if data.get('cron_schedule'):
            try:
                cron = croniter(data['cron_schedule'], datetime.now())
                task_data['next_run_at'] = cron.get_next(datetime).isoformat()
            except:
                pass
        
        # Insert task
        supabase = get_supabase_client()
        result = supabase.table('scheduled_tasks').insert(task_data).execute()
        
        # Reload scheduler tasks
        scheduler = get_scheduler()
        if scheduler:
            scheduler.load_tasks_from_db()
        
        return jsonify({
            'success': True,
            'task': result.data[0] if result.data else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scheduler_bp.route('/scheduler/tasks/<task_id>', methods=['PUT'])
@require_auth
def update_scheduled_task(task_id):
    """Update a scheduled task"""
    try:
        data = request.get_json()
        
        # Prepare update data
        update_data = {}
        
        # Update allowed fields
        allowed_fields = ['task_name', 'description', 'is_active', 'task_config']
        for field in allowed_fields:
            if field in data:
                if field == 'task_config':
                    update_data[field] = json.dumps(data[field])
                else:
                    update_data[field] = data[field]
        
        # Update schedule configuration if provided
        if 'schedule_type' in data:
            update_data['schedule_type'] = data['schedule_type']
            
            if data['schedule_type'] == 'cron' and 'cron_expression' in data:
                try:
                    croniter(data['cron_expression'])
                    update_data['cron_expression'] = data['cron_expression']
                    update_data['interval_minutes'] = None
                    update_data['scheduled_time'] = None
                except Exception:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid cron expression'
                    }), 400
            elif data['schedule_type'] == 'interval' and 'interval_minutes' in data:
                update_data['interval_minutes'] = data['interval_minutes']
                update_data['cron_expression'] = None
                update_data['scheduled_time'] = None
            elif data['schedule_type'] == 'one_time' and 'scheduled_time' in data:
                update_data['scheduled_time'] = data['scheduled_time']
                update_data['cron_expression'] = None
                update_data['interval_minutes'] = None
        
        if update_data:
            update_data['updated_at'] = datetime.now().isoformat()
            result = get_supabase_client().table('scheduled_tasks').update(update_data).eq('task_id', task_id).execute()
            
            return jsonify({
                'success': True,
                'task': result.data[0] if result.data else None
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No valid fields to update'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scheduler_bp.route('/scheduler/tasks/<task_id>', methods=['DELETE'])
@require_auth
def delete_scheduled_task(task_id):
    """Delete a scheduled task"""
    try:
        result = get_supabase_client().table('scheduled_tasks').delete().eq('task_id', task_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'Task deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scheduler_bp.route('/scheduler/tasks/<task_id>/run', methods=['POST'])
@require_auth
def run_task_now(task_id):
    """Manually trigger a scheduled task"""
    try:
        # Get task details
        result = get_supabase_client().table('scheduled_tasks').select('*').eq('task_id', task_id).execute()
        
        if not result.data:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        task = result.data[0]
        
        if task['is_running']:
            return jsonify({
                'success': False,
                'error': 'Task is already running'
            }), 400
        
        # Execute task in background
        import threading
        thread = threading.Thread(target=get_scheduler()._execute_task, args=(task,), daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Task execution started'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scheduler_bp.route('/scheduler/status', methods=['GET'])
@require_auth
def get_scheduler_status():
    """Get scheduler status"""
    try:
        return jsonify({
            'success': True,
            'status': {
                'running': get_scheduler().running,
                'active_tasks_count': _get_active_tasks_count(),
                'running_tasks_count': _get_running_tasks_count()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def _get_schedule_description(task):
    """Get human-readable schedule description"""
    cron_schedule = task.get('cron_schedule', '')
    
    if cron_schedule == '0 0 6 * * *':
        return 'Daily at 6:00 AM'
    elif cron_schedule == '0 0 * * * *':
        return 'Every hour'
    elif cron_schedule == '0 */6 * * * *':
        return 'Every 6 hours'
    elif cron_schedule == '0 0 0 * * 0':
        return 'Weekly on Sunday at midnight'
    else:
        return f'Cron: {cron_schedule}'

def _get_active_tasks_count():
    """Get count of active tasks"""
    try:
        result = get_supabase_client().table('scheduled_tasks').select('task_id', count='exact').eq('is_active', True).execute()
        return result.count or 0
    except:
        return 0

def _get_running_tasks_count():
    """Get count of currently running tasks"""
    try:
        result = get_supabase_client().table('scheduled_tasks').select('task_id', count='exact').eq('is_running', True).execute()
        return result.count or 0
    except:
        return 0

