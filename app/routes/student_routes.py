from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, session
from werkzeug.utils import secure_filename
import os
import pickle
import numpy as np
import base64
import io
from PIL import Image
from ..services.face_recognition import FaceRecognitionService
from ..db.mongo_client import get_collections
import pandas as pd
import bcrypt

bp = Blueprint('students', __name__)

@bp.route('/student/login', methods=['POST'])
def student_login():
    """Student login endpoint used by multilogin page"""
    collections = get_collections()
    roll_no = request.form.get('roll_no', '').strip()
    password = request.form.get('password', '')

    if not roll_no or not password:
        flash("Please enter roll number and password.", "error")
        return redirect('/multilogin')

    user = collections['students'].find_one({"roll_no": roll_no})
    if not user or not isinstance(user.get('password'), (bytes, bytearray)) or not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        flash("Invalid roll number or password.", "error")
        return redirect('/multilogin')

    session['student_roll_no'] = roll_no
    session['student_name'] = user.get('name', 'Student')
    session['role'] = 'student'

    # Redirect student after login
    return redirect('/student/dashboard')


def _require_student_session():
    roll_no = session.get('student_roll_no')
    if not roll_no:
        return None
    return roll_no


def _get_student_doc(roll_no):
    cols = get_collections()
    return cols['students'].find_one({"roll_no": roll_no})


@bp.route('/student/dashboard')
def student_dashboard():
    roll_no = _require_student_session()
    if not roll_no:
        return redirect('/multilogin')

    cols = get_collections()
    student = _get_student_doc(roll_no)
    if not student:
        flash('Student not found.', 'error')
        return redirect('/multilogin')

    student_name = student.get('name', 'Student')
    branch = student.get('branch', '')
    semester = str(student.get('semester', ''))
    section = student.get('section', 'A')

    # Today's classes from timetable.csv
    df = pd.read_csv('timetable.csv') if os.path.exists('timetable.csv') else pd.DataFrame()
    today_classes = []
    attendance_stats = {}
    recent_attendance = []
    monthly_trend = {}

    if not df.empty:
        today = pd.Timestamp.now().strftime('%A')
        class_df = df[(df['branch'] == branch) & (df['semester'].astype(str) == semester) & (df['section'] == section) & (df['day'] == today)]
        today_classes = class_df.to_dict(orient='records')

    # Subject-wise attendance stats for this student
    # Build list of subjects from timetable or attendance
    subjects = set([c.get('subject') for c in today_classes])
    for doc in cols['attendance'].find({"student.roll_no": roll_no}):
        if doc.get('subject'):
            subjects.add(doc['subject'])

    for subj in subjects:
        total = cols['attendance'].count_documents({"student.roll_no": roll_no, "subject": subj})
        present = cols['attendance'].count_documents({"student.roll_no": roll_no, "subject": subj, "student.status": "Present"})
        percentage = int(round((present / total) * 100)) if total > 0 else 0
        attendance_stats[subj] = {"total": total, "present": present, "percentage": percentage}

    # Recent attendance (latest 10)
    recent_cursor = cols['attendance'].find({"student.roll_no": roll_no}).sort("_id", -1).limit(10)
    for r in recent_cursor:
        recent_attendance.append({
            'subject': r.get('subject', ''),
            'date': r.get('date', ''),
            'status': r.get('student', {}).get('status', '')
        })

    # Get all unique subjects from timetable for this student
    timetable_subjects = set()
    if not df.empty:
        student_timetable = df[(df['branch'] == branch) & (df['semester'].astype(str) == semester) & (df['section'] == section)]
        timetable_subjects = student_timetable['subject'].drop_duplicates().tolist()

    # Weekly attendance by subject (past 7 days)
    from datetime import datetime, timedelta

    weekly_attendance = {}
    week_ago = datetime.now() - timedelta(days=7)

    for subject in timetable_subjects:
        # Get attendance records for this subject in the past week
        weekly_docs = cols['attendance'].find({
            "student.roll_no": roll_no,
            "subject": subject,
            "date": {"$gte": week_ago.strftime("%Y-%m-%d")}
        })

        total_weekly = 0
        present_weekly = 0

        for doc in weekly_docs:
            total_weekly += 1
            if doc.get('student', {}).get('status') == 'Present':
                present_weekly += 1

        if total_weekly > 0:
            weekly_attendance[subject] = {
                "present": present_weekly,
                "absent": total_weekly - present_weekly,
                "total": total_weekly
            }

    overall_total = sum(v['total'] for v in attendance_stats.values())
    overall_present = sum(v['present'] for v in attendance_stats.values())
    overall_absent = overall_total - overall_present
    overall_percentage = int(round((overall_present / overall_total) * 100)) if overall_total > 0 else 0

    return render_template(
        'student_dashboard.html',
        student_name=student_name,
        student_roll_no=roll_no,
        student_branch=branch,
        student_semester=semester,
        student_section=section,
        today_classes=today_classes,
        attendance_stats=attendance_stats,
        recent_attendance=recent_attendance,
        monthly_trend=monthly_trend,
        overall_percentage=overall_percentage,
        overall_stats={
            'total_present': overall_present,
            'total_absent': overall_absent
        },
        timetable_subjects=timetable_subjects,
        weekly_attendance=weekly_attendance
    )


