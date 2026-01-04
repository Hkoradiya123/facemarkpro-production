from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app
import bcrypt
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from ..db.mongo_client import get_collections
from dotenv import load_dotenv
import os

load_dotenv()  # Loads variables from .env

from flask import Flask
from app.db.mongo_client import init_mongo_client

app = Flask(__name__)

# Initialize MongoDB client
init_mongo_client(app)

bp = Blueprint('faculty', __name__)

# --------------------------------------------------------------------
# FACULTY INFO EDIT
# --------------------------------------------------------------------
@bp.route('/edit-faculty-info', methods=['POST'])
def edit_faculty_info():
    """Edit faculty info: phone, qualification, address, with password confirmation"""
    collections = get_collections()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    phone = request.form.get('phone', '')
    qualification = request.form.get('qualification', '')
    address = request.form.get('address', '')

    # 🔧 Changed from 'users' → 'faculty'
    user = collections['faculty'].find_one({"email": email})
    if not user:
        flash("Faculty not found.", "error")
        return redirect('/profile')

    # Verify password
    if not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        flash("Password incorrect.", "error")
        return redirect('/profile')

    update_fields = {}
    if phone:
        update_fields['phone'] = phone
    if qualification:
        update_fields['qualification'] = qualification
    if address:
        update_fields['address'] = address

    if update_fields:
        collections['faculty'].update_one({"email": email}, {"$set": update_fields})
        flash("Faculty info updated successfully.", "success")
    else:
        flash("No changes submitted.", "info")
    return redirect('/profile')


# --------------------------------------------------------------------
# LOGIN / LOGOUT / HOME
# --------------------------------------------------------------------
@bp.route('/')
def home():
    """Home route - redirect to dashboard if logged in, otherwise to login"""
    if 'faculty_email' in session:
        return redirect('/dashboard')
    return redirect('/multilogin')


