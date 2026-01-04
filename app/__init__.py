from flask import Flask, redirect, url_for
from flask_session import Session
import os
from dotenv import load_dotenv
from .db.mongo_client import init_mongo_client

# Load environment variables from .env file
load_dotenv()


def create_app():
    # Allow overriding template/static folders from environment (useful for platforms like Render)
    template_folder = os.environ.get('TEMPLATE_FOLDER', 'templates')
    static_folder = os.environ.get('STATIC_FOLDER', 'static')

    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    
    # Configuration from environment variables
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "attendance_secret")
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', "dataset")
    app.config['ENCODING_FILE'] = os.environ.get('ENCODING_FILE', "encodings/face_encodings.pickle")
    app.config['TIMETABLE_FILE'] = os.environ.get('TIMETABLE_FILE', "timetable.csv")
    app.config['ATTENDANCE_DIR'] = os.environ.get('ATTENDANCE_DIR', "attendance_logs")
    app.config['SPLIT_DIR'] = os.environ.get('SPLIT_DIR', "split_encodings")
    
    # Create necessary directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs("encodings", exist_ok=True)
    os.makedirs(app.config['SPLIT_DIR'], exist_ok=True)
    
    # Initialize MongoDB
    init_mongo_client(app)
    
    # Register blueprints
    from .routes import student_routes, faculty_routes, attendance_routes
    
    app.register_blueprint(student_routes.bp)
    app.register_blueprint(faculty_routes.bp)
    app.register_blueprint(attendance_routes.bp)
    
    # Root route
    @app.route('/')
    def root():
        return redirect(url_for('faculty.home'))
    
    return app 