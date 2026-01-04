from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session, current_app
from werkzeug.utils import secure_filename
import os
import pickle
import numpy as np
import pandas as pd
import cv2
import base64
import io
import threading
import time
from threading import Lock
import logging
from datetime import datetime
from PIL import Image
from ..services.face_recognition import FaceRecognitionService
from ..db.mongo_client import get_collections
from ..services.attendance import AttendanceService

bp = Blueprint('attendance', __name__, url_prefix='/attendance')

# Global variables for live attendance tracking
live_attendance_sessions = {}  # Store active sessions
session_lock = Lock()  # Thread-safe access to sessions

# Add logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@bp.route('/', methods=['GET'])
def attendance():
    """Attendance page with class selection"""
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return redirect('/multilogin')
    # Get today's lectures for dropdown
    faculty_map = pd.read_csv('faculty_users.csv')
    faculty_map['faculty_email'] = faculty_map['faculty_email'].str.strip().str.lower()
    faculty_map['faculty_name'] = faculty_map['faculty_name'].str.strip().str.lower()
    faculty_row = faculty_map[faculty_map['faculty_email'] == faculty_email.strip().lower()]
    if faculty_row.empty:
        flash("Faculty not found.", "error")
        return redirect('/login')
    faculty_name = faculty_row.iloc[0]['faculty_name']
    df = pd.read_csv('timetable.csv')
    df['faculty_name'] = df['faculty_name'].str.strip().str.lower()
    today = datetime.now().strftime('%A')
    today_lectures = df[(df['faculty_name'] == faculty_name) & (df['day'] == today)]
    # Add a unique id for each lecture for dropdown value
    today_lectures = today_lectures.copy()
    today_lectures['id'] = today_lectures.apply(lambda row: f"{row['branch']}_{row['semester']}", axis=1)
    lectures_today = today_lectures.to_dict(orient='records')
    return render_template('attendance.html', faculty=faculty_name, lectures_today=lectures_today)

