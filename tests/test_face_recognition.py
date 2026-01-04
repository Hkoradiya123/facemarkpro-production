import unittest
import numpy as np
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from services.face_recognition import FaceRecognitionService

class TestFaceRecognition(unittest.TestCase):
    """Test cases for face recognition functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.face_service = FaceRecognitionService()
    
    def test_face_service_initialization(self):
        """Test that face service initializes correctly"""
        self.assertIsNotNone(self.face_service.face_app)
    
    def test_get_faces_empty_image(self):
        """Test face detection on empty image"""
        # Create a blank image
        blank_image = np.zeros((100, 100, 3), dtype=np.uint8)
        faces = self.face_service.get_faces(blank_image)
        self.assertEqual(len(faces), 0)
    
    def test_get_faces_random_image(self):
        """Test face detection on random image"""
        # Create a random image
        random_image = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        faces = self.face_service.get_faces(random_image)
        # Should not crash, may or may not find faces
        self.assertIsInstance(faces, list)
    
    def test_compare_faces_empty(self):
        """Test face comparison with empty encodings"""
        known_encodings = []
        face_encoding = np.random.rand(512)
        result = self.face_service.compare_faces(known_encodings, face_encoding)
        self.assertEqual(len(result), 0)
    
    def test_compare_faces_none_encoding(self):
        """Test face comparison with None encoding"""
        known_encodings = [np.random.rand(512)]
        result = self.face_service.compare_faces(known_encodings, None)
        self.assertEqual(len(result), 0)
    
    def test_find_matching_face_empty(self):
        """Test finding matching face with empty data"""
        known_encodings = []
        known_metadata = []
        face_encoding = np.random.rand(512)
        result, distance = self.face_service.find_matching_face(known_encodings, known_metadata, face_encoding)
        self.assertIsNone(result)
        self.assertIsNone(distance)
    
    def test_find_matching_face_none_encoding(self):
        """Test finding matching face with None encoding"""
        known_encodings = [np.random.rand(512)]
        known_metadata = [{"name": "test"}]
        result, distance = self.face_service.find_matching_face(known_encodings, known_metadata, None)
        self.assertIsNone(result)
        self.assertIsNone(distance)

if __name__ == '__main__':
    unittest.main() 