@bp.route('/multilogin')
def multilogin():
    """Multi-login page"""
    if 'faculty_email' in session:
        return redirect('/dashboard')
    return render_template('multilogin.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Unified faculty login"""
    role = request.args.get('role', 'teacher')

    if request.method == 'GET':
        return redirect('/multilogin')

    collections = get_collections()
    email = request.form.get('faculty_email', '').strip().lower()
    password = request.form.get('password', '')

    if not email or not password:
        flash("Please enter both email and password.", "error")
        return redirect('/multilogin')

    # 🔧 Changed from 'users' → 'faculty'
    user = collections['faculty'].find_one({"email": email})
    if not user:
        flash("Invalid email or password.", "error")
        return redirect('/multilogin')

    hashed_password = user.get('password')
    if not bcrypt.checkpw(password.encode('utf-8'), hashed_password):
        flash("Invalid email or password.", "error")
        return redirect('/multilogin')

    session['faculty_email'] = email
    session['role'] = user.get('role', role)
    session['faculty_name'] = user.get('name', 'Faculty')

    return redirect('/dashboard')


@bp.route('/logout')
def logout():
    """Logout faculty"""
    session.clear()
    return redirect('/multilogin')


# --------------------------------------------------------------------
# PROFILE PAGE
# --------------------------------------------------------------------
@bp.route('/profile')
def profile():
    """Faculty profile page"""
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return redirect('/multilogin')

    collections = get_collections()
    
    # Use the 'faculty' collection, not 'users'
    user = collections['faculty'].find_one({'email': faculty_email})
    if not user:
        flash("Faculty not found.", "error")
        return redirect('/multilogin')

    faculty_name = user.get('name', 'Faculty')
    role = user.get('role', 'Faculty')
    department = user.get('department', 'N/A')
    faculty_id = user.get('faculty_id', 'N/A')
    phone = user.get('phone', 'N/A')
    joined_date = user.get('joined_date', 'N/A')
    qualification = user.get('qualification', 'N/A')
    address = user.get('address', 'N/A')

    return render_template(
        'faculty_profile.html',
        faculty_name=faculty_name,
        faculty_email=faculty_email,
        role=role,
        department=department,
        faculty_id=faculty_id,
        phone=phone,
        joined_date=joined_date,
        qualification=qualification,
        address=address
    )

# --------------------------------------------------------------------
# DASHBOARD PAGE (unchanged except collection fix)
# --------------------------------------------------------------------
@bp.route('/dashboard')
def dashboard():
    """Faculty dashboard with timetable and attendance stats"""
    faculty_email = session.get('faculty_email')
    if not faculty_email:
        return redirect('/multilogin')

    faculty_map = pd.read_csv('faculty_users.csv')
    faculty_map['faculty_email'] = faculty_map['faculty_email'].str.strip().str.lower()
    faculty_map['faculty_name'] = faculty_map['faculty_name'].str.strip().str.lower()
    faculty_row = faculty_map[faculty_map['faculty_email'] == faculty_email.strip().lower()]
    if faculty_row.empty:
        flash("Faculty not found.", "error")
        return redirect('/multilogin')

    faculty_name = faculty_row.iloc[0]['faculty_name']

    df = pd.read_csv('timetable.csv')
    df['faculty_name'] = df['faculty_name'].str.strip().str.lower()
    faculty_df = df[df['faculty_name'] == faculty_name]

    def get_status(row):
        try:
            start = datetime.strptime(row['start_time'], "%H:%M").time()
            end = datetime.strptime(row['end_time'], "%H:%M").time()
            now = datetime.now().time()
            if start <= now <= end:
                return 'current'
            elif now < start:
                return 'upcoming'
            else:
                return 'past'
        except:
            return 'past'

    faculty_df = faculty_df.copy()
    faculty_df['status'] = faculty_df.apply(get_status, axis=1)
    lectures = faculty_df.to_dict(orient='records')

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    time_slots = sorted(df['start_time'].unique(), key=lambda x: datetime.strptime(x, "%H:%M"))
    timetable = {(row['day'], row['start_time']): {'subject': row['subject'], 'classroom': row['classroom']} for _, row in faculty_df.iterrows()}

    today_str = datetime.now().strftime('%Y-%m-%d')
    collections = get_collections()
    class_attendance = defaultdict(int)
    for _, row in faculty_df.iterrows():
        query = {
            "date": today_str,
            "subject": row['subject'],
            "branch": row['branch'],
            "semester": row['semester'],
            "section": row['section'],
            "faculty_email": faculty_email,
            "student.status": "Present"
        }
        count = collections['attendance'].count_documents(query)
        class_attendance[f"{row['branch']}-{row['semester']}-{row['section']}"] += count

    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)
    monthly_trend = defaultdict(int)
    for doc in collections['attendance'].find({"faculty_email": faculty_email}):
        try:
            doc_date = datetime.strptime(doc.get("date", ""), "%Y-%m-%d")
            if thirty_days_ago <= doc_date <= today:
                if doc.get("student", {}).get("status") == "Present":
                    monthly_trend[doc_date.strftime("%Y-%m-%d")] += 1
        except:
            continue
    monthly_labels = sorted(monthly_trend.keys())
    monthly_data = [monthly_trend[date] for date in monthly_labels]

    matrix = defaultdict(lambda: defaultdict(int))
    for doc in collections['attendance'].find({"faculty_email": faculty_email}):
        subject = doc.get("subject", "?")
        classroom = doc.get("classroom", "?")
        if doc.get("student", {}).get("status") == "Present":
            matrix[subject][classroom] += 1

    bar_labels = sorted(matrix.keys())
    classroom_list = sorted(set(cls for subj in matrix.values() for cls in subj))
    bar_data = {cls: [matrix[subj].get(cls, 0) for subj in bar_labels] for cls in classroom_list}

    subject_labels = bar_labels
    classroom_labels = classroom_list
    heatmap_data = [
        {"x": j, "y": i, "v": matrix[subj].get(cls, 0)}
        for i, subj in enumerate(subject_labels)
        for j, cls in enumerate(classroom_labels)
    ]

    # --- Today's lecture logic ---
    now = datetime.now().time()
    today = datetime.now().strftime('%A')
    today_lectures = [lec for lec in lectures if lec.get('day') == today]

    def parse_time(t):
        try:
            return datetime.strptime(t, '%H:%M').time()
        except:
            return datetime.min.time()

    today_lectures_sorted = sorted(today_lectures, key=lambda x: parse_time(x['start_time']))
    current_lecture, next_lecture, upcoming_lectures = None, None, []
    for lec in today_lectures_sorted:
        start = parse_time(lec['start_time'])
        end = parse_time(lec['end_time'])
        if start <= now <= end:
            current_lecture = lec
        elif now < start:
            if not next_lecture:
                next_lecture = lec
            else:
                upcoming_lectures.append(lec)

    attendance_stats = {'Present': 0, 'Absent': 0}
    for status in attendance_stats.keys():
        count = collections['attendance'].count_documents({
            "date": today_str,
            "faculty_email": faculty_email,
            "student.status": status
        })
        attendance_stats[status] = count

    students_list = []
    for branch, semester, section in faculty_df[['branch', 'semester', 'section']].drop_duplicates().to_records(index=False):
        students_cursor = collections['students'].find({
            "branch": branch,
            "semester": int(semester),
            "section": section
        })
        for s in students_cursor:
            students_list.append({
                "roll_no": str(s.get("roll_no")) if s.get("roll_no") else "",
                "name": str(s.get("name")) if s.get("name") else "",
                "branch": str(branch),
                "semester": int(semester),
                "section": str(section)
            })

    return render_template(
        'dashboard.html',
        faculty=faculty_name,
        lectures=lectures,
        days=days,
        time_slots=time_slots,
        timetable=timetable,
        class_attendance=class_attendance,
        monthly_labels=monthly_labels,
        monthly_data=monthly_data,
        bar_labels=bar_labels,
        classroom_list=classroom_list,
        bar_data=bar_data,
        heatmap_data=heatmap_data,
        subject_labels=subject_labels,
        classroom_labels=classroom_labels,
        current_lecture=current_lecture,
        next_lecture=next_lecture,
        upcoming_lectures=upcoming_lectures,
        attendance_stats=attendance_stats,
        students_list=students_list
    )


# --------------------------------------------------------------------
# CHANGE PASSWORD
# --------------------------------------------------------------------
@bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Change faculty password"""
    collections = get_collections()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')

        # 🔧 Changed from 'users' → 'faculty'
        user = collections['faculty'].find_one({"email": email})
        if not user or not bcrypt.checkpw(current_password.encode('utf-8'), user['password']):
            flash("Current password incorrect.", "error")
            return redirect('/profile')

        new_hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        collections['faculty'].update_one({"email": email}, {"$set": {"password": new_hashed}})

        session.clear()
        flash("Password changed successfully. Please log in again.", "success")
        return redirect('/login')

    return render_template("faculty_profile.html")