@bp.route('/upload', methods=['POST'])
def attendance_upload():
    """Upload video for attendance processing"""
    try:
        faculty_email = session.get('faculty_email')
        if not faculty_email:
            logger.error("No faculty email in session")
            return jsonify({'error': 'Not logged in'}), 401
        
        class_id = request.form.get('class')
        video = request.files.get('video')
        
        if not class_id or not video:
            logger.error(f"Missing class_id: {class_id}, video: {video}")
            flash('Please select a class and upload a video.', 'error')
            return redirect(url_for('attendance.attendance'))
        
        logger.info(f"Processing video upload for class {class_id} by faculty {faculty_email}")
        
        # Get faculty name
        faculty_map = pd.read_csv('faculty_users.csv')
        faculty_map['faculty_email'] = faculty_map['faculty_email'].str.strip().str.lower()
        faculty_map['faculty_name'] = faculty_map['faculty_name'].str.strip().str.lower()
        faculty_row = faculty_map[faculty_map['faculty_email'] == faculty_email.strip().lower()]
        if faculty_row.empty:
            logger.error(f"Faculty {faculty_email} not found in faculty_users.csv")
            flash("Faculty not found.", "error")
            return redirect('/multilogin')
        faculty_name = faculty_row.iloc[0]['faculty_name']
        
        # Save video temporarily
        os.makedirs('temp_uploads', exist_ok=True)
        video_path = os.path.join('temp_uploads', secure_filename(video.filename))
        video.save(video_path)
        logger.info(f"Video saved to {video_path}")
        
        # Load encodings
        pickle_path = f'split_encodings/{class_id}.pickle'
        if not os.path.exists(pickle_path):
            logger.error(f"Encoding file not found: {pickle_path}")
            flash('Encoding file not found for this class.', 'error')
            os.remove(video_path)
            return redirect(url_for('attendance.attendance'))
        
        logger.info(f"Loading encodings from {pickle_path}")
        try:
            with open(pickle_path, 'rb') as f:
                data = pickle.load(f)
                known_encodings = np.array(data['encodings'])
                known_metadata = data.get('metadata', [])
        except (ModuleNotFoundError, ImportError, ValueError) as e:
            logger.error(f"Could not load pickle file due to version incompatibility: {e}")
            flash('Encoding file is incompatible with current numpy version. Please re-register students.', 'error')
            os.remove(video_path)
            return redirect(url_for('attendance.attendance'))
        
        logger.info(f"Loaded {len(known_encodings)} encodings for {len(known_metadata)} students")
        
        # Initialize face recognition service
        try:
            face_service = FaceRecognitionService()
            logger.info("Face recognition service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize face recognition service: {e}")
            os.remove(video_path)
            flash('Failed to initialize face recognition service.', 'error')
            return redirect(url_for('attendance.attendance'))
        
        # Process video
        video_capture = cv2.VideoCapture(video_path)
        if not video_capture.isOpened():
            logger.error(f"Failed to open video file: {video_path}")
            os.remove(video_path)
            flash('Failed to process video file.', 'error')
            return redirect(url_for('attendance.attendance'))
        
        recognized_students = set()
        tolerance = 0.85
        frame_count = 0
        
        logger.info("Starting video processing...")
        while True:
            ret, frame = video_capture.read()
            if not ret:
                break
            
            frame_count += 1
            if frame_count % 30 == 0:  # Log every 30 frames
                logger.info(f"Processing frame {frame_count}")
            
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            try:
                faces = face_service.get_faces(rgb_small_frame)
                for face in faces:
                    embedding = face.normed_embedding
                    dists = np.linalg.norm(known_encodings - embedding, axis=1)
                    min_dist = np.min(dists)
                    min_idx = np.argmin(dists)
                    if min_dist < tolerance:
                        name = known_metadata[min_idx].get('roll_no') or known_metadata[min_idx].get('name')
                        recognized_students.add(name)
                        logger.info(f"Recognized student: {name} (distance: {min_dist:.3f})")
            except Exception as e:
                logger.error(f"Error processing frame {frame_count}: {e}")
                continue
        
        video_capture.release()
        os.remove(video_path)
        logger.info(f"Video processing completed. Recognized {len(recognized_students)} students")
        
        # Mark attendance in DB for recognized students
        # Get lecture info from timetable
        df = pd.read_csv('timetable.csv')
        branch, semester = class_id.split('_')
        lecture_row = df[(df['branch'] == branch) & (df['semester'].astype(str) == semester) & (df['faculty_name'].str.strip().str.lower() == faculty_name)]
        if lecture_row.empty:
            logger.error(f"Lecture info not found for class {class_id}")
            flash('Lecture info not found.', 'error')
            return redirect(url_for('attendance.attendance'))
        
        lecture = lecture_row.iloc[0]
        subject = lecture['subject']
        section = lecture['section']
        classroom = lecture['classroom']
        start_time = lecture['start_time']
        end_time = lecture['end_time']
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Save to database
        collections = get_collections()
        saved_count = 0
        for name in recognized_students:
            collections['attendance'].insert_one({
                'date': date_str,
                'subject': subject,
                'faculty_email': faculty_email,
                'classroom': classroom,
                'branch': branch,
                'semester': int(semester),
                'section': section,
                'student': {
                    'name': name,
                    'status': 'Present'
                }
            })
            saved_count += 1
        
        logger.info(f"Saved {saved_count} attendance records to database")
        
        return render_template('attendance_result.html', present_students=recognized_students, lecture=lecture)
        
    except Exception as e:
        logger.error(f"Unexpected error in attendance_upload: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Clean up video file if it exists
        try:
            if 'video_path' in locals() and os.path.exists(video_path):
                os.remove(video_path)
        except:
            pass
        
        flash(f'An error occurred while processing the video: {str(e)}', 'error')
        return redirect(url_for('attendance.attendance'))

# Manual Attendance Routes
@bp.route('/manual_attendance', methods=['GET', 'POST'])
def manual_attendance():
    """Manual attendance selection page"""
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return redirect('/login')

    # Get faculty name
    faculty_map = pd.read_csv('faculty_users.csv')
    faculty_map['faculty_email'] = faculty_map['faculty_email'].str.strip().str.lower()
    faculty_map['faculty_name'] = faculty_map['faculty_name'].str.strip().str.lower()
    faculty_row = faculty_map[faculty_map['faculty_email'] == faculty_email.strip().lower()]
    if faculty_row.empty:
        flash("Faculty not found.", "error")
        return redirect('/login')
    faculty_name = faculty_row.iloc[0]['faculty_name']

    # Get today's lectures for this faculty
    df = pd.read_csv('timetable.csv')
    df['faculty_name'] = df['faculty_name'].str.strip().str.lower()
    today = datetime.now().strftime('%A')
    today_lectures = df[(df['faculty_name'] == faculty_name) & (df['day'] == today)]
    lectures = today_lectures.to_dict(orient='records')

    return render_template('manual_attendance_select.html', lectures=lectures)

@bp.route('/manual_attendance/select_students', methods=['POST'])
def manual_attendance_select_students():
    """Select students for manual attendance"""
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return redirect('/login')

    # Get selected lecture info
    branch = request.form.get('branch')
    semester = request.form.get('semester')
    section = request.form.get('section')
    subject = request.form.get('subject')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    classroom = request.form.get('classroom')

    # Get students for this class from MongoDB
    collections = get_collections()
    students_cursor = collections['students'].find({
        "branch": branch,
        "semester": int(semester),
        "section": section
    })
    students = []
    for s in students_cursor:
        students.append({
            "Roll Number": s.get("roll_no"),
            "Student Name": s.get("name")
        })

    lecture_info = {
        'branch': branch,
        'semester': semester,
        'section': section,
        'subject': subject,
        'start_time': start_time,
        'end_time': end_time,
        'classroom': classroom
    }
    return render_template('manual_attendance_mark.html', students=students, lecture=lecture_info)

@bp.route('/manual_attendance/submit', methods=['POST'])
def manual_attendance_submit():
    """Submit manual attendance"""
    faculty_email = session.get('faculty_email')
    faculty_name = session.get('faculty_name')
    if not faculty_email:
        return redirect('/login')

    # Get lecture info
    branch = request.form.get('branch')
    semester = request.form.get('semester')
    section = request.form.get('section')
    subject = request.form.get('subject')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    classroom = request.form.get('classroom')
    date_str = datetime.now().strftime('%Y-%m-%d')

    # Get all student roll numbers and names for this class from MongoDB
    collections = get_collections()
    students_cursor = collections['students'].find({
        "branch": branch,
        "semester": int(semester),
        "section": section
    })
    roll_name_map = {}
    roll_numbers = []
    for s in students_cursor:
        roll_no = s.get("roll_no")
        name = s.get("name")
        roll_name_map[roll_no] = name
        roll_numbers.append(roll_no)

    # Get present students from form
    present_rolls = request.form.getlist('present')

    # Mark attendance in DB with required structure
    for roll in roll_numbers:
        status = 'Present' if roll in present_rolls else 'Absent'
        name = roll_name_map.get(roll, '')
        collections['attendance'].insert_one({
            'date': date_str,
            'subject': subject,
            'faculty_email': faculty_email,
            'classroom': classroom,
            'branch': branch,
            'semester': int(semester),
            'section': section,
            'student': {
                'roll_no': roll,
                'name': name,
                'status': status
            }
        })
    flash('Attendance marked successfully!', 'success')
    return redirect('/dashboard')

# Live Attendance Routes
@bp.route('/live_frame', methods=['POST'])
def attendance_live_frame():
    """Process single frame for live attendance"""
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return jsonify({'error': 'Not logged in'}), 401
    
    class_id = request.form.get('class_id')
    img_data = request.form.get('frame')
    if not class_id or not img_data:
        return jsonify({'error': 'Missing data'}), 400
    
    # Load encodings
    pickle_path = f'split_encodings/{class_id}.pickle'
    if not os.path.exists(pickle_path):
        return jsonify({'error': 'Encoding file not found'}), 404
    
    try:
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)
            known_encodings = np.array(data['encodings'])
            known_metadata = data.get('metadata', [])
    except (ModuleNotFoundError, ImportError, ValueError) as e:
        logger.error(f"Could not load pickle file due to version incompatibility: {e}")
        return jsonify({'error': 'Encoding file is incompatible with current numpy version'}), 500
    
    face_service = FaceRecognitionService()
    img_bytes = base64.b64decode(img_data.split(',')[1])
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    frame = np.array(img)
    faces = face_service.get_faces(frame)
    recognized = set()
    tolerance = 0.85
    
    for face in faces:
        embedding = face.normed_embedding
        dists = np.linalg.norm(known_encodings - embedding, axis=1)
        min_dist = np.min(dists)
        min_idx = np.argmin(dists)
        if min_dist < tolerance:
            name = known_metadata[min_idx].get('roll_no') or known_metadata[min_idx].get('name')
            recognized.add(name)
    
    return jsonify({'recognized': list(recognized)})

