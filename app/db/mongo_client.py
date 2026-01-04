from pymongo import MongoClient
import os

client = None
db = None
attendance_col = None
students_col = None
users_collection = None

def init_mongo_client(app):
    global client, db, attendance_col, students_col, users_collection
    
    mongodb_uri = os.environ.get('MONGO_URI')
    mongodb_db = os.environ.get('MONGODB_DB', 'attendance_db')

    if not mongodb_uri:
        raise ValueError("Please set MONGO_URI environment variable for MongoDB Atlas")

    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    attendance_col = db["attendance"]
    students_col = db["students"]
    users_collection = db["faculty"]

    app.mongo_client = client
    app.db = db
    app.attendance_col = attendance_col
    app.students_col = students_col
    app.users_collection = users_collection

def get_collections():
    if client is None:
        raise ValueError("Mongo client not initialized. Call init_mongo_client(app) first.")
    return {
        "faculty": db["faculty"],
        "students": db["students"],
        "attendance": db["attendance"],
        "users": db["users"],
        "timetable": db["timetable"]
    }
