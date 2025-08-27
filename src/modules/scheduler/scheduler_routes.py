from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from croniter import croniter
import json
from .task_scheduler import scheduler
from ...modules.auth.auth import require_auth
import os
from supabase import create_client, Client

scheduler_bp = Blueprint('scheduler', __name__)

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

@scheduler_bp.route('/api/scheduler/tasks', methods=['GET'])
@require_auth
def get_scheduled_tasks():
    """Get all scheduled tasks"""
    try:
        result = supabase.table('scheduled_tasks').select('*').order('created_at', desc=True).execute()
        
        # Format tasks for frontend
        tasks = []
        for task in result.data:
            formatted_task = {
                'task_id': task['task_id'],
                'task_name': task['task_name'],
                'task_type': task['task_type'],
                'description': task['description'],
                'schedule_type': task['schedule_type'],
                'cron_expression': task.get('cron_expression'),
                'interval_minutes': task.get('interval_minutes'),
                'scheduled_time': task.get('scheduled_time'),
                'is_active': task['is_active'],
                'is_running': task['is_running'],
                'last_run_at': task.get('last_run_at'),
                'last_run_status': task.get('last_run_status'),
                'last_run_message': task.get('last_run_message'),
                'next_run_at': task.get('next_run_at'),
                'total_runs': task.get('total_runs', 0),
                'successful_runs': task.get('successful_runs', 0),
                'failed_runs': task.get('failed_runs', 0),
                'created_at': task['created_at']
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

@scheduler_bp.route('/api/scheduler/tasks', methods=['POST'])
@require_auth
def create_scheduled_task():
    """Create a new scheduled task"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['task_name', 'task_type', 'schedule_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate schedule configuration
        schedule_type = data['schedule_type']
        if schedule_type == 'cron' and not data.get('cron_expression'):
            return jsonify({
                'success': False,
                'error': 'Cron expression required for cron schedule type'
            }), 400
        elif schedule_type == 'interval' and not data.get('interval_minutes'):
            return jsonify({
                'success': False,
                'error': 'Interval minutes required for interval schedule type'
            }), 400
        elif schedule_type == 'one_time' and not data.get('scheduled_time'):
            return jsonify({
                'success': False,
                'error': 'Scheduled time required for one-time schedule type'
            }), 400
        
        # Validate cron expression if provided
        if data.get('cron_expression'):
            try:
                croniter(data['cron_expression'])
            except Exception:
                return jsonify({
                    'success': False,
                    'error': 'Invalid cron expression'
                }), 400
        
        # Prepare task data
        task_data = {
            'task_name': data['task_name'],
            'task_type': data['task_type'],
            'description': data.get('description', ''),
            'schedule_type': schedule_type,
            'task_config': json.dumps(data.get('task_config', {})),
            'is_active': data.get('is_active', True)
        }
        
        # Add schedule-specific fields
        if schedule_type == 'cron':
            task_data['cron_expression'] = data['cron_expression']
        elif schedule_type == 'interval':
            task_data['interval_minutes'] = data['interval_minutes']
        elif schedule_type == 'one_time':
            task_data['scheduled_time'] = data['scheduled_time']
        
        # Calculate next run time
        if schedule_type == 'cron' and data.get('cron_expression'):
            try:
                cron = croniter(data['cron_expression'], datetime.now())
                task_data['next_run_at'] = cron.get_next(datetime).isoformat()
            except:
                pass
        elif schedule_type == 'interval' and data.get('interval_minutes'):
            next_run = datetime.now() + timedelta(minutes=data['interval_minutes'])
            task_data['next_run_at'] = next_run.isoformat()
        elif schedule_type == 'one_time' and data.get('scheduled_time'):
            task_data['next_run_at'] = data['scheduled_time']
        
        # Insert task
        result = supabase.table('scheduled_tasks').insert(task_data).execute()
        
        return jsonify({
            'success': True,
            'task': result.data[0] if result.data else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scheduler_bp.route('/api/scheduler/tasks/<task_id>', methods=['PUT'])
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
            result = supabase.table('scheduled_tasks').update(update_data).eq('task_id', task_id).execute()
            
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

@scheduler_bp.route('/api/scheduler/tasks/<task_id>', methods=['DELETE'])
@require_auth
def delete_scheduled_task(task_id):
    """Delete a scheduled task"""
    try:
        result = supabase.table('scheduled_tasks').delete().eq('task_id', task_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'Task deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scheduler_bp.route('/api/scheduler/tasks/<task_id>/run', methods=['POST'])
@require_auth
def run_task_now(task_id):
    """Manually trigger a scheduled task"""
    try:
        # Get task details
        result = supabase.table('scheduled_tasks').select('*').eq('task_id', task_id).execute()
        
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
        thread = threading.Thread(target=scheduler._execute_task, args=(task,), daemon=True)
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

@scheduler_bp.route('/api/scheduler/status', methods=['GET'])
@require_auth
def get_scheduler_status():
    """Get scheduler status"""
    try:
        return jsonify({
            'success': True,
            'status': {
                'running': scheduler.running,
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
    schedule_type = task['schedule_type']
    
    if schedule_type == 'cron':
        cron_expr = task.get('cron_expression', '')
        if cron_expr == '0 6 * * *':
            return 'Daily at 6:00 AM'
        elif cron_expr == '0 */6 * * *':
            return 'Every 6 hours'
        elif cron_expr == '0 0 * * 0':
            return 'Weekly on Sunday at midnight'
        else:
            return f'Cron: {cron_expr}'
    elif schedule_type == 'interval':
        minutes = task.get('interval_minutes', 0)
        if minutes < 60:
            return f'Every {minutes} minutes'
        elif minutes == 60:
            return 'Every hour'
        elif minutes % 60 == 0:
            hours = minutes // 60
            return f'Every {hours} hours'
        else:
            return f'Every {minutes} minutes'
    elif schedule_type == 'one_time':
        scheduled_time = task.get('scheduled_time')
        if scheduled_time:
            try:
                dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                return f'Once at {dt.strftime("%Y-%m-%d %H:%M")}'
            except:
                return 'One-time execution'
        return 'One-time execution'
    
    return 'Unknown schedule'

def _get_active_tasks_count():
    """Get count of active tasks"""
    try:
        result = supabase.table('scheduled_tasks').select('task_id', count='exact').eq('is_active', True).execute()
        return result.count or 0
    except:
        return 0

def _get_running_tasks_count():
    """Get count of currently running tasks"""
    try:
        result = supabase.table('scheduled_tasks').select('task_id', count='exact').eq('is_running', True).execute()
        return result.count or 0
    except:
        return 0

