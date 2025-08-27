"""
Meeting Status Management Service

Handles archiving and status management for meetings
"""

import os
from datetime import datetime, date
from supabase import create_client, Client

class MeetingStatusService:
    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not configured")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def archive_old_meetings(self, cutoff_date=None):
        """
        Archive meetings older than cutoff_date
        
        Args:
            cutoff_date: Date to archive before (defaults to today)
            
        Returns:
            dict: Statistics about archived meetings
        """
        if cutoff_date is None:
            cutoff_date = date.today()
        
        # Convert to string format for database query
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        try:
            # Get meetings to archive first (for counting)
            meetings_to_archive = self.supabase.table('meetings').select('meeting_id, track_name, meeting_date').eq('status', 'active').lt('meeting_date', cutoff_str).execute()
            
            count_to_archive = len(meetings_to_archive.data) if meetings_to_archive.data else 0
            
            if count_to_archive == 0:
                return {
                    'success': True,
                    'archived_count': 0,
                    'message': f'No active meetings found before {cutoff_date}',
                    'cutoff_date': cutoff_str
                }
            
            # Archive the meetings
            archive_result = self.supabase.table('meetings').update({
                'status': 'archived',
                'archived_at': datetime.now().isoformat()
            }).eq('status', 'active').lt('meeting_date', cutoff_str).execute()
            
            archived_count = len(archive_result.data) if archive_result.data else 0
            
            return {
                'success': True,
                'archived_count': archived_count,
                'message': f'Successfully archived {archived_count} meetings before {cutoff_date}',
                'cutoff_date': cutoff_str,
                'archived_meetings': meetings_to_archive.data[:10]  # First 10 for logging
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'archived_count': 0,
                'cutoff_date': cutoff_str
            }
    
    def get_meeting_status_summary(self):
        """
        Get summary of meeting statuses
        
        Returns:
            dict: Status summary with counts
        """
        try:
            # Get active meetings count
            active_result = self.supabase.table('meetings').select('meeting_id', count='exact').eq('status', 'active').execute()
            active_count = active_result.count if active_result.count is not None else 0
            
            # Get archived meetings count
            archived_result = self.supabase.table('meetings').select('meeting_id', count='exact').eq('status', 'archived').execute()
            archived_count = archived_result.count if archived_result.count is not None else 0
            
            # Get total count
            total_result = self.supabase.table('meetings').select('meeting_id', count='exact').execute()
            total_count = total_result.count if total_result.count is not None else 0
            
            return {
                'success': True,
                'summary': {
                    'active_meetings': active_count,
                    'archived_meetings': archived_count,
                    'total_meetings': total_count
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'summary': {
                    'active_meetings': 0,
                    'archived_meetings': 0,
                    'total_meetings': 0
                }
            }
    
    def toggle_meeting_status(self, meeting_id, new_status):
        """
        Toggle a specific meeting's status
        
        Args:
            meeting_id: ID of the meeting to update
            new_status: 'active' or 'archived'
            
        Returns:
            dict: Result of the operation
        """
        if new_status not in ['active', 'archived']:
            return {
                'success': False,
                'error': 'Invalid status. Must be "active" or "archived"'
            }
        
        try:
            # Prepare update data
            update_data = {'status': new_status}
            
            if new_status == 'archived':
                update_data['archived_at'] = datetime.now().isoformat()
            else:
                update_data['archived_at'] = None
            
            # Update the meeting
            result = self.supabase.table('meetings').update(update_data).eq('meeting_id', meeting_id).execute()
            
            if result.data:
                return {
                    'success': True,
                    'message': f'Meeting {meeting_id} status updated to {new_status}',
                    'meeting': result.data[0]
                }
            else:
                return {
                    'success': False,
                    'error': f'Meeting {meeting_id} not found'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_meetings_by_status(self, status='active', limit=50, offset=0):
        """
        Get meetings filtered by status
        
        Args:
            status: 'active', 'archived', or 'all'
            limit: Number of meetings to return
            offset: Offset for pagination
            
        Returns:
            dict: Meetings data
        """
        try:
            query = self.supabase.table('meetings').select('*').order('meeting_date', desc=True)
            
            if status != 'all':
                query = query.eq('status', status)
            
            result = query.range(offset, offset + limit - 1).execute()
            
            return {
                'success': True,
                'meetings': result.data,
                'count': len(result.data) if result.data else 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'meetings': [],
                'count': 0
            }

