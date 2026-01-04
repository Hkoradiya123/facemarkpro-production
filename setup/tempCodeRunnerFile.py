import os
from pymongo import MongoClient
import bcrypt
from dotenv import load_dotenv


def get_db():
    """Create a direct MongoDB client using env vars, defaulting to localhost."""
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'attendance_db')
    client = MongoClient(mongodb_uri)