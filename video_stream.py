import os
import time
from datetime import datetime
from PIL import Image

# Ensure the directory for storing frames exists
FRAME_STORAGE_DIR = os.path.join(os.getcwd(), 'captured_images')
os.makedirs(FRAME_STORAGE_DIR, exist_ok=True)

_last_save_time = 0
_frame_count = 0


def save_frame(frame):
    """Save a numpy array frame to disk. Returns the file path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"frame_{timestamp}.jpg"
    filepath = os.path.join(FRAME_STORAGE_DIR, filename)
    img = Image.fromarray(frame)
    img.save(filepath, "JPEG")
    return filepath


def process_streaming_frame(frame, capture_rate=1):
    """Process a streaming frame from Gradio webcam.

    Saves frame to disk at the specified capture_rate interval.
    Returns the frame for display.
    """
    global _last_save_time, _frame_count
    if frame is None:
        return frame
    current_time = time.time()
    if current_time - _last_save_time >= capture_rate:
        filepath = save_frame(frame)
        _last_save_time = current_time
        _frame_count += 1
        print(f"[VideoStream] Frame #{_frame_count} saved: {filepath}")
    return frame


def get_frame_count():
    """Return the current frame count."""
    return _frame_count


def reset_frame_count():
    """Reset frame counter for a new capturing session."""
    global _frame_count
    _frame_count = 0


def get_captured_frames():
    """Return list of captured frame paths, sorted newest first."""
    if os.path.exists(FRAME_STORAGE_DIR):
        frames = [os.path.join(FRAME_STORAGE_DIR, f)
                  for f in os.listdir(FRAME_STORAGE_DIR)
                  if f.endswith('.jpg')]
        return sorted(frames, key=lambda x: os.path.getmtime(x), reverse=True)
    return []


def clear_captured_frames():
    """Clear all captured frames from storage directory."""
    count = 0
    if os.path.exists(FRAME_STORAGE_DIR):
        for f in os.listdir(FRAME_STORAGE_DIR):
            if f.endswith('.jpg'):
                os.remove(os.path.join(FRAME_STORAGE_DIR, f))
                count += 1
    print(f"[VideoStream] Cleared {count} frame(s)")
