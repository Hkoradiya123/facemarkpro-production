import os
import pickle
import glob
import numpy as np
from werkzeug.utils import secure_filename

def ensure_directory(directory_path):
    """Ensure a directory exists, create if it doesn't"""
    os.makedirs(directory_path, exist_ok=True)

def save_encodings(encodings, metadata, file_path):
    """Save face encodings and metadata to a pickle file"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        data = {'encodings': encodings, 'metadata': metadata}
        with open(file_path, 'wb') as f:
            pickle.dump(data, f)
        return True
    except Exception as e:
        print(f"Error saving encodings: {e}")
        return False

def load_encodings(file_path):
    """Load face encodings and metadata from a pickle file"""
    try:
        if not os.path.exists(file_path):
            return None, None
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
        return data.get('encodings', []), data.get('metadata', [])
    except (ModuleNotFoundError, ImportError, ValueError) as e:
        print(f"Error loading encodings due to numpy version incompatibility: {e}")
        return None, None
    except Exception as e:
        print(f"Error loading encodings: {e}")
        return None, None 