import pandas as pd
from datetime import datetime
from ..db.mongo_client import get_collections

class TimetableService:
    """Service for timetable-related operations"""
    
    def __init__(self, timetable_file='timetable.csv'):
        """Initialize the timetable service"""
        self.timetable_file = timetable_file
        self.collections = get_collections()
    
    def load_timetable(self):
        """Load timetable from CSV file"""
        try:
            df = pd.read_csv(self.timetable_file)
            return df
        except Exception as e:
            print(f"Error loading timetable: {e}")
            return pd.DataFrame()
    
    def get_faculty_timetable(self, faculty_name):
        """
        Get timetable for a specific faculty member
        
        Args:
            faculty_name: Name of the faculty member
            
        Returns:
            DataFrame: Faculty's timetable
        """
        df = self.load_timetable()
        if df.empty:
            return df
        
        df['faculty_name'] = df['faculty_name'].str.strip().str.lower()
        faculty_df = df[df['faculty_name'] == faculty_name.strip().lower()]
        return faculty_df
    
    def get_today_lectures(self, faculty_name):
        """
        Get today's lectures for a faculty member
        
        Args:
            faculty_name: Name of the faculty member
            
        Returns:
            list: List of today's lectures
        """
        faculty_df = self.get_faculty_timetable(faculty_name)
        if faculty_df.empty:
            return []
        
        today = datetime.now().strftime('%A')
        today_lectures = faculty_df[faculty_df['day'] == today]
        return today_lectures.to_dict(orient='records')
    
    def get_lecture_status(self, lecture):
        """
        Get the status of a lecture (current, upcoming, past)
        
        Args:
            lecture: Lecture dictionary with start_time and end_time
            
        Returns:
            str: Status of the lecture
        """
        try:
            start = datetime.strptime(lecture['start_time'], "%H:%M").time()
            end = datetime.strptime(lecture['end_time'], "%H:%M").time()
            now = datetime.now().time()
            
            if start <= now <= end:
                return 'current'
            elif now < start:
                return 'upcoming'
            else:
                return 'past'
        except:
            return 'past'
    
    def get_current_lecture(self, faculty_name):
        """
        Get the current lecture for a faculty member
        
        Args:
            faculty_name: Name of the faculty member
            
        Returns:
            dict: Current lecture or None
        """
        today_lectures = self.get_today_lectures(faculty_name)
        now = datetime.now().time()
        
        for lecture in today_lectures:
            try:
                start = datetime.strptime(lecture['start_time'], "%H:%M").time()
                end = datetime.strptime(lecture['end_time'], "%H:%M").time()
                if start <= now <= end:
                    return lecture
            except:
                continue
        
        return None
    
    def get_next_lecture(self, faculty_name):
        """
        Get the next lecture for a faculty member
        
        Args:
            faculty_name: Name of the faculty member
            
        Returns:
            dict: Next lecture or None
        """
        today_lectures = self.get_today_lectures(faculty_name)
        now = datetime.now().time()
        
        # Sort lectures by start time
        def parse_time(t):
            try:
                return datetime.strptime(t, '%H:%M').time()
            except:
                return datetime.min.time()
        
        today_lectures_sorted = sorted(today_lectures, key=lambda x: parse_time(x['start_time']))
        
        for lecture in today_lectures_sorted:
            try:
                start = parse_time(lecture['start_time'])
                if now < start:
                    return lecture
            except:
                continue
        
        return None
    
    def get_upcoming_lectures(self, faculty_name, limit=5):
        """
        Get upcoming lectures for a faculty member
        
        Args:
            faculty_name: Name of the faculty member
            limit: Maximum number of upcoming lectures to return
            
        Returns:
            list: List of upcoming lectures
        """
        today_lectures = self.get_today_lectures(faculty_name)
        now = datetime.now().time()
        
        # Sort lectures by start time
        def parse_time(t):
            try:
                return datetime.strptime(t, '%H:%M').time()
            except:
                return datetime.min.time()
        
        today_lectures_sorted = sorted(today_lectures, key=lambda x: parse_time(x['start_time']))
        upcoming = []
        
        for lecture in today_lectures_sorted:
            try:
                start = parse_time(lecture['start_time'])
                if now < start and len(upcoming) < limit:
                    upcoming.append(lecture)
            except:
                continue
        
        return upcoming
    
    def validate_lecture_time(self, faculty_name, subject, branch, semester, section):
        """
        Validate if a lecture exists and is currently active
        
        Args:
            faculty_name: Name of the faculty member
            subject: Subject name
            branch: Student branch
            semester: Student semester
            section: Student section
            
        Returns:
            dict: Lecture info if valid, None otherwise
        """
        faculty_df = self.get_faculty_timetable(faculty_name)
        if faculty_df.empty:
            return None
        
        # Filter by lecture details
        lecture_row = faculty_df[
            (faculty_df['subject'] == subject) &
            (faculty_df['branch'] == branch) &
            (faculty_df['semester'].astype(str) == str(semester)) &
            (faculty_df['section'] == section)
        ]
        
        if lecture_row.empty:
            return None
        
        lecture = lecture_row.iloc[0].to_dict()
        status = self.get_lecture_status(lecture)
        
        if status == 'current':
            return lecture
        
        return None
    
    def get_class_id(self, branch, semester):
        """
        Generate class ID for encoding files
        
        Args:
            branch: Student branch
            semester: Student semester
            
        Returns:
            str: Class ID
        """
        return f"{branch}_{semester}"
    
    def get_all_classes(self, faculty_name):
        """
        Get all classes taught by a faculty member
        
        Args:
            faculty_name: Name of the faculty member
            
        Returns:
            list: List of unique class tuples (branch, semester, section)
        """
        faculty_df = self.get_faculty_timetable(faculty_name)
        if faculty_df.empty:
            return []
        
        # Get unique class combinations
        class_tuples = faculty_df[['branch', 'semester', 'section']].drop_duplicates().to_records(index=False)
        return list(class_tuples) 