@bp.route('/student/timetable')
def student_timetable():
    roll_no = _require_student_session()
    if not roll_no:
        return redirect('/multilogin')

    student = _get_student_doc(roll_no)
    if not student:
        flash('Student not found.', 'error')
        return redirect('/multilogin')

    student_name = student.get('name', 'Student')
    branch = student.get('branch', '')
    semester = str(student.get('semester', ''))
    section = student.get('section', 'A')

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    timetable = {d: [] for d in days}

    df = pd.read_csv('timetable.csv') if os.path.exists('timetable.csv') else pd.DataFrame()
    if not df.empty:
        class_df = df[(df['branch'] == branch) & (df['semester'].astype(str) == semester) & (df['section'] == section)]
        # sort by start_time within day
        for day in days:
            day_df = class_df[class_df['day'] == day]
            try:
                day_df = day_df.sort_values(by='start_time')
            except:
                pass
            timetable[day] = day_df.to_dict(orient='records')

    return render_template('student_timetable.html', student_name=student_name, days=days, timetable=timetable)


@bp.route('/student/attendance')
def student_attendance():
    roll_no = _require_student_session()
    if not roll_no:
        return redirect('/multilogin')

    student = _get_student_doc(roll_no)
    if not student:
        flash('Student not found.', 'error')
        return redirect('/multilogin')

    student_name = student.get('name', 'Student')

    cols = get_collections()
    detailed = []

    # Build subject list from attendance docs
    subjects = cols['attendance'].distinct('subject', {"student.roll_no": roll_no})
    for subj in subjects:
        if not subj:
            continue
        total = cols['attendance'].count_documents({"student.roll_no": roll_no, "subject": subj})
        present = cols['attendance'].count_documents({"student.roll_no": roll_no, "subject": subj, "student.status": "Present"})
        percentage = int(round((present / total) * 100)) if total > 0 else 0
        # recent records for subject
        records = []
        for r in cols['attendance'].find({"student.roll_no": roll_no, "subject": subj}).sort("_id", -1).limit(20):
            records.append({
                'date': r.get('date', ''),
                'status': r.get('student', {}).get('status', '')
            })
        detailed.append({
            'subject': subj,
            'faculty': r.get('faculty_email', '' ) if records else '',
            'present_classes': present,
            'total_classes': total,
            'percentage': percentage,
            'attendance_records': records
        })

    return render_template('student_attendance.html', student_name=student_name, detailed_attendance=detailed)


@bp.route('/student/profile')
def student_profile():
    roll_no = _require_student_session()
    if not roll_no:
        return redirect('/multilogin')

    student = _get_student_doc(roll_no)
    if not student:
        flash('Student not found.', 'error')
        return redirect('/multilogin')

    return render_template('student_profile.html', student=student)


@bp.route('/student/change-password', methods=['GET', 'POST'])
def student_change_password():
    roll_no = _require_student_session()
    if not roll_no:
        return redirect('/multilogin')

    cols = get_collections()
    student = _get_student_doc(roll_no)
    if not student:
        flash('Student not found.', 'error')
        return redirect('/multilogin')

    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if new_password != confirm_password:
            flash('New password and confirm password do not match.', 'error')
            return render_template('student_change_password.html')

        stored_hash = student.get('password')
        if not isinstance(stored_hash, (bytes, bytearray)) or not bcrypt.checkpw(current_password.encode('utf-8'), stored_hash):
            flash('Current password is incorrect.', 'error')
            return render_template('student_change_password.html')

        new_hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        cols['students'].update_one({'_id': student['_id']}, {'$set': {'password': new_hashed}})
        # Logout after password change and send to multilogin
        session.pop('student_roll_no', None)
        session.pop('student_name', None)
        if 'role' in session and session['role'] == 'student':
            session.pop('role', None)
        flash('Password changed successfully. Please log in again.', 'success')
        return redirect('/multilogin')

    return render_template('student_change_password.html')


