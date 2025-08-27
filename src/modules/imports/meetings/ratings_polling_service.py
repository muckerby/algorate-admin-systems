"""
Ratings Update Polling Service
Monitors Punting Form API for ratings updates and triggers refreshes
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from supabase import create_client, Client

class RatingsPollingService:
    """Service for monitoring and polling ratings updates"""
    
    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            raise Exception("Supabase credentials not configured")
        
        self.supabase = create_client(supabase_url, supabase_key)
        self.api_base_url = "https://api.puntingform.com.au/v2"
        self.api_key = os.getenv('PUNTING_FORM_API_KEY')
        
        if not self.api_key:
            raise Exception("PUNTING_FORM_API_KEY not configured")
    
    def check_ratings_updates(self, days_back: int = 7) -> Dict:
        """
        Check for ratings updates in recent meetings
        Returns summary of meetings with updated ratings
        """
        try:
            # Get recent meetings from database
            cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            db_meetings = self.supabase.table('meetings').select(
                'pf_meeting_id, meeting_date, ratings_updated, track_name'
            ).gte('meeting_date', cutoff_date).eq('status', 'active').execute()
            
            if not db_meetings.data:
                return {
                    'total_checked': 0,
                    'updates_found': 0,
                    'meetings_to_update': [],
                    'message': 'No recent meetings found'
                }
            
            updates_found = []
            total_checked = len(db_meetings.data)
            
            # Check each meeting for ratings updates
            for meeting in db_meetings.data:
                pf_meeting_id = meeting['pf_meeting_id']
                current_ratings_updated = meeting.get('ratings_updated')
                meeting_date = meeting['meeting_date']
                
                # Fetch current ratings timestamp from API
                api_ratings_updated = self._get_api_ratings_timestamp(pf_meeting_id, meeting_date)
                
                if api_ratings_updated and self._is_ratings_newer(api_ratings_updated, current_ratings_updated):
                    updates_found.append({
                        'pf_meeting_id': pf_meeting_id,
                        'track_name': meeting['track_name'],
                        'meeting_date': meeting_date,
                        'current_ratings_updated': current_ratings_updated,
                        'api_ratings_updated': api_ratings_updated
                    })
            
            return {
                'total_checked': total_checked,
                'updates_found': len(updates_found),
                'meetings_to_update': updates_found,
                'message': f'Found {len(updates_found)} meetings with updated ratings out of {total_checked} checked'
            }
            
        except Exception as e:
            raise Exception(f"Ratings polling failed: {str(e)}")
    
    def _get_api_ratings_timestamp(self, pf_meeting_id: str, meeting_date: str) -> Optional[str]:
        """Get ratings timestamp from API for a specific meeting"""
        try:
            url = f"{self.api_base_url}/form/meetingslist"
            params = {
                "meetingDate": meeting_date,
                "apiKey": self.api_key
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"⚠️ API request failed for {meeting_date}: {response.status_code}")
                return None
            
            meetings_data = response.json()
            
            # Find the specific meeting
            for meeting in meetings_data:
                if str(meeting.get('meetingId', '')) == str(pf_meeting_id):
                    # Try multiple possible field names for ratings timestamp
                    ratings_updated = (
                        meeting.get('ratingsUpdated') or
                        meeting.get('ratings_updated') or
                        meeting.get('RatingsUpdated')
                    )
                    return ratings_updated
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error fetching API ratings for meeting {pf_meeting_id}: {str(e)}")
            return None
    
    def _is_ratings_newer(self, api_timestamp: str, db_timestamp: Optional[str]) -> bool:
        """Check if API ratings timestamp is newer than database timestamp"""
        if not api_timestamp:
            return False
        
        if not db_timestamp:
            return True  # API has timestamp, DB doesn't
        
        try:
            # Parse timestamps (handle various formats)
            api_dt = self._parse_timestamp(api_timestamp)
            db_dt = self._parse_timestamp(db_timestamp)
            
            if api_dt and db_dt:
                return api_dt > db_dt
            
            return False
            
        except Exception as e:
            print(f"⚠️ Error comparing timestamps: {str(e)}")
            return False
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return None
        
        # Try common timestamp formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def trigger_ratings_refresh(self, meetings_to_update: List[Dict]) -> Dict:
        """
        Trigger refresh for meetings with updated ratings
        This could re-import specific meetings or update ratings data
        """
        try:
            from src.modules.imports.meetings.meetings_import_service import MeetingsImportService
            
            import_service = MeetingsImportService()
            results = {
                'total_meetings': len(meetings_to_update),
                'successful_updates': 0,
                'failed_updates': 0,
                'errors': []
            }
            
            for meeting in meetings_to_update:
                try:
                    meeting_date = meeting['meeting_date']
                    pf_meeting_id = meeting['pf_meeting_id']
                    
                    # Re-import the specific meeting date to get updated ratings
                    result = import_service.import_meetings_for_date(meeting_date, test_mode=False)
                    
                    if result.get('total_meetings', 0) > 0:
                        results['successful_updates'] += 1
                        print(f"✅ Updated ratings for meeting {pf_meeting_id} on {meeting_date}")
                    else:
                        results['failed_updates'] += 1
                        results['errors'].append(f"No data returned for meeting {pf_meeting_id}")
                        
                except Exception as e:
                    results['failed_updates'] += 1
                    results['errors'].append(f"Failed to update meeting {meeting.get('pf_meeting_id', 'unknown')}: {str(e)}")
            
            return results
            
        except Exception as e:
            raise Exception(f"Ratings refresh failed: {str(e)}")
    
    def run_ratings_polling_cycle(self, days_back: int = 7, auto_refresh: bool = True) -> Dict:
        """
        Run a complete ratings polling cycle
        Check for updates and optionally trigger refreshes
        """
        try:
            print(f"🔍 Starting ratings polling cycle (checking {days_back} days back)")
            
            # Check for updates
            check_result = self.check_ratings_updates(days_back)
            
            result = {
                'polling_completed': True,
                'check_result': check_result,
                'refresh_result': None,
                'summary': check_result['message']
            }
            
            # If updates found and auto-refresh enabled, trigger refresh
            if auto_refresh and check_result['updates_found'] > 0:
                print(f"🔄 Auto-refreshing {check_result['updates_found']} meetings with updated ratings")
                
                refresh_result = self.trigger_ratings_refresh(check_result['meetings_to_update'])
                result['refresh_result'] = refresh_result
                
                result['summary'] = (
                    f"Polling complete: {check_result['updates_found']} updates found, "
                    f"{refresh_result['successful_updates']} successfully refreshed"
                )
            
            return result
            
        except Exception as e:
            return {
                'polling_completed': False,
                'error': str(e),
                'summary': f"Ratings polling failed: {str(e)}"
            }