@bp.route('/live_submit', methods=['POST'])
def attendance_live_submit():
    """Submit live attendance results"""
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return jsonify({'error': 'Not logged in'}), 401
    
    class_id = request.form.get('class_id')
    recognized_students = request.form.getlist('recognized[]')
    if not class_id or not recognized_students:
        return jsonify({'error': 'Missing data'}), 400
    
    # Get lecture info from timetable
    faculty_map = pd.read_csv('faculty_users.csv')
    faculty_map['faculty_email'] = faculty_map['faculty_email'].str.strip().str.lower()
    faculty_map['faculty_name'] = faculty_map['faculty_name'].str.strip().str.lower()
    faculty_row = faculty_map[faculty_map['faculty_email'] == faculty_email.strip().lower()]
    if faculty_row.empty:
        return jsonify({'error': 'Faculty not found'}), 404
    
    faculty_name = faculty_row.iloc[0]['faculty_name']
    df = pd.read_csv('timetable.csv')
    branch, semester = class_id.split('_')
    lecture_row = df[(df['branch'] == branch) & (df['semester'].astype(str) == semester) & (df['faculty_name'].str.strip().str.lower() == faculty_name)]
    if lecture_row.empty:
        return jsonify({'error': 'Lecture info not found'}), 404
    
    lecture = lecture_row.iloc[0]
    subject = lecture['subject']
    section = lecture['section']
    classroom = lecture['classroom']
    start_time = lecture['start_time']
    end_time = lecture['end_time']
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    collections = get_collections()
    for name in recognized_students:
        collections['attendance'].insert_one({
            'date': date_str,
            'subject': subject,
            'faculty_email': faculty_email,
            'classroom': classroom,
            'branch': branch,
            'semester': int(semester),
            'section': section,
            'student': {
                'name': name,
                'status': 'Present'
            }
        })
    
    return jsonify({'success': True, 'present': recognized_students})

