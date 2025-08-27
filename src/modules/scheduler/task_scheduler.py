import os
import json
import threading
import time
from datetime import datetime, timedelta
from croniter import croniter
from supabase import create_client, Client
from ..imports.meetings.meetings_import_service import MeetingsImportService
from ...shared.import_log import ImportLogService

class TaskScheduler:
    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not configured")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.running = False
        self.scheduler_thread = None
        
        # Initialize services
        self.meetings_service = MeetingsImportService()
        self.import_log_service = ImportLogService()
    
    def start(self):
        """Start the task scheduler"""
        if self.running:
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        print("Task scheduler started")
    
    def stop(self):
        """Stop the task scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        print("Task scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                self._check_and_execute_tasks()
                time.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Scheduler error: {str(e)}")
                time.sleep(60)
    
    def _check_and_execute_tasks(self):
        """Check for tasks that need to be executed"""
        now = datetime.now()
        
        # Get active tasks that are due to run
        result = self.supabase.table('scheduled_tasks').select('*').eq('is_active', True).eq('is_running', False).execute()
        
        if not result.data:
            return
        
        for task in result.data:
            if self._is_task_due(task, now):
                self._execute_task(task)
    
    def _is_task_due(self, task, now):
        """Check if a task is due to run"""
        schedule_type = task.get('schedule_type')
        
        if schedule_type == 'cron':
            return self._is_cron_due(task, now)
        elif schedule_type == 'interval':
            return self._is_interval_due(task, now)
        elif schedule_type == 'one_time':
            return self._is_one_time_due(task, now)
        
        return False
    
    def _is_cron_due(self, task, now):
        """Check if cron task is due"""
        cron_expression = task.get('cron_expression')
        if not cron_expression:
            return False
        
        try:
            cron = croniter(cron_expression, now)
            next_run = cron.get_prev(datetime)
            last_run = task.get('last_run_at')
            
            if not last_run:
                return True
            
            last_run_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
            return next_run > last_run_dt
        except Exception as e:
            print(f"Error checking cron schedule for task {task['task_id']}: {str(e)}")
            return False
    
    def _is_interval_due(self, task, now):
        """Check if interval task is due"""
        interval_minutes = task.get('interval_minutes')
        if not interval_minutes:
            return False
        
        last_run = task.get('last_run_at')
        if not last_run:
            return True
        
        last_run_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
        next_run = last_run_dt + timedelta(minutes=interval_minutes)
        return now >= next_run
    
    def _is_one_time_due(self, task, now):
        """Check if one-time task is due"""
        scheduled_time = task.get('scheduled_time')
        if not scheduled_time:
            return False
        
        scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
        return now >= scheduled_dt and not task.get('last_run_at')
    
    def _execute_task(self, task):
        """Execute a scheduled task"""
        task_id = task['task_id']
        task_type = task['task_type']
        
        try:
            # Mark task as running
            self.supabase.table('scheduled_tasks').update({
                'is_running': True,
                'last_run_at': datetime.now().isoformat()
            }).eq('task_id', task_id).execute()
            
            # Execute based on task type
            if task_type == 'meetings_import':
                self._execute_meetings_import(task)
            elif task_type == 'ratings_check':
                self._execute_ratings_check(task)
            else:
                raise Exception(f"Unknown task type: {task_type}")
            
            # Mark task as completed successfully
            self._update_task_completion(task_id, 'success', 'Task completed successfully')
            
        except Exception as e:
            error_message = str(e)
            print(f"Task execution failed for {task_id}: {error_message}")
            self._update_task_completion(task_id, 'failed', error_message)
    
    def _execute_meetings_import(self, task):
        """Execute meetings import task with automatic archiving"""
        task_config = task.get('task_config', {})
        
        # Determine import date
        if task_config.get('auto_date', True):
            # Import tomorrow's meetings (common for racing data)
            import_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            import_date = task_config.get('import_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Create import log
        log_id = self.import_log_service.create_log(
            import_type='meetings',
            trigger_type='scheduled',
            import_date=import_date
        )
        
        try:
            # First, archive old meetings (enabled by default)
            archive_count = 0
            if task_config.get('archive_old_meetings', True):
                archive_count = self._archive_old_meetings()
            
            # Execute import
            result = self.meetings_service.import_meetings_for_date(import_date)
            
            # Update import log with combined results
            message = result.get('message', '')
            if archive_count > 0:
                message += f" | Archived {archive_count} old meetings"
            
            self.import_log_service.update_log(
                log_id=log_id,
                status='completed',
                records_processed=result.get('total_meetings', 0),
                records_inserted=result.get('inserted', 0),
                records_updated=result.get('updated', 0),
                message=message
            )
            
        except Exception as e:
            # Update import log with error
            self.import_log_service.update_log(
                log_id=log_id,
                status='failed',
                error_message=str(e)
            )
            raise
    
    def _archive_old_meetings(self):
        """Archive meetings older than today"""
        try:
            from ..imports.meetings.meeting_status_service import MeetingStatusService
            
            status_service = MeetingStatusService()
            result = status_service.archive_old_meetings()
            
            if result['success']:
                return result['archived_count']
            else:
                print(f"Failed to archive old meetings: {result['error']}")
                return 0
                
        except Exception as e:
            print(f"Error archiving old meetings: {e}")
            return 0
    
    def _execute_ratings_check(self, task):
        """Execute ratings update polling task"""
        task_config = task.get('task_config', {})
        
        try:
            from ..imports.meetings.ratings_polling_service import RatingsPollingService
            
            polling_service = RatingsPollingService()
            
            # Get configuration
            days_back = task_config.get('days_back', 7)
            auto_refresh = task_config.get('auto_refresh', True)
            
            # Run polling cycle
            result = polling_service.run_ratings_polling_cycle(days_back, auto_refresh)
            
            if result.get('polling_completed'):
                print(f"✅ Ratings polling completed: {result.get('summary')}")
            else:
                print(f"❌ Ratings polling failed: {result.get('summary')}")
                raise Exception(result.get('error', 'Ratings polling failed'))
                
        except Exception as e:
            print(f"Error in ratings polling: {e}")
            raise
    
    def _update_task_completion(self, task_id, status, message):
        """Update task completion status"""
        update_data = {
            'is_running': False,
            'last_run_status': status,
            'last_run_message': message,
            'total_runs': self.supabase.rpc('increment_total_runs', {'task_id': task_id}).execute()
        }
        
        if status == 'success':
            update_data['successful_runs'] = self.supabase.rpc('increment_successful_runs', {'task_id': task_id}).execute()
        else:
            update_data['failed_runs'] = self.supabase.rpc('increment_failed_runs', {'task_id': task_id}).execute()
        
        # Calculate next run time for recurring tasks
        task_result = self.supabase.table('scheduled_tasks').select('*').eq('task_id', task_id).execute()
        if task_result.data:
            task = task_result.data[0]
            next_run = self._calculate_next_run(task)
            if next_run:
                update_data['next_run_at'] = next_run.isoformat()
        
        self.supabase.table('scheduled_tasks').update(update_data).eq('task_id', task_id).execute()
    
    def _calculate_next_run(self, task):
        """Calculate next run time for a task"""
        schedule_type = task.get('schedule_type')
        
        if schedule_type == 'cron':
            cron_expression = task.get('cron_expression')
            if cron_expression:
                try:
                    cron = croniter(cron_expression, datetime.now())
                    return cron.get_next(datetime)
                except:
                    return None
        elif schedule_type == 'interval':
            interval_minutes = task.get('interval_minutes')
            if interval_minutes:
                return datetime.now() + timedelta(minutes=interval_minutes)
        
        return None

# Global scheduler instance - initialized lazily
scheduler = None

def get_scheduler():
    """Get or create the global scheduler instance"""
    global scheduler
    if scheduler is None:
        scheduler = TaskScheduler()
    return scheduler

def start_scheduler():
    """Start the global scheduler"""
    try:
        get_scheduler().start()
    except Exception as e:
        print(f"Failed to start scheduler: {e}")

def stop_scheduler():
    """Stop the global scheduler"""
    if scheduler is not None:
        scheduler.stop()

