from flask import Blueprint, jsonify
import requests
import os
from datetime import datetime

api_debug_bp = Blueprint('api_debug', __name__)

@api_debug_bp.route('/raw-api-response', methods=['GET'])
def get_raw_api_response():
    """Get raw API response to examine field structure"""
    try:
        # Use a date we know has meetings
        target_date = "29/08/2025"
        
        # Get API key from environment
        api_key = os.getenv('PUNTING_FORM_API_KEY')
        if not api_key:
            return jsonify({
                'error': 'API key not found',
                'message': 'PUNTING_FORM_API_KEY environment variable not set'
            }), 500
        
        # Make API call
        url = "https://api.puntingform.com.au/v2/form/meetingslist"
        params = {
            'meetingDate': target_date,
            'apiKey': api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        api_data = response.json()
        
        # Get first meeting for detailed examination
        meetings = api_data.get('Meetings', [])
        if not meetings:
            return jsonify({
                'error': 'No meetings found',
                'api_response': api_data,
                'target_date': target_date
            })
        
        first_meeting = meetings[0]
        
        return jsonify({
            'success': True,
            'target_date': target_date,
            'total_meetings': len(meetings),
            'raw_api_structure': {
                'top_level_keys': list(api_data.keys()),
                'meetings_count': len(meetings),
                'first_meeting_keys': list(first_meeting.keys()) if first_meeting else [],
                'first_meeting_data': first_meeting
            },
            'field_analysis': {
                'looking_for': ['sectionals_updated', 'expected_condition', 'results_updated'],
                'possible_matches': _find_possible_field_matches(first_meeting)
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to fetch raw API response'
        }), 500

def _find_possible_field_matches(meeting_data):
    """Find possible field matches for our target fields"""
    target_fields = ['sectionals_updated', 'expected_condition', 'results_updated']
    possible_matches = {}
    
    def search_nested(obj, path=""):
        matches = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check if key contains any target field keywords
                key_lower = key.lower()
                for target in target_fields:
                    target_words = target.split('_')
                    if any(word in key_lower for word in target_words):
                        matches.append({
                            'path': current_path,
                            'key': key,
                            'value': value,
                            'target_field': target
                        })
                
                # Recursively search nested objects
                if isinstance(value, (dict, list)):
                    matches.extend(search_nested(value, current_path))
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                matches.extend(search_nested(item, current_path))
        
        return matches
    
    all_matches = search_nested(meeting_data)
    
    # Group by target field
    for target in target_fields:
        possible_matches[target] = [m for m in all_matches if m['target_field'] == target]
    
    return possible_matches