@bp.route('/student/logout')
def student_logout():
    session.pop('student_roll_no', None)
    session.pop('student_name', None)
    if 'role' in session and session['role'] == 'student':
        session.pop('role', None)
    return redirect('/multilogin')

@bp.route('/students')
def students():
    """Display all students for the logged-in faculty"""
    from flask import session
    
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return redirect('/multilogin')

    # Get faculty name
    faculty_map = pd.read_csv('faculty_users.csv')
    faculty_map['faculty_email'] = faculty_map['faculty_email'].str.strip().str.lower()
    faculty_map['faculty_name'] = faculty_map['faculty_name'].str.strip().str.lower()
    faculty_row = faculty_map[faculty_map['faculty_email'] == faculty_email.strip().lower()]
    if faculty_row.empty:
        flash("Faculty not found.", "error")
        return redirect('/multilogin')
    faculty_name = faculty_row.iloc[0]['faculty_name']

    # Get all classes taught by this faculty
    df = pd.read_csv('timetable.csv')
    df['faculty_name'] = df['faculty_name'].str.strip().str.lower()
    faculty_df = df[df['faculty_name'] == faculty_name]
    # Get all unique (branch, semester, section) tuples
    class_tuples = faculty_df[['branch', 'semester', 'section']].drop_duplicates().to_records(index=False)

    # Fetch all students in these classes
    collections = get_collections()
    students = []
    for branch, semester, section in class_tuples:
        students_cursor = collections['students'].find({
            "branch": branch,
            "semester": int(semester),
            "section": section
        })
        for s in students_cursor:
            students.append({
                "roll_no": str(s.get("roll_no")),
                "name": str(s.get("name")),
                "branch": str(branch),
                "semester": int(semester),
                "section": str(section)
            })
    return render_template('students.html', students=students, faculty=faculty_name)

