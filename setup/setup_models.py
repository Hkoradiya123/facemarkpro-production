from insightface.app import FaceAnalysis
import os

def setup_models():
    """Initialize and download InsightFace models"""
    
    print("Setting up InsightFace models...")
    
    try:
        # Initialize the face analysis app
        app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        
        # Prepare the model (this will download if not already present)
        print("Downloading and preparing face recognition model...")
        app.prepare(ctx_id=0)
        
        print("Face recognition model setup completed successfully!")
        
        # Test the model
        print("Testing model with a dummy image...")
        import numpy as np
        
        # Create a dummy image (1x1 pixel)
        dummy_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        # Try to detect faces (should return empty list for dummy image)
        faces = app.get(dummy_image)
        print(f"Model test completed. Detected {len(faces)} faces in dummy image.")
        
        return True
        
    except Exception as e:
        print(f"Error setting up models: {e}")
        return False

def check_model_files():
    """Check if model files exist"""
    
    # InsightFace models are typically stored in ~/.insightface/models/
    home_dir = os.path.expanduser("~")
    model_dir = os.path.join(home_dir, ".insightface", "models")
    
    if os.path.exists(model_dir):
        print(f"Model directory exists: {model_dir}")
        files = os.listdir(model_dir)
        print(f"Found {len(files)} files in model directory")
        return True
    else:
        print("Model directory not found. Models will be downloaded on first use.")
        return False

if __name__ == "__main__":
    print("Checking existing model files...")
    check_model_files()
    
    print("\nSetting up models...")
    success = setup_models()
    
    if success:
        print("\nModel setup completed successfully!")
    else:
        print("\nModel setup failed. Please check the error messages above.") 