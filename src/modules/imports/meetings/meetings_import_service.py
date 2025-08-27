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
    
    def import_meetings_for_date(self, date_str, test_mode=False):
        """
        Import meetings for a specific date (ISO format YYYY-MM-DD)
        Returns dict with import statistics
        
        Args:
            date_str: Date in YYYY-MM-DD format
            test_mode: If True, marks imported data as test data
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
                    result = self._process_meeting(meeting, date_str, test_mode)
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
    
    def _safe_get_field(self, data, field_names):
        """
        Safely extract field from data with multiple possible field names
        Returns None if field is not found or is empty
        """
        for field_name in field_names:
            value = data.get(field_name)
            if value is not None and value != '':
                return value
        return None
    
    def _process_meeting(self, meeting_data, date_str, test_mode=False):
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
        is_barrier_trial = meeting_data.get('isBarrierTrial', False)
        is_jumps = meeting_data.get('isJumps', False)
        has_sectionals = meeting_data.get('hasSectionals', False)
        
        # Extract timestamp fields from API with better null handling
        form_updated = self._safe_get_field(meeting_data, ['formUpdated', 'form_updated', 'FormUpdated'])
        results_updated = self._safe_get_field(meeting_data, ['resultsUpdated', 'results_updated', 'ResultsUpdated'])
        sectionals_updated = self._safe_get_field(meeting_data, ['sectionalsUpdated', 'sectionals_updated', 'SectionalsUpdated'])
        ratings_updated = self._safe_get_field(meeting_data, ['ratingsUpdated', 'ratings_updated', 'RatingsUpdated'])
        
        # Enhanced field extraction with fallbacks
        expected_condition = self._safe_get_field(meeting_data, ['expectedCondition', 'expected_condition', 'ExpectedCondition', 'condition'])
        rail_position = self._safe_get_field(meeting_data, ['railPosition', 'rail_position', 'RailPosition', 'rail'])
        
        # Log missing fields for debugging
        missing_fields = []
        if not expected_condition:
            missing_fields.append('expectedCondition')
        if not results_updated:
            missing_fields.append('resultsUpdated')
        if not sectionals_updated:
            missing_fields.append('sectionalsUpdated')
        if not ratings_updated:
            missing_fields.append('ratingsUpdated')
            
        if missing_fields:
            print(f"⚠️ Missing fields for meeting {pf_meeting_id}: {', '.join(missing_fields)}")
            print(f"📊 Available fields: {list(meeting_data.keys())}")
        
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
            'is_test_data': test_mode,  # Mark as test data if in test mode
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