@bp.route('/model_status')
def attendance_model_status():
    """Check if face recognition model is ready"""
    try:
        face_service = FaceRecognitionService()
        # Dummy recognition: blank image
        import numpy as np
        blank = np.zeros((100, 100, 3), dtype=np.uint8)
        _ = face_service.get_faces(blank)
        return jsonify({'ready': True})
    except Exception as e:
        return jsonify({'ready': False, 'error': str(e)})

# Live attendance session management
@bp.route('/start_session', methods=['POST'])
def start_attendance_session():
    """Start a live attendance session"""
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return jsonify({'error': 'Not logged in'}), 401
    
    class_id = request.form.get('class_id')
    if not class_id:
        return jsonify({'error': 'Missing class_id'}), 400
    
    logger.info(f"Starting attendance session for faculty {faculty_email}, class {class_id}")
    
    # Check if encoding file exists
    pickle_path = f'split_encodings/{class_id}.pickle'
    if not os.path.exists(pickle_path):
        logger.error(f"Encoding file not found: {pickle_path}")
        return jsonify({'error': 'Encoding file not found for this class'}), 404
    
    # Create unique session ID
    session_id = f"{faculty_email}_{class_id}_{int(time.time())}"
    
    # Initialize session data
    with session_lock:
        live_attendance_sessions[session_id] = {
            'faculty_email': faculty_email,
            'class_id': class_id,
            'recognized_students': set(),
            'is_active': True,
            'start_time': time.time(),
            'thread': None,
            'model_verified': False
        }
    
    logger.info(f"Created session {session_id} with {len(live_attendance_sessions)} active sessions")
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': 'Attendance session started'
    })

