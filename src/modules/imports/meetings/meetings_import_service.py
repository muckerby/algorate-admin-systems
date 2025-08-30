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
            
            if not meetings_data or 'Meetings' not in meetings_data:
                return {
                    'total_meetings': 0,
                    'inserted': 0,
                    'updated': 0,
                    'errors': 0,
                    'message': 'No meetings found for this date'
                }
            
            meetings = meetings_data['Meetings']
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
                    meeting_id = meeting.get('meetingId', meeting.get('MeetingId', meeting.get('id', 'unknown')))
                    print(f"Error processing meeting {meeting_id}: {str(e)}")
            
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
        # First try direct field access
        for field_name in field_names:
            value = data.get(field_name)
            if value is not None and value != '':
                return value
        
        # If not found, try recursive search in nested objects
        return self._find_field_recursive(data, field_names)
    
    def _find_field_recursive(self, data, field_names, path=""):
        """
        Recursively search for field in nested objects
        Returns the first matching field value found
        """
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check if this key matches any of our target field names (case insensitive)
                for field_name in field_names:
                    if key.lower() == field_name.lower():
                        if value is not None and value != '':
                            return value
                
                # Recursively search in nested objects
                if isinstance(value, dict):
                    result = self._find_field_recursive(value, field_names, current_path)
                    if result is not None:
                        return result
                elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    # Search in first item of list if it contains objects
                    result = self._find_field_recursive(value[0], field_names, f"{current_path}[0]")
                    if result is not None:
                        return result
        
        return None
    
    def _debug_available_fields(self, meeting_data, meeting_id):
        """Log all available fields for debugging NULL field issues"""
        print(f"🔍 DEBUG: Available fields for meeting {meeting_id}:")
        
        def print_fields(obj, prefix="", max_depth=3, current_depth=0):
            if current_depth >= max_depth:
                return
                
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        print(f"  {prefix}{key}: [nested object with {len(value)} fields]")
                        if current_depth < max_depth - 1:
                            print_fields(value, f"{prefix}{key}.", max_depth, current_depth + 1)
                    elif isinstance(value, list):
                        print(f"  {prefix}{key}: [list with {len(value)} items]")
                        if len(value) > 0 and isinstance(value[0], dict):
                            print(f"  {prefix}{key}[0]: [object with {len(value[0])} fields]")
                    else:
                        value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                        print(f"  {prefix}{key}: {type(value).__name__} = {value_str}")
        
        print_fields(meeting_data)
    
    def _process_meeting(self, meeting_data, date_str, test_mode=False):
        """
        Process a single meeting and insert/update in database
        Returns 'inserted' or 'updated'
        """
        # Extract meeting data with correct field names - handle multiple possible formats
        pf_meeting_id = str(meeting_data.get('meetingId', meeting_data.get('MeetingId', meeting_data.get('id', ''))))
        
        # Track data might be nested in 'track' object or directly in meeting data
        track_data = meeting_data.get('track', meeting_data.get('Track', meeting_data))
        track_name = track_data.get('name', track_data.get('Name', track_data.get('trackName', track_data.get('TrackName', ''))))
        track_id = str(track_data.get('trackId', track_data.get('TrackId', track_data.get('id', track_data.get('Id', '')))))
        track_state = track_data.get('state', track_data.get('State', track_data.get('trackState', track_data.get('TrackState', ''))))
        track_location = track_data.get('location', track_data.get('Location', track_data.get('trackLocation', '')))
        track_abbreviation = track_data.get('abbrev', track_data.get('Abbrev', track_data.get('abbreviation', track_data.get('Abbreviation', ''))))
        
        stage = meeting_data.get('stage', 'A')
        tab_meeting = meeting_data.get('tabMeeting', True)
        is_barrier_trial = meeting_data.get('isBarrierTrial', False)
        is_jumps = meeting_data.get('isJumps', False)
        has_sectionals = meeting_data.get('hasSectionals', False)
        
        # Enhanced field extraction with comprehensive fallbacks and debugging
        expected_condition_fields = [
            'expectedCondition', 'expected_condition', 'ExpectedCondition', 
            'condition', 'trackCondition', 'track_condition', 'trackConditions',
            'weather', 'weatherCondition', 'going', 'surface', 'trackSurface'
        ]
        
        results_updated_fields = [
            'resultsUpdated', 'results_updated', 'ResultsUpdated',
            'resultUpdated', 'result_updated', 'lastResultUpdate',
            'resultsLastUpdated', 'resultTime', 'finishedAt',
            'completedAt', 'raceFinished', 'resultsAvailable'
        ]
        
        sectionals_updated_fields = [
            'sectionalsUpdated', 'sectionals_updated', 'SectionalsUpdated',
            'sectionalUpdated', 'sectional_updated', 'lastSectionalUpdate',
            'sectionalsLastUpdated', 'sectionalTime', 'sectionalData',
            'timingUpdated', 'sectionalAvailable'
        ]
        
        ratings_updated_fields = [
            'ratingsUpdated', 'ratings_updated', 'RatingsUpdated',
            'ratingUpdated', 'rating_updated', 'lastRatingUpdate',
            'ratingsLastUpdated', 'formUpdated', 'form_updated'
        ]
        
        # Extract fields with enhanced search
        expected_condition = self._safe_get_field(meeting_data, expected_condition_fields)
        results_updated = self._safe_get_field(meeting_data, results_updated_fields)
        sectionals_updated = self._safe_get_field(meeting_data, sectionals_updated_fields)
        ratings_updated = self._safe_get_field(meeting_data, ratings_updated_fields)
        
        # Enhanced debugging for NULL fields
        missing_fields = []
        if not expected_condition:
            missing_fields.append('expected_condition')
        if not results_updated:
            missing_fields.append('results_updated')
        if not sectionals_updated:
            missing_fields.append('sectionals_updated')
        if not ratings_updated:
            missing_fields.append('ratings_updated')
            
        if missing_fields:
            print(f"⚠️ Missing fields for meeting {pf_meeting_id}: {', '.join(missing_fields)}")
            # Enable detailed debugging for first few meetings with missing fields
            if len(missing_fields) >= 2:  # If 2 or more fields are missing, debug
                self._debug_available_fields(meeting_data, pf_meeting_id)
        
        # Extract rail position with enhanced search
        rail_position_fields = [
            'railPosition', 'rail_position', 'RailPosition', 'rail',
            'railPos', 'trackRail', 'barrierPosition'
        ]
        rail_position = self._safe_get_field(meeting_data, rail_position_fields)
        
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
            'form_updated': ratings_updated,  # Use ratings_updated for form_updated
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

