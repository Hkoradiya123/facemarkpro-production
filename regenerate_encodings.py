#!/usr/bin/env python3
"""
Script to regenerate face encoding files with current numpy version
This fixes the 'numpy._core' compatibility issue
"""

import os
import pickle
import numpy as np
from app.services.face_recognition import FaceRecognitionService
import cv2
from werkzeug.utils import secure_filename

def regenerate_encodings():
    """Regenerate all encoding files with current numpy version"""
    
    # Initialize face recognition service
    print("Initializing face recognition service...")
    face_service = FaceRecognitionService()
    
    # Get all pickle files in split_encodings directory
    split_dir = "split_encodings"
    if not os.path.exists(split_dir):
        print(f"Directory {split_dir} not found. Nothing to regenerate.")
        return
    
    pickle_files = [f for f in os.listdir(split_dir) if f.endswith('.pickle')]
    
    if not pickle_files:
        print("No pickle files found to regenerate.")
        return
    
    print(f"Found {len(pickle_files)} pickle files to regenerate:")
    
    for pickle_file in pickle_files:
        file_path = os.path.join(split_dir, pickle_file)
        print(f"\nProcessing: {pickle_file}")
        
        try:
            # Try to load the old file
            with open(file_path, 'rb') as f:
                old_data = pickle.load(f)
            
            # Extract encodings and metadata
            old_encodings = old_data.get('encodings', [])
            old_metadata = old_data.get('metadata', [])
            
            print(f"  - Found {len(old_encodings)} encodings")
            
            # Convert to current numpy format
            new_encodings = []
            for encoding in old_encodings:
                if isinstance(encoding, np.ndarray):
                    new_encodings.append(encoding.copy())
                else:
                    new_encodings.append(np.array(encoding))
            
            # Create new data structure
            new_data = {
                'encodings': new_encodings,
                'metadata': old_metadata
            }
            
            # Save with current numpy version
            with open(file_path, 'wb') as f:
                pickle.dump(new_data, f)
            
            print(f"  ✓ Successfully regenerated {pickle_file}")
            
        except (ModuleNotFoundError, ImportError, ValueError) as e:
            print(f"  ✗ Error loading {pickle_file}: {e}")
            print(f"    This file will be skipped. You may need to re-register students for this class.")
        except Exception as e:
            print(f"  ✗ Unexpected error with {pickle_file}: {e}")
    
    print(f"\nRegeneration complete!")

if __name__ == "__main__":
    print("Face Encoding Regeneration Tool")
    print("=" * 40)
    regenerate_encodings() 