@bp.route('/process_frame', methods=['POST'])
def process_attendance_frame():
    """Process a frame in live attendance session"""
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return jsonify({'error': 'Not logged in'}), 401
    
    session_id = request.form.get('session_id')
    img_data = request.form.get('frame')
    
    if not session_id or not img_data:
        return jsonify({'error': 'Missing session_id or frame data'}), 400
    
    with session_lock:
        if session_id not in live_attendance_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session_data = live_attendance_sessions[session_id]
        if not session_data['is_active']:
            return jsonify({'error': 'Session is not active'}), 400
    
    try:
        # Load encodings for this class
        class_id = session_data['class_id']
        pickle_path = f'split_encodings/{class_id}.pickle'
        
        try:
            with open(pickle_path, 'rb') as f:
                data = pickle.load(f)
                known_encodings = np.array(data['encodings'])
                known_metadata = data.get('metadata', [])
        except (ModuleNotFoundError, ImportError, ValueError) as e:
            logger.error(f"Could not load pickle file due to version incompatibility: {e}")
            return jsonify({'error': 'Encoding file is incompatible with current numpy version'}), 500
        
        # Initialize face recognition
        face_service = FaceRecognitionService()
        
        # Process the frame
        img_bytes = base64.b64decode(img_data.split(',')[1])
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        frame = np.array(img)
        
        # Attempt inference; success here (even with zero faces) verifies model
        faces = face_service.get_faces(frame)
        with session_lock:
            if session_id in live_attendance_sessions:
                live_attendance_sessions[session_id]['model_verified'] = True
        recognized_in_frame = set()
        tolerance = 0.85
        
        for face in faces:
            embedding = face.normed_embedding
            dists = np.linalg.norm(known_encodings - embedding, axis=1)
            min_dist = np.min(dists)
            min_idx = np.argmin(dists)
            
            if min_dist < tolerance:
                student_info = known_metadata[min_idx]
                roll_no = student_info.get('roll_no', '')
                name = student_info.get('name', '')
                student_id = f"{roll_no}_{name}" if roll_no else name
                recognized_in_frame.add(student_id)
        
        # Update session with new recognitions
        with session_lock:
            if session_id in live_attendance_sessions:
                session_data = live_attendance_sessions[session_id]
                session_data['recognized_students'].update(recognized_in_frame)
        
        with session_lock:
            current_verified = live_attendance_sessions.get(session_id, {}).get('model_verified', False)
            total_recognized = len(live_attendance_sessions.get(session_id, {}).get('recognized_students', set()))
        return jsonify({
            'success': True,
            'recognized_in_frame': list(recognized_in_frame),
            'total_recognized': total_recognized,
            'model_verified': current_verified
        })
        
    except Exception as e:
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

@bp.route('/poll_session', methods=['GET'])
def poll_attendance_session():
    """Poll session status for live attendance"""
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return jsonify({'error': 'Not logged in'}), 401
    
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400
    
    with session_lock:
        if session_id not in live_attendance_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session_data = live_attendance_sessions[session_id]
        if not session_data['is_active']:
            return jsonify({'error': 'Session is not active'}), 400
        
        # Get current recognized students
        recognized_students = list(session_data['recognized_students'])
        model_verified = session_data.get('model_verified', False)
        
        return jsonify({
            'success': True,
            'recognized_students': recognized_students,
            'count': len(recognized_students),
            'is_active': session_data['is_active'],
            'model_verified': model_verified
        })

