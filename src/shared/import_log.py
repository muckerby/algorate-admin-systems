import os
from datetime import datetime
from supabase import create_client, Client

class ImportLogService:
    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not configured")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def create_log(self, import_type, trigger_type, import_date=None):
        """Create a new import log entry"""
        log_data = {
            'import_type': import_type,
            'trigger_type': trigger_type,
            'status': 'running',
            'started_at': datetime.now().isoformat(),
            'import_date': import_date,
            'records_processed': 0,
            'records_inserted': 0,
            'records_updated': 0,
            'created_at': datetime.now().isoformat()
        }
        
        result = self.supabase.table('import_logs').insert(log_data).execute()
        return result.data[0]['id'] if result.data else None
    
    def update_log(self, log_id, status=None, records_processed=0, records_inserted=0, 
                   records_updated=0, message=None, error_message=None):
        """Update an existing import log"""
        update_data = {
            'records_processed': records_processed,
            'records_inserted': records_inserted,
            'records_updated': records_updated
        }
        
        if status:
            update_data['status'] = status
            if status in ['completed', 'failed']:
                update_data['completed_at'] = datetime.now().isoformat()
        
        if message:
            update_data['message'] = message
        
        if error_message:
            update_data['error_message'] = error_message
        
        result = self.supabase.table('import_logs').update(update_data).eq('id', log_id).execute()
        return result.data[0] if result.data else None
    
    def get_recent_logs(self, limit=10):
        """Get recent import logs"""
        result = self.supabase.table('import_logs').select('*').order('created_at', desc=True).limit(limit).execute()
        return result.data if result.data else []
    
    def get_last_import_status(self):
        """Get the status of the last import"""
        result = self.supabase.table('import_logs').select('*').order('created_at', desc=True).limit(1).execute()
        return result.data[0] if result.data else None

