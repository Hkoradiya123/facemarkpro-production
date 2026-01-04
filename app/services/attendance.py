from datetime import datetime, timedelta
from collections import defaultdict
from ..db.mongo_client import get_collections

class AttendanceService:
    """Service for attendance-related business logic"""
    
    def __init__(self):
        """Initialize the attendance service"""
        self.collections = get_collections()
    
    def mark_attendance(self, faculty_email, subject, classroom, branch, semester, section, 
                       student_roll_no, student_name, status, date_str=None):
        """
        Mark attendance for a student
        
        Args:
            faculty_email: Email of the faculty member
            subject: Subject name
            classroom: Classroom name
            branch: Student branch
            semester: Student semester
            section: Student section
            student_roll_no: Student roll number
            student_name: Student name
            status: Attendance status ('Present' or 'Absent')
            date_str: Date string (defaults to today)
            
        Returns:
            bool: True if attendance marked successfully
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        try:
            attendance_record = {
                'date': date_str,
                'subject': subject,
                'faculty_email': faculty_email,
                'classroom': classroom,
                'branch': branch,
                'semester': int(semester),
                'section': section,
                'student': {
                    'roll_no': student_roll_no,
                    'name': student_name,
                    'status': status
                }
            }
            
            self.collections['attendance'].insert_one(attendance_record)
            return True
        except Exception as e:
            print(f"Error marking attendance: {e}")
            return False
    
    def get_today_attendance(self, faculty_email, date_str=None):
        """
        Get today's attendance for a faculty member
        
        Args:
            faculty_email: Email of the faculty member
            date_str: Date string (defaults to today)
            
        Returns:
            dict: Attendance statistics
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        attendance_stats = {'Present': 0, 'Absent': 0}
        
        for status in attendance_stats.keys():
            count = self.collections['attendance'].count_documents({
                "date": date_str,
                "faculty_email": faculty_email,
                "student.status": status
            })
            attendance_stats[status] = count
        
        return attendance_stats
    
    def get_class_attendance(self, faculty_email, subject, branch, semester, section, date_str=None):
        """
        Get attendance for a specific class
        
        Args:
            faculty_email: Email of the faculty member
            subject: Subject name
            branch: Student branch
            semester: Student semester
            section: Student section
            date_str: Date string (defaults to today)
            
        Returns:
            int: Number of present students
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        query = {
            "date": date_str,
            "subject": subject,
            "branch": branch,
            "semester": int(semester),
            "section": section,
            "faculty_email": faculty_email,
            "student.status": "Present"
        }
        
        return self.collections['attendance'].count_documents(query)
    
    def get_monthly_trend(self, faculty_email, days=30):
        """
        Get monthly attendance trend for a faculty member
        
        Args:
            faculty_email: Email of the faculty member
            days: Number of days to look back
            
        Returns:
            dict: Daily attendance counts
        """
        today = datetime.now()
        start_date = today - timedelta(days=days)
        
        monthly_trend = defaultdict(int)
        
        for doc in self.collections['attendance'].find({"faculty_email": faculty_email}):
            try:
                doc_date = datetime.strptime(doc.get("date", ""), "%Y-%m-%d")
                if start_date <= doc_date <= today:
                    if doc.get("student", {}).get("status") == "Present":
                        monthly_trend[doc_date.strftime("%Y-%m-%d")] += 1
            except:
                continue
        
        return monthly_trend
    
    def get_subject_classroom_matrix(self, faculty_email):
        """
        Get attendance matrix by subject and classroom
        
        Args:
            faculty_email: Email of the faculty member
            
        Returns:
            dict: Matrix of attendance counts by subject and classroom
        """
        matrix = defaultdict(lambda: defaultdict(int))
        
        for doc in self.collections['attendance'].find({"faculty_email": faculty_email}):
            subject = doc.get("subject", "?")
            classroom = doc.get("classroom", "?")
            if doc.get("student", {}).get("status") == "Present":
                matrix[subject][classroom] += 1
        
        return matrix
    
    def get_students_for_class(self, branch, semester, section):
        """
        Get all students for a specific class
        
        Args:
            branch: Student branch
            semester: Student semester
            section: Student section
            
        Returns:
            list: List of student dictionaries
        """
        students = []
        students_cursor = self.collections['students'].find({
            "branch": branch,
            "semester": int(semester),
            "section": section
        })
        
        for student in students_cursor:
            students.append({
                "roll_no": student.get("roll_no"),
                "name": student.get("name"),
                "branch": branch,
                "semester": semester,
                "section": section
            })
        
        return students
    
    def mark_bulk_attendance(self, faculty_email, subject, classroom, branch, semester, section, 
                           present_roll_numbers, date_str=None):
        """
        Mark attendance for multiple students at once
        
        Args:
            faculty_email: Email of the faculty member
            subject: Subject name
            classroom: Classroom name
            branch: Student branch
            semester: Student semester
            section: Student section
            present_roll_numbers: List of present student roll numbers
            date_str: Date string (defaults to today)
            
        Returns:
            int: Number of attendance records created
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Get all students for this class
        students = self.get_students_for_class(branch, semester, section)
        roll_name_map = {s['roll_no']: s['name'] for s in students}
        
        created_count = 0
        
        for student in students:
            roll_no = student['roll_no']
            name = student['name']
            status = 'Present' if roll_no in present_roll_numbers else 'Absent'
            
            success = self.mark_attendance(
                faculty_email, subject, classroom, branch, semester, section,
                roll_no, name, status, date_str
            )
            
            if success:
                created_count += 1
        
        return created_count 