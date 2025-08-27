import requests
import os
from datetime import datetime
from supabase import create_client, Client

class MeetingsImportService:
    def __init__(self):
        self.api_base_url = "https://api.puntingform.com.au/v2"
        self.api_key = os.getenv('PUNTING_FORM_API_KEY')
        
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not configured")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        if not self.api_key:
            raise ValueError("Punting Form API key not configured")
    
    def import_meetings_for_date(self, date_str):
        """
        Import meetings for a specific date (ISO format YYYY-MM-DD)
        Returns dict with import statistics
        """
        try:
            # Fetch meetings from API
            meetings_data = self._fetch_meetings_from_api(date_str)
            
            if not meetings_data or 'payLoad' not in meetings_data:
                return {
                    'total_meetings': 0,
                    'inserted': 0,
                    'updated': 0,
                    'errors': 0,
                    'message': 'No meetings found for this date'
                }
            
            meetings = meetings_data['payLoad']
            total_meetings = len(meetings)
            inserted = 0
            updated = 0
            errors = 0
            
            # Process each meeting
            for meeting in meetings:
                try:
                    result = self._process_meeting(meeting, date_str)
                    if result == 'inserted':
                        inserted += 1
                    elif result == 'updated':
                        updated += 1
                except Exception as e:
                    errors += 1
                    print(f"Error processing meeting {meeting.get('MeetingId', 'unknown')}: {str(e)}")
            
            return {
                'total_meetings': total_meetings,
                'inserted': inserted,
                'updated': updated,
                'errors': errors,
                'message': f'Processed {total_meetings} meetings: {inserted} inserted, {updated} updated, {errors} errors'
            }
            
        except Exception as e:
            raise Exception(f"Import failed: {str(e)}")
    
    def _fetch_meetings_from_api(self, date_str):
        """Fetch meetings data from Punting Form API"""
        url = f"{self.api_base_url}/form/meetingslist"
        params = {
            "meetingDate": date_str,
            "apiKey": self.api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")
        
        return response.json()
    
    def _process_meeting(self, meeting_data, date_str):
        """
        Process a single meeting and insert/update in database
        Returns 'inserted' or 'updated'
        """
        # Extract meeting data with correct field names
        pf_meeting_id = str(meeting_data.get('meetingId', ''))
        
        # Track data is nested in 'track' object
        track_data = meeting_data.get('track', {})
        track_name = track_data.get('name', '')
        track_id = str(track_data.get('trackId', ''))
        track_state = track_data.get('state', '')
        track_location = track_data.get('location', '')
        track_abbreviation = track_data.get('abbrev', '')
        
        stage = meeting_data.get('stage', 'A')
        tab_meeting = meeting_data.get('tabMeeting', True)
        rail_position = meeting_data.get('railPosition', '')
        expected_condition = meeting_data.get('expectedCondition', '')
        is_barrier_trial = meeting_data.get('isBarrierTrial', False)
        is_jumps = meeting_data.get('isJumps', False)
        has_sectionals = meeting_data.get('hasSectionals', False)
        
        # Extract timestamp fields from API
        form_updated = meeting_data.get('formUpdated', '')
        results_updated = meeting_data.get('resultsUpdated', '')
        sectionals_updated = meeting_data.get('sectionalsUpdated', '')
        ratings_updated = meeting_data.get('ratingsUpdated', '')
        
        # Prepare meeting record
        meeting_record = {
            'pf_meeting_id': pf_meeting_id,
            'track_name': track_name,
            'track_id': track_id,
            'track_state': track_state,
            'track_country': 'Australia',  # Default for now
            'track_location': track_location,
            'track_abbreviation': track_abbreviation,
            'meeting_date': date_str,
            'stage': stage,
            'tab_meeting': tab_meeting,
            'rail_position': rail_position,
            'expected_condition': expected_condition,
            'is_barrier_trial': is_barrier_trial,
            'is_jumps': is_jumps,
            'has_sectionals': has_sectionals,
            'form_updated': form_updated,
            'results_updated': results_updated,
            'sectionals_updated': sectionals_updated,
            'ratings_updated': ratings_updated,
            'status': 'active',  # New meetings are active by default
            'updated_at': datetime.now().isoformat()
        }
        
        # Check if meeting already exists
        existing = self.supabase.table('meetings').select('meeting_id').eq('pf_meeting_id', pf_meeting_id).execute()
        
        if existing.data:
            # Update existing meeting
            result = self.supabase.table('meetings').update(meeting_record).eq('pf_meeting_id', pf_meeting_id).execute()
            return 'updated'
        else:
            # Insert new meeting
            meeting_record['created_at'] = datetime.now().isoformat()
            result = self.supabase.table('meetings').insert(meeting_record).execute()
            return 'inserted'
    
    def test_api_connection(self):
        """Test API connectivity"""
        try:
            from datetime import timedelta
            tomorrow = datetime.now() + timedelta(days=1)
            test_date = tomorrow.strftime('%Y-%m-%d')
            
            data = self._fetch_meetings_from_api(test_date)
            meeting_count = len(data.get('Meetings', []))
            
            return {
                'success': True,
                'meeting_count': meeting_count,
                'test_date': test_date
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

