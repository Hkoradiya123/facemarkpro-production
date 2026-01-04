from insightface.app import FaceAnalysis
import numpy as np
import cv2
import os

class FaceRecognitionService:
    """Service for face detection and recognition using InsightFace"""
    
    def __init__(self):
        """Initialize the face recognition service"""
        self.face_app = None
        self._initialize_face_app()
    
    def _initialize_face_app(self):
        """Initialize the InsightFace application"""
        try:
            # Get model name from environment variable
            model_name = os.environ.get('FACE_RECOGNITION_MODEL', "buffalo_l")
            self.face_app = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
            self.face_app.prepare(ctx_id=0)
        except Exception as e:
            print(f"Error initializing face recognition: {e}")
            raise
    
    def get_faces(self, image):
        """
        Detect faces in an image and return face embeddings
        
        Args:
            image: RGB numpy array of the image
            
        Returns:
            List of detected faces with embeddings
        """
        if self.face_app is None:
            self._initialize_face_app()
        
        try:
            faces = self.face_app.get(image)
            return faces
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return []
    
    def get_face_embedding(self, image):
        """
        Get face embedding from an image
        
        Args:
            image: RGB numpy array of the image
            
        Returns:
            Face embedding as numpy array or None if no face detected
        """
        faces = self.get_faces(image)
        if faces:
            return faces[0].normed_embedding
        return None
    
    def compare_faces(self, known_encodings, face_encoding, tolerance=None):
        """
        Compare a face encoding with known encodings
        
        Args:
            known_encodings: List of known face encodings
            face_encoding: Face encoding to compare
            tolerance: Distance threshold for matching (uses env var if None)
            
        Returns:
            List of boolean values indicating matches
        """
        if not known_encodings or face_encoding is None:
            return []
        
        # Get tolerance from environment variable if not provided
        if tolerance is None:
            tolerance = float(os.environ.get('FACE_RECOGNITION_TOLERANCE', 0.85))
        
        known_encodings = np.array(known_encodings)
        distances = np.linalg.norm(known_encodings - face_encoding, axis=1)
        return distances < tolerance
    
    def find_matching_face(self, known_encodings, known_metadata, face_encoding, tolerance=None):
        """
        Find the best matching face from known encodings
        
        Args:
            known_encodings: List of known face encodings
            known_metadata: List of metadata corresponding to known encodings
            face_encoding: Face encoding to match
            tolerance: Distance threshold for matching (uses env var if None)
            
        Returns:
            Tuple of (matched_metadata, distance) or (None, None) if no match
        """
        if not known_encodings or face_encoding is None:
            return None, None
        
        # Get tolerance from environment variable if not provided
        if tolerance is None:
            tolerance = float(os.environ.get('FACE_RECOGNITION_TOLERANCE', 0.85))
        
        known_encodings = np.array(known_encodings)
        distances = np.linalg.norm(known_encodings - face_encoding, axis=1)
        min_idx = np.argmin(distances)
        min_distance = distances[min_idx]
        
        if min_distance < tolerance:
            return known_metadata[min_idx], min_distance
        
        return None, None 