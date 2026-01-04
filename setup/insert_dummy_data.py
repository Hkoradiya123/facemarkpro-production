from pymongo import MongoClient
import bcrypt
import pandas as pd

def insert_dummy_data():
    """Insert dummy data for testing the application"""
    
    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client["attendance_db"]
    
    # Insert dummy faculty users
    faculty_collection = db["faculty"]
    
    # Hash passwords
    password = "password123"
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    faculty_users = [
        {
            "email": "faculty1@example.com",
            "password": hashed_password,
            "name": "Dr. John Smith",
            "role": "teacher"
        },
        {
            "email": "faculty2@example.com", 
            "password": hashed_password,
            "name": "Prof. Jane Doe",
            "role": "teacher"
        }
    ]
    
    for faculty in faculty_users:
        faculty_collection.update_one(
            {"email": faculty["email"]},
            {"$set": faculty},
            upsert=True
        )
    
    print("Dummy faculty users inserted")
    
    # Insert dummy students
    students_collection = db["students"]
    
    dummy_students = [
        {"roll_no": "001", "name": "Alice Johnson", "branch": "CSE", "semester": 3, "section": "A"},
        {"roll_no": "002", "name": "Bob Smith", "branch": "CSE", "semester": 3, "section": "A"},
        {"roll_no": "003", "name": "Charlie Brown", "branch": "CE", "semester": 5, "section": "A"},
        {"roll_no": "004", "name": "Diana Prince", "branch": "CE", "semester": 5, "section": "A"},
        {"roll_no": "005", "name": "Eve Wilson", "branch": "CSE", "semester": 5, "section": "A"}
    ]
    
    for student in dummy_students:
        students_collection.update_one(
            {"roll_no": student["roll_no"]},
            {"$set": student},
            upsert=True
        )
    
    print("Dummy students inserted")
    
    # Create dummy timetable
    timetable_data = [
        {"day": "Monday", "start_time": "09:00", "end_time": "10:00", "subject": "Python", "branch": "CSE", "semester": 3, "section": "A", "classroom": "Lab 101", "faculty_name": "Dr. John Smith"},
        {"day": "Monday", "start_time": "10:00", "end_time": "11:00", "subject": "DBMS", "branch": "CSE", "semester": 5, "section": "A", "classroom": "Lab 102", "faculty_name": "Prof. Jane Doe"},
        {"day": "Tuesday", "start_time": "09:00", "end_time": "10:00", "subject": "Data Structures", "branch": "CSE", "semester": 3, "section": "A", "classroom": "Lab 101", "faculty_name": "Dr. John Smith"},
        {"day": "Tuesday", "start_time": "10:00", "end_time": "11:00", "subject": "Computer Networks", "branch": "CSE", "semester": 5, "section": "A", "classroom": "Lab 102", "faculty_name": "Prof. Jane Doe"}
    ]
    
    timetable_df = pd.DataFrame(timetable_data)
    timetable_df.to_csv("timetable.csv", index=False)
    print("Dummy timetable created")
    
    # Create dummy faculty users CSV
    faculty_csv_data = [
        {"faculty_email": "faculty1@example.com", "faculty_name": "Dr. John Smith"},
        {"faculty_email": "faculty2@example.com", "faculty_name": "Prof. Jane Doe"}
    ]
    
    faculty_df = pd.DataFrame(faculty_csv_data)
    faculty_df.to_csv("faculty_users.csv", index=False)
    print("Dummy faculty users CSV created")
    
    print("Dummy data insertion completed!")

if __name__ == "__main__":
    insert_dummy_data() 