@bp.route('/register_student_face', methods=['GET', 'POST'])
def register_student_face():
    """Register a student with face photos"""
    from flask import session
    
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return redirect('/multilogin')

    # Get faculty name
    faculty_map = pd.read_csv('faculty_users.csv')
    faculty_map['faculty_email'] = faculty_map['faculty_email'].str.strip().str.lower()
    faculty_map['faculty_name'] = faculty_map['faculty_name'].str.strip().str.lower()
    faculty_row = faculty_map[faculty_map['faculty_email'] == faculty_email.strip().lower()]
    if faculty_row.empty:
        flash("Faculty not found.", "error")
        return redirect('/multilogin')
    faculty_name = faculty_row.iloc[0]['faculty_name']
    
    collections = get_collections()
    branches = ['CE', 'CSE', 'IT', 'ECE']
    semesters = [1, 2, 3, 4, 5, 6, 7, 8]
    message = None
    error = None
    selected_branch = None
    selected_semester = None
    students = []

    if request.method == 'POST':
        branch = request.form.get('branch')
        semester = request.form.get('semester')
        selected_branch = branch
        selected_semester = semester
        # Filter students for dropdown
        if branch and semester:
            students = list(collections['students'].find({"branch": branch, "semester": int(semester)}, {"_id": 0}))
        else:
            students = list(collections['students'].find({}, {"_id": 0}))
        student_id = request.form.get('student_id')
        new_name = request.form.get('new_name').strip()
        new_roll_no = request.form.get('new_roll_no').strip()
        section = None
        if student_id:
            student = collections['students'].find_one({"roll_no": student_id})
            if not student:
                error = "Selected student not found."
            else:
                name = student['name']
                roll_no = student['roll_no']
                semester = student['semester']
                branch = student['branch']
                section = student.get('section', 'A')
        elif new_name and new_roll_no:
            name = new_name
            roll_no = new_roll_no
            section = 'A'
            if not collections['students'].find_one({"roll_no": roll_no}):
                default_hash = bcrypt.hashpw('123456'.encode('utf-8'), bcrypt.gensalt())
                collections['students'].insert_one({
                    "roll_no": roll_no,
                    "name": name,
                    "semester": int(semester),
                    "branch": branch,
                    "section": section,
                    "password": default_hash
                })
        else:
            error = "Please select or enter student details."
        photos = [request.files.get(f'photo{i}') for i in range(1, 4)]
        if not error and (not all(photos) or not all(photo and photo.filename for photo in photos)):
            error = "Please upload 3 face photos."
        if not error:
            face_service = FaceRecognitionService()
            encodings = []
            for idx, photo in enumerate(photos):
                filename = secure_filename(f"{roll_no}_{name}_face{idx+1}.jpg")
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                photo.save(save_path)
                import cv2
                img = cv2.imread(save_path)
                if img is None:
                    error = f"Failed to read uploaded image {filename}."
                    break
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                faces = face_service.get_faces(rgb)
                if not faces:
                    error = f"No face found in {filename}."
                    break
                encodings.append(faces[0].normed_embedding)
            
            if not error and len(encodings) == 3:
                avg_encoding = np.mean(encodings, axis=0)
                
                # Check if this face is already registered in any class
                split_dir = current_app.config['SPLIT_DIR']
                os.makedirs(split_dir, exist_ok=True)
                
                # Get all pickle files in split_encodings directory
                all_pickle_files = [f for f in os.listdir(split_dir) if f.endswith('.pickle')]
                existing_registration = None
                
                for pickle_file in all_pickle_files:
                    pickle_path = os.path.join(split_dir, pickle_file)
                    try:
                        with open(pickle_path, 'rb') as f:
                            data = pickle.load(f)
                            existing_encodings = data.get('encodings', [])
                            existing_metadata = data.get('metadata', [])
                            
                            if existing_encodings:
                                # Compare with existing encodings
                                for i, existing_encoding in enumerate(existing_encodings):
                                    distance = np.linalg.norm(avg_encoding - existing_encoding)
                                    if distance < 0.85:  # Same tolerance as face recognition
                                        existing_student = existing_metadata[i]
                                        existing_class = pickle_file.replace('.pickle', '')
                                        existing_registration = {
                                            'student_name': existing_student.get('name', 'Unknown'),
                                            'student_roll': existing_student.get('roll_no', 'Unknown'),
                                            'class': existing_class,
                                            'distance': distance
                                        }
                                        break
                                        
                    except (ModuleNotFoundError, ImportError, ValueError) as e:
                        # Skip incompatible files
                        continue
                    except Exception as e:
                        # Skip other errors
                        continue
                    
                    if existing_registration:
                        break
                
                # If face is already registered in another class
                if existing_registration:
                    error = f"Face already registered! This face belongs to {existing_registration['student_name']} ({existing_registration['student_roll']}) in class {existing_registration['class']}. Distance: {existing_registration['distance']:.3f}"
                else:
                    # Proceed with registration in the selected class
                    pickle_path = os.path.join(split_dir, f"{branch}_{semester}.pickle")
                    if os.path.exists(pickle_path):
                        try:
                            with open(pickle_path, 'rb') as f:
                                data = pickle.load(f)
                        except (ModuleNotFoundError, ImportError, ValueError) as e:
                            # Handle numpy version incompatibility
                            print(f"Warning: Could not load existing pickle file due to version incompatibility: {e}")
                            print("Creating new pickle file...")
                            data = {"encodings": [], "metadata": []}
                    else:
                        data = {"encodings": [], "metadata": []}
                    
                    new_metadata = {"roll_no": roll_no, "name": name, "semester": int(semester), "branch": branch, "section": section}
                    filtered = [(e, m) for e, m in zip(data["encodings"], data["metadata"]) if m.get("roll_no") != roll_no]
                    data["encodings"] = [e for e, m in filtered]
                    data["metadata"] = [m for e, m in filtered]
                    data["encodings"].append(avg_encoding)
                    data["metadata"].append(new_metadata)
                    with open(pickle_path, 'wb') as f:
                        pickle.dump(data, f)
                    message = f"Student {name} ({roll_no}) registered successfully!"
        # Refresh students list for the selected branch/semester
        if selected_branch and selected_semester:
            students = list(collections['students'].find({"branch": selected_branch, "semester": int(selected_semester)}, {"_id": 0}))
        else:
            students = list(collections['students'].find({}, {"_id": 0}))
        # AJAX/JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if error:
                return {"success": False, "message": error}
            else:
                return {"success": True, "message": message}
    else:
        # GET: show all students by default
        students = list(collections['students'].find({}, {"_id": 0}))
    return render_template('register_student_face.html', branches=branches, semesters=semesters, students=students, message=message, error=error, selected_branch=selected_branch, selected_semester=selected_semester, faculty=faculty_name)