@bp.route('/stop_session', methods=['POST'])
def stop_attendance_session():
    """Stop live attendance session and save results"""
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return jsonify({'error': 'Not logged in'}), 401
    
    session_id = request.form.get('session_id')
    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400
    
    logger.info(f"Stopping attendance session {session_id} for faculty {faculty_email}")
    
    with session_lock:
        if session_id not in live_attendance_sessions:
            logger.error(f"Session {session_id} not found")
            return jsonify({'error': 'Session not found'}), 404
        
        session_data = live_attendance_sessions[session_id]
        session_data['is_active'] = False
        recognized_students = list(session_data['recognized_students'])
        
        logger.info(f"Session {session_id}: Stopping with {len(recognized_students)} recognized students")
        
        # Get lecture info for database insertion
        class_id = session_data['class_id']
        faculty_map = pd.read_csv('faculty_users.csv')
        faculty_map['faculty_email'] = faculty_map['faculty_email'].str.strip().str.lower()
        faculty_map['faculty_name'] = faculty_map['faculty_name'].str.strip().str.lower()
        faculty_row = faculty_map[faculty_map['faculty_email'] == faculty_email.strip().lower()]
        
        if faculty_row.empty:
            logger.error(f"Faculty {faculty_email} not found in faculty_users.csv")
            return jsonify({'error': 'Faculty not found'}), 404
        
        faculty_name = faculty_row.iloc[0]['faculty_name']
        df = pd.read_csv('timetable.csv')
        branch, semester = class_id.split('_')
        lecture_row = df[(df['branch'] == branch) & (df['semester'].astype(str) == semester) & (df['faculty_name'].str.strip().str.lower() == faculty_name)]
        
        if lecture_row.empty:
            logger.error(f"Lecture info not found for class {class_id}")
            return jsonify({'error': 'Lecture info not found'}), 404
        
        lecture = lecture_row.iloc[0]
        subject = lecture['subject']
        section = lecture['section']
        classroom = lecture['classroom']
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Save attendance to database
        collections = get_collections()
        saved_count = 0
        present_roll_nos = set()
        for student_id in recognized_students:
            # Parse student_id (format: "roll_no_name" or just "name")
            if '_' in student_id:
                roll_no, name = student_id.split('_', 1)
            else:
                roll_no = ''
                name = student_id
            present_roll_nos.add(roll_no)
            collections['attendance'].insert_one({
                'date': date_str,
                'subject': subject,
                'faculty_email': faculty_email,
                'classroom': classroom,
                'branch': branch,
                'semester': int(semester),
                'section': section,
                'student': {
                    'roll_no': roll_no,
                    'name': name,
                    'status': 'Present'
                }
            })
            saved_count += 1
        
        # Mark absent for students not recognized
        attendance_service = AttendanceService()
        all_students = attendance_service.get_students_for_class(branch, semester, section)
        for student in all_students:
            if student['roll_no'] not in present_roll_nos:
                collections['attendance'].insert_one({
                    'date': date_str,
                    'subject': subject,
                    'faculty_email': faculty_email,
                    'classroom': classroom,
                    'branch': branch,
                    'semester': int(semester),
                    'section': section,
                    'student': {
                        'roll_no': student['roll_no'],
                        'name': student['name'],
                        'status': 'Absent'
                    }
                })
        
        logger.info(f"Session {session_id}: Saved {saved_count} attendance records to database")
        
        # Clean up session
        del live_attendance_sessions[session_id]
        logger.info(f"Session {session_id} cleaned up. Active sessions: {len(live_attendance_sessions)}")
        
        return jsonify({
            'success': True,
            'message': 'Attendance session stopped and saved',
            'recognized_students': recognized_students,
            'count': len(recognized_students)
        }) 