# Facial Recognition Attendance System

A modern, scalable facial recognition attendance system built with Flask, MongoDB, and InsightFace.

## Features

- **Real-time Face Recognition**: Live attendance tracking using webcam
- **Video Upload**: Process pre-recorded videos for attendance
- **Manual Attendance**: Traditional manual attendance marking
- **Faculty Dashboard**: Comprehensive dashboard with attendance analytics
- **Student Management**: Register and manage student information
- **Timetable Integration**: Automatic lecture scheduling and validation
- **Multi-class Support**: Handle multiple classes and subjects
- **Secure Authentication**: Faculty login with password hashing

## Project Structure

```
facial_attendance_system/
│
├── app/                         # All app logic lives here
│   ├── routes/                  # Flask routes
│   │   ├── __init__.py
│   │   ├── student_routes.py    # Student registration, list
│   │   ├── faculty_routes.py    # Faculty dashboard & timetable
│   │   └── attendance_routes.py # Marking/viewing attendance
│   │
│   ├── services/                # Business logic
│   │   ├── __init__.py
│   │   ├── face_recognition.py  # Face detection + embeddings
│   │   ├── attendance.py        # Attendance logic
│   │   └── timetable.py         # Timetable validation logic
│   │
│   ├── db/                      # MongoDB connection & queries
│   │   ├── __init__.py
│   │   ├── mongo_client.py      # MongoDB client init
│   │   ├── student_collection.py
│   │   ├── attendance_collection.py
│   │   └── timetable_collection.py
│   │
│   ├── utils/                   # Helper functions
│   │   ├── __init__.py
│   │   ├── camera_utils.py
│   │   └── file_utils.py
│   │
│   ├── templates/               # HTML files (for Flask Jinja)
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── register_student.html
│   │   └── view_attendance.html
│   │
│   ├── static/                  # CSS, JS, images
│   │   ├── css/
│   │   ├── js/
│   │   └── uploads/             # Student photos
│   │
│   └── __init__.py              # Flask app factory
│
├── encodings/                   # Face encodings (optional if not in DB)
│   └── face_encodings.pickle
│
├── tests/                       # Unit tests
│   └── test_face_recognition.py
│
├── setup/                       # Initial setup scripts
│   ├── insert_dummy_data.py     # Load sample students/timetable
│   └── setup_models.py          # InsightFace model init
│
├── .env                         # Secret keys & DB config
├── requirements.txt
├── run.py                       # Entry point to start Flask app
└── README.md
```

## Installation

### Prerequisites

- Python 3.8+
- MongoDB
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd facial_attendance_system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup MongoDB**
   - Install MongoDB if not already installed
   - Start MongoDB service
   - Create database `attendance_db`

5. **Setup InsightFace models**
   ```bash
   python setup/setup_models.py
   ```

6. **Insert dummy data (optional)**
   ```bash
   python setup/insert_dummy_data.py
   ```

7. **Run the application**
   ```bash
   python run.py
   ```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your_secret_key_here

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=attendance_db

# File Paths
UPLOAD_FOLDER=dataset
ENCODING_FILE=encodings/face_encodings.pickle
TIMETABLE_FILE=timetable.csv
ATTENDANCE_DIR=attendance_logs
SPLIT_DIR=split_encodings

# Face Recognition Configuration
FACE_RECOGNITION_TOLERANCE=0.85
FACE_RECOGNITION_MODEL=buffalo_l
```

## Usage

### Faculty Login

1. Access the application at `http://localhost:5000`
2. Login with faculty credentials
3. Navigate to dashboard

### Student Registration

1. Go to Students → Register Face
2. Select branch and semester
3. Upload 3 face photos
4. System will generate face encodings

### Marking Attendance

#### Live Attendance
1. Go to Attendance → Live Attendance
2. Select class
3. Start session
4. Students will be recognized automatically

#### Video Upload
1. Go to Attendance → Video Upload
2. Select class and upload video
3. System processes video and marks attendance

#### Manual Attendance
1. Go to Attendance → Manual Attendance
2. Select lecture
3. Mark present/absent students
4. Submit attendance

## API Endpoints

### Faculty Routes
- `GET /faculty/` - Home redirect
- `GET /faculty/multilogin` - Multi-login page
- `GET/POST /faculty/login` - Faculty login
- `GET /faculty/dashboard` - Faculty dashboard
- `GET /faculty/logout` - Logout
- `GET/POST /faculty/change-password` - Change password

### Student Routes
- `GET /students/` - List students
- `GET/POST /students/register_face` - Register student face

### Attendance Routes
- `GET /attendance/` - Attendance page
- `POST /attendance/upload` - Upload video for attendance
- `GET /attendance/manual` - Manual attendance
- `POST /attendance/manual/select_students` - Select students for manual attendance
- `POST /attendance/manual/submit` - Submit manual attendance
- `POST /attendance/live_frame` - Process live frame
- `POST /attendance/live_submit` - Submit live attendance
- `GET /attendance/model_status` - Check model status
- `POST /attendance/start_session` - Start live session
- `POST /attendance/process_frame` - Process frame in session
- `GET /attendance/poll_session` - Poll session status
- `POST /attendance/stop_session` - Stop live session

## Database Schema

### Collections

#### faculty
```json
{
  "email": "faculty@example.com",
  "password": "hashed_password",
  "name": "Faculty Name",
  "role": "teacher"
}
```

#### students
```json
{
  "roll_no": "001",
  "name": "Student Name",
  "branch": "CSE",
  "semester": 3,
  "section": "A"
}
```

#### attendance
```json
{
  "date": "2024-01-15",
  "subject": "Python",
  "faculty_email": "faculty@example.com",
  "classroom": "Lab 101",
  "branch": "CSE",
  "semester": 3,
  "section": "A",
  "student": {
    "roll_no": "001",
    "name": "Student Name",
    "status": "Present"
  }
}
```

## Testing

Run unit tests:
```bash
python -m unittest tests/test_face_recognition.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please open an issue on GitHub. 