@bp.route('/check_existing_registration')
def check_existing_registration():
    """Check if a student already has face registrations in any class"""
    from flask import session
    
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return jsonify({'error': 'Not logged in'}), 401
    
    student_id = request.args.get('student_id')
    if not student_id:
        return jsonify({'error': 'Missing student_id'}), 400
    
    # Get student info
    collections = get_collections()
    student = collections['students'].find_one({"roll_no": student_id})
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    # Check all pickle files for this student's face
    split_dir = current_app.config['SPLIT_DIR']
    existing_registrations = []
    
    if os.path.exists(split_dir):
        all_pickle_files = [f for f in os.listdir(split_dir) if f.endswith('.pickle')]
        
        for pickle_file in all_pickle_files:
            pickle_path = os.path.join(split_dir, pickle_file)
            try:
                with open(pickle_path, 'rb') as f:
                    data = pickle.load(f)
                    existing_metadata = data.get('metadata', [])
                    
                    # Check if this student is in this class
                    for metadata in existing_metadata:
                        if metadata.get('roll_no') == student_id:
                            class_name = pickle_file.replace('.pickle', '')
                            branch, semester = class_name.split('_')
                            existing_registrations.append({
                                'class': class_name,
                                'branch': branch,
                                'semester': semester,
                                'section': metadata.get('section', 'A')
                            })
                            break
                            
            except (ModuleNotFoundError, ImportError, ValueError) as e:
                # Skip incompatible files
                continue
            except Exception as e:
                # Skip other errors
                continue
    
    return jsonify({
        'student_name': student.get('name', 'Unknown'),
        'student_roll': student.get('roll_no', 'Unknown'),
        'existing_registrations': existing_registrations
    })

@bp.route('/face_registrations_summary')
def face_registrations_summary():
    """Show a summary of all face registrations in the system"""
    from flask import session
    
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return redirect('/multilogin')
    
    # Get faculty name
    faculty_map = pd.read_csv('faculty_users.csv')
    faculty_map['faculty_email'] = faculty_map['faculty_email'].str.strip().str.lower()
    faculty_map['faculty_name'] = faculty_map['faculty_name'].str.strip().str.lower()
    faculty_row = faculty_map[faculty_map['faculty_email'] == faculty_email.strip().lower()]
    if faculty_row.empty:
        flash("Faculty not found.", "error")
        return redirect('/multilogin')
    faculty_name = faculty_row.iloc[0]['faculty_name']
    
    # Get all face registrations
    split_dir = current_app.config['SPLIT_DIR']
    all_registrations = []
    
    if os.path.exists(split_dir):
        all_pickle_files = [f for f in os.listdir(split_dir) if f.endswith('.pickle')]
        
        for pickle_file in all_pickle_files:
            pickle_path = os.path.join(split_dir, pickle_file)
            try:
                with open(pickle_path, 'rb') as f:
                    data = pickle.load(f)
                    encodings = data.get('encodings', [])
                    metadata = data.get('metadata', [])
                    
                    class_name = pickle_file.replace('.pickle', '')
                    branch, semester = class_name.split('_')
                    
                    for i, student_meta in enumerate(metadata):
                        all_registrations.append({
                            'student_name': student_meta.get('name', 'Unknown'),
                            'student_roll': student_meta.get('roll_no', 'Unknown'),
                            'class': class_name,
                            'branch': branch,
                            'semester': semester,
                            'section': student_meta.get('section', 'A'),
                            'encoding_index': i
                        })
                        
            except (ModuleNotFoundError, ImportError, ValueError) as e:
                # Skip incompatible files
                continue
            except Exception as e:
                # Skip other errors
                continue
    # Sort by class and then by student name
    all_registrations.sort(key=lambda x: (x['class'], x['student_name']))
    
    return render_template('face_registrations_summary.html', 
                         registrations=all_registrations, 
                         faculty=faculty_name)
    
