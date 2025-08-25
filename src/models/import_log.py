from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ImportLog(db.Model):
    __tablename__ = 'import_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    import_type = db.Column(db.String(50), nullable=False)  # 'meetings', 'races', etc.
    trigger_type = db.Column(db.String(20), nullable=False)  # 'manual', 'scheduled'
    status = db.Column(db.String(20), nullable=False)  # 'running', 'completed', 'failed'
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    target_date = db.Column(db.String(10), nullable=True)  # ISO format YYYY-MM-DD
    records_processed = db.Column(db.Integer, default=0)
    records_inserted = db.Column(db.Integer, default=0)
    records_updated = db.Column(db.Integer, default=0)
    message = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'import_type': self.import_type,
            'trigger_type': self.trigger_type,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'target_date': self.target_date,
            'records_processed': self.records_processed,
            'records_inserted': self.records_inserted,
            'records_updated': self.records_updated,
            'message': self.message,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<ImportLog {self.id}: {self.import_type} - {self.status}>'

