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
    return client[mongodb_db]


def ensure_student_passwords(default_password: str = '123456') -> dict:
    """Hash-set a default password for all students missing a proper bcrypt hash.

    A student is considered missing a password if the `password` field is absent
    or not stored as bytes (bcrypt hashes are bytes).
    """
    db = get_db()
    students = db['students']

    updated = 0
    skipped = 0
    default_hash = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt())

    for doc in students.find({}, {'_id': 1, 'password': 1}):
        pwd = doc.get('password')
        if isinstance(pwd, (bytes, bytearray)):
            skipped += 1
            continue
        students.update_one({'_id': doc['_id']}, {'$set': {'password': default_hash}})
        updated += 1

    return {'updated': updated, 'skipped': skipped}


if __name__ == '__main__':
    result = ensure_student_passwords('123456')
    print(f"Student password initialization complete. Updated: {result['updated']}, Skipped (already hashed): {result['skipped']}")