@bp.route('/delete_student_face', methods=['POST'])
def delete_student_face():
    """Delete all face registration data for a specific student"""
    from flask import session

    print("Delete student face route called")
    faculty_email = session.get('faculty_email')
    print(f"Faculty email from session: {faculty_email}")

    if not faculty_email:
        print("No faculty email in session")
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    try:
        data = request.get_json()
        print(f"Request data: {data}")
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        student_roll = data.get('student_roll')
        # class_name is now optional; we will remove from ALL classes regardless
        class_name = data.get('class_name')

        print(f"Student roll: {student_roll}, Class name: {class_name}")

        if not student_roll:
            return jsonify({'success': False, 'message': 'Missing student_roll'}), 400

        # Get collections and current app config
        collections = get_collections()
        split_dir = current_app.config['SPLIT_DIR']
        upload_folder = current_app.config['UPLOAD_FOLDER']

        print(f"Split dir: {split_dir}, Upload folder: {upload_folder}")

        # Remove student's face data from ALL class pickle files
        classes_affected = []
        total_removed = 0
        if os.path.exists(split_dir):
            all_pickle_files = [f for f in os.listdir(split_dir) if f.endswith('.pickle')]
            for pickle_file in all_pickle_files:
                pickle_path = os.path.join(split_dir, pickle_file)
                try:
                    with open(pickle_path, 'rb') as f:
                        pkl = pickle.load(f)
                    encodings = pkl.get('encodings', [])
                    metadata = pkl.get('metadata', [])
                    original_count = len(metadata)

                    filtered_encodings = []
                    filtered_metadata = []
                    removed_here = 0

                    for i, meta in enumerate(metadata):
                        if meta.get('roll_no') != student_roll:
                            filtered_encodings.append(encodings[i])
                            filtered_metadata.append(meta)
                        else:
                            removed_here += 1

                    if removed_here > 0:
                        pkl['encodings'] = filtered_encodings
                        pkl['metadata'] = filtered_metadata
                        with open(pickle_path, 'wb') as f:
                            pickle.dump(pkl, f)
                        classes_affected.append(pickle_file.replace('.pickle', ''))
                        total_removed += removed_here
                except Exception as e:
                    print(f"Warning: Skipping pickle {pickle_path} due to error: {e}")

        # Remove uploaded face images for this roll number
        removed_files = []
        try:
            import glob
            for i in range(1, 4):
                pattern = os.path.join(upload_folder, f"{student_roll}_*_face{i}.jpg")
                matching_files = glob.glob(pattern)
                for file_path in matching_files:
                    try:
                        os.remove(file_path)
                        removed_files.append(os.path.basename(file_path))
                    except Exception as e:
                        print(f"Warning: Could not remove file {file_path}: {e}")
        except Exception as e:
            print(f"Warning during photo cleanup: {e}")

        # Delete student and related attendance from MongoDB
        try:
            # Remove the student document
            student_result = collections['students'].delete_one({'roll_no': student_roll})
            # Remove attendance records referencing this student
            attendance_result = collections['attendance'].delete_many({'student.roll_no': student_roll})
        except Exception as e:
            print(f"Warning: Error deleting from database: {e}")
            student_result = type('obj', (), {'deleted_count': 0})()
            attendance_result = type('obj', (), {'deleted_count': 0})()

        # Build response
        return jsonify({
            'success': True,
            'message': (
                f"Deleted student {student_roll} everywhere. "
                f"Removed {total_removed} face entries across classes {classes_affected}. "
                f"Deleted {len(removed_files)} uploaded photo(s). "
                f"DB deletions - students: {getattr(student_result, 'deleted_count', 0)}, "
                f"attendance: {getattr(attendance_result, 'deleted_count', 0)}."
            ),
            'classes_affected': classes_affected,
            'removed_photos': removed_files,
            'removed_face_entries': total_removed,
            'db': {
                'students_deleted': getattr(student_result, 'deleted_count', 0),
                'attendance_deleted': getattr(attendance_result, 'deleted_count', 0)
            }
        })

    except Exception as e:
        print(f"General exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@bp.route('/edit_student_face', methods=['POST'])
def edit_student_face():
    """Edit student face registration data"""
    from flask import session

    print("Edit student face route called")
    faculty_email = session.get('faculty_email')
    print(f"Faculty email from session: {faculty_email}")

    if not faculty_email:
        print("No faculty email in session")
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    try:
        data = request.get_json()
        print(f"Edit request data: {data}")
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        old_roll_no = data.get('old_roll_no')
        old_class_name = data.get('old_class_name')
        new_name = data.get('new_name')
        new_roll_no = data.get('new_roll_no')
        new_branch = data.get('new_branch')
        new_semester = data.get('new_semester')
        new_section = data.get('new_section')

        print(f"Edit request - Old: {old_roll_no} in {old_class_name}, New: {new_name} ({new_roll_no}) in {new_branch}_{new_semester}")

        if not all([old_roll_no, old_class_name, new_name, new_roll_no, new_branch, new_semester, new_section]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        # Get collections and current app config
        collections = get_collections()
        split_dir = current_app.config['SPLIT_DIR']

        # Check if new roll number already exists in students collection
        existing_student = collections['students'].find_one({"roll_no": new_roll_no})
        if existing_student and existing_student['roll_no'] != old_roll_no:
            return jsonify({
                'success': False,
                'message': f'Student with roll number {new_roll_no} already exists'
            }), 400

        # Find and update the pickle file for the old class
        old_pickle_path = os.path.join(split_dir, f"{old_class_name}.pickle")
        print(f"Looking for old pickle file: {old_pickle_path}")
        print(f"Old file exists: {os.path.exists(old_pickle_path)}")

        if os.path.exists(old_pickle_path):
            try:
                with open(old_pickle_path, 'rb') as f:
                    data = pickle.load(f)

                # Find and update the student's data
                encodings = data.get('encodings', [])
                metadata = data.get('metadata', [])

                # Find the student to update
                student_found = False
                for i, meta in enumerate(metadata):
                    if meta.get('roll_no') == old_roll_no:
                        # Update metadata
                        metadata[i] = {
                            'roll_no': new_roll_no,
                            'name': new_name,
                            'semester': int(new_semester),
                            'branch': new_branch,
                            'section': new_section
                        }
                        student_found = True
                        print(f"Updated student at index {i}")
                        break

                if not student_found:
                    return jsonify({
                        'success': False,
                        'message': f'Student {old_roll_no} not found in class {old_class_name}'
                    }), 404

                # Update the pickle file
                data['metadata'] = metadata
                with open(old_pickle_path, 'wb') as f:
                    pickle.dump(data, f)

                print(f"Updated old pickle file: {old_pickle_path}")

                # Update student record in MongoDB
                update_result = collections['students'].update_one(
                    {"roll_no": old_roll_no},
                    {
                        "$set": {
                            "roll_no": new_roll_no,
                            "name": new_name,
                            "branch": new_branch,
                            "semester": int(new_semester),
                            "section": new_section
                        }
                    }
                )

                if update_result.modified_count > 0:
                    print(f"Updated student record in database")

                    # If class changed, we need to move data to new class file
                    new_class_name = f"{new_branch}_{new_semester}"
                    if new_class_name != old_class_name:
                        print(f"Class changed from {old_class_name} to {new_class_name}")
                        # Move data to new class file
                        new_pickle_path = os.path.join(split_dir, f"{new_class_name}.pickle")

                        if os.path.exists(new_pickle_path):
                            try:
                                with open(new_pickle_path, 'rb') as f:
                                    new_data = pickle.load(f)
                                new_encodings = new_data.get('encodings', [])
                                new_metadata = new_data.get('metadata', [])
                            except:
                                new_encodings = []
                                new_metadata = []
                        else:
                            new_encodings = []
                            new_metadata = []

                        # Add student to new class
                        new_encodings.append(encodings[i])  # Use the encoding from old file
                        new_metadata.append(metadata[i])

                        # Update new class file
                        new_data = {'encodings': new_encodings, 'metadata': new_metadata}
                        with open(new_pickle_path, 'wb') as f:
                            pickle.dump(new_data, f)

                        print(f"Added student to new class file: {new_pickle_path}")

                        # Remove from old class file (we already updated it above)
                        # The old file already has the student removed since we updated metadata

                    return jsonify({
                        'success': True,
                        'message': f'Successfully updated student information for {new_name} ({new_roll_no})'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': f'Failed to update student record in database'
                    }), 500

            except Exception as e:
                print(f"Exception in edit processing: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'message': f'Error updating face data: {str(e)}'
                }), 500
        else:
            return jsonify({
                'success': False,
                'message': f'No face registration data found for class {old_class_name}'
            }), 404

    except Exception as e:
        print(f"General exception in edit: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500