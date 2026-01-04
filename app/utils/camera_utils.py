import cv2
import numpy as np
from PIL import Image
import io
import base64

def extract_frames_from_video(video_path, max_frames=None):
    """
    Extract frames from a video file
    
    Args:
        video_path: Path to the video file
        max_frames: Maximum number of frames to extract (None for all)
        
    Returns:
        list: List of frames as numpy arrays
    """
    frames = []
    cap = cv2.VideoCapture(video_path)
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if max_frames and frame_count >= max_frames:
            break
            
        frames.append(frame)
        frame_count += 1
    
    cap.release()
    return frames

def resize_frame(frame, scale_factor=0.25):
    """
    Resize a frame for faster processing
    
    Args:
        frame: Input frame as numpy array
        scale_factor: Scale factor for resizing
        
    Returns:
        numpy array: Resized frame
    """
    return cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)

def frame_to_rgb(frame):
    """
    Convert BGR frame to RGB
    
    Args:
        frame: BGR frame as numpy array
        
    Returns:
        numpy array: RGB frame
    """
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

def base64_to_frame(base64_string):
    """
    Convert base64 image string to numpy array
    
    Args:
        base64_string: Base64 encoded image string
        
    Returns:
        numpy array: Image as numpy array
    """
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        img_bytes = base64.b64decode(base64_string)
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        return np.array(img)
    except Exception as e:
        print(f"Error converting base64 to frame: {e}")
        return None

def frame_to_base64(frame):
    """
    Convert numpy array frame to base64 string
    
    Args:
        frame: Frame as numpy array
        
    Returns:
        str: Base64 encoded image string
    """
    try:
        # Convert to PIL Image
        if len(frame.shape) == 3:
            img = Image.fromarray(frame)
        else:
            img = Image.fromarray(frame, mode='L')
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"Error converting frame to base64: {e}")
        return None

def draw_face_boxes(frame, faces, names=None):
    """
    Draw bounding boxes around detected faces
    
    Args:
        frame: Input frame
        faces: List of detected faces
        names: List of names corresponding to faces
        
    Returns:
        numpy array: Frame with drawn boxes
    """
    frame_copy = frame.copy()
    
    for i, face in enumerate(faces):
        # Get bounding box coordinates
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        
        # Draw rectangle
        cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Add name if provided
        if names and i < len(names):
            name = names[i]
            cv2.putText(frame_copy, name, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    
    return frame_copy

def get_video_info(video_path):
    """
    Get information about a video file
    
    Args:
        video_path: Path to the video file
        
    Returns:
        dict: Video information
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return None
    
    info = {
        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        'duration': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS)
    }
    
    cap.release()
    return info 