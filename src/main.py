import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.modules.admin.user import user_bp
from src.modules.admin.dashboard import admin_bp
from src.modules.imports.meetings.meetings import meetings_bp
from src.modules.imports.meetings.meeting_status_routes import meeting_status_bp
from src.modules.imports.meetings.ratings_polling_routes import ratings_polling_bp
from src.modules.imports.meetings.api_debug import api_debug_bp
from src.modules.auth.auth import auth_bp
from src.modules.auth.two_factor import two_factor_bp
from src.modules.scheduler.scheduler_routes import scheduler_bp
from src.modules.scheduler.task_scheduler import start_scheduler

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key-change-in-production')

# Enable CORS for all routes
CORS(app)

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/api')
app.register_blueprint(meetings_bp, url_prefix='/api')
app.register_blueprint(meeting_status_bp, url_prefix='/api')
app.register_blueprint(ratings_polling_bp, url_prefix='/api')
app.register_blueprint(api_debug_bp, url_prefix='/api/debug')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(two_factor_bp, url_prefix='/api/auth/2fa')
app.register_blueprint(scheduler_bp, url_prefix='/api')

# Start the task scheduler
start_scheduler()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
