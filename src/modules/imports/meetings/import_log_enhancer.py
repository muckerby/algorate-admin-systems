"""
Enhanced Import Logging Service
Provides better logging and display of import information
"""

from datetime import datetime
from typing import Dict, List, Optional

class ImportLogEnhancer:
    """Enhanced logging for import operations"""
    
    @staticmethod
    def format_import_type(trigger_type: str, import_mode: str = 'production') -> str:
        """Format import type for display"""
        type_mapping = {
            'manual': 'MANUAL',
            'scheduled': 'AUTO',
            'test': 'TEST'
        }
        
        base_type = type_mapping.get(trigger_type, trigger_type.upper())
        
        if import_mode == 'test':
            return f"{base_type} (TEST)"
        
        return base_type
    
    @staticmethod
    def format_log_entry(log_entry: Dict) -> Dict:
        """Format a log entry for enhanced display"""
        formatted = log_entry.copy()
        
        # Format import type
        trigger_type = log_entry.get('trigger_type', 'manual')
        import_mode = log_entry.get('import_mode', 'production')
        formatted['formatted_type'] = ImportLogEnhancer.format_import_type(trigger_type, import_mode)
        
        # Format timestamps
        if 'started_at' in log_entry:
            formatted['formatted_date'] = ImportLogEnhancer.format_timestamp(log_entry['started_at'])
        
        # Add status badge info
        status = log_entry.get('status', 'unknown')
        formatted['status_badge'] = ImportLogEnhancer.get_status_badge(status)
        
        # Format summary
        processed = log_entry.get('records_processed', 0)
        inserted = log_entry.get('records_inserted', 0)
        updated = log_entry.get('records_updated', 0)
        
        formatted['summary'] = f"Processed: {processed} | Inserted: {inserted} | Updated: {updated}"
        
        return formatted
    
    @staticmethod
    def format_timestamp(timestamp_str: str) -> str:
        """Format timestamp for Australian display"""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            # Convert to AEST (UTC+10)
            aest_dt = dt.replace(tzinfo=None)  # Simplified for now
            return aest_dt.strftime('%d/%m/%Y %I:%M %p AEST')
        except:
            return timestamp_str
    
    @staticmethod
    def get_status_badge(status: str) -> Dict:
        """Get status badge configuration"""
        badge_config = {
            'completed': {'variant': 'success', 'text': 'COMPLETED'},
            'failed': {'variant': 'destructive', 'text': 'FAILED'},
            'running': {'variant': 'secondary', 'text': 'RUNNING'},
            'pending': {'variant': 'outline', 'text': 'PENDING'}
        }
        
        return badge_config.get(status, {'variant': 'outline', 'text': status.upper()})
    
    @staticmethod
    def get_import_statistics(logs: List[Dict]) -> Dict:
        """Calculate import statistics from logs"""
        stats = {
            'total_imports': len(logs),
            'successful_imports': 0,
            'failed_imports': 0,
            'test_imports': 0,
            'manual_imports': 0,
            'scheduled_imports': 0,
            'total_records_processed': 0,
            'total_records_inserted': 0,
            'total_records_updated': 0
        }
        
        for log in logs:
            status = log.get('status', '')
            trigger_type = log.get('trigger_type', '')
            import_mode = log.get('import_mode', 'production')
            
            # Count by status
            if status == 'completed':
                stats['successful_imports'] += 1
            elif status == 'failed':
                stats['failed_imports'] += 1
            
            # Count by type
            if import_mode == 'test':
                stats['test_imports'] += 1
            elif trigger_type == 'manual':
                stats['manual_imports'] += 1
            elif trigger_type == 'scheduled':
                stats['scheduled_imports'] += 1
            
            # Sum records
            stats['total_records_processed'] += log.get('records_processed', 0)
            stats['total_records_inserted'] += log.get('records_inserted', 0)
            stats['total_records_updated'] += log.get('records_updated', 0)
        
        return stats
    
    @staticmethod
    def format_error_message(error_message: str) -> str:
        """Format error message for better display"""
        if not error_message:
            return ""
        
        # Clean up common error patterns
        if "Could not find the 'message' column" in error_message:
            return "Database schema mismatch - column not found"
        
        if "API request failed" in error_message:
            return "External API connection failed"
        
        if "timeout" in error_message.lower():
            return "Request timeout - API or database connection slow"
        
        # Truncate very long error messages
        if len(error_message) > 200:
            return error_message[:197] + "..."
        
        return error_message
    
    @staticmethod
    def create_import_summary(result: Dict, import_mode: str = 'production') -> str:
        """Create a formatted import summary"""
        total = result.get('total_meetings', 0)
        inserted = result.get('inserted', 0)
        updated = result.get('updated', 0)
        errors = result.get('errors', 0)
        
        summary = f"Import completed: {total} meetings processed"
        
        if inserted > 0:
            summary += f", {inserted} new"
        
        if updated > 0:
            summary += f", {updated} updated"
        
        if errors > 0:
            summary += f", {errors} errors"
        
        if import_mode == 'test':
            summary += " (TEST MODE)"
        
        return summary

