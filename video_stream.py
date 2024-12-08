import cv2
import os
import time
import base64
from datetime import datetime
import threading
import queue

# Ensure the directory for storing frames exists
FRAME_STORAGE_DIR = os.path.join(os.getcwd(), 'captured_images')
os.makedirs(FRAME_STORAGE_DIR, exist_ok=True)

# Global variables to store the latest frame and captured frame path
latest_frame = None
latest_captured_frame_path = None

# Global queue for logging
log_queue = queue.Queue()

def save_frame(frame):
    """
    Save a frame to the local file system with a timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = os.path.join(FRAME_STORAGE_DIR, f"frame_{timestamp}.jpg")
    cv2.imwrite(filename, frame)
    return filename

def frame_to_base64(frame):
    """
    Convert OpenCV frame to base64 encoded image
    """
    _, buffer = cv2.imencode('.jpg', frame)
    return base64.b64encode(buffer).decode('utf-8')

def capture_video_stream():
    """
    Capture video stream and return frame details
    """
    cap = cv2.VideoCapture(0)  # Open default camera
    
    if not cap.isOpened():
        return None, "无法打开摄像头", None
    
    ret, frame = cap.read()
    if not ret:
        cap.release()
        return None, "无法读取视频流", None
    
    cap.release()
    return frame, None, frame

def start_video_stream():
    """
    Start displaying live video stream
    """
    frame, error, _ = capture_video_stream()
    if frame is not None:
        return frame_to_base64(frame)
    return error or "无法启动视频流"

def start_frame_capture(stop_capture_flag):
    """
    Start continuous frame capture
    """
    global latest_frame, latest_captured_frame_path

    def capture_loop():
        global latest_frame, latest_captured_frame_path
        cap = cv2.VideoCapture(0)  # Open default camera
        
        if not cap.isOpened():
            log_queue.put("错误: 无法打开摄像头")
            return

        while not stop_capture_flag.is_set():
            try:
                ret, frame = cap.read()
                if not ret:
                    log_queue.put("错误: 无法读取视频流")
                    break

                # Save frame
                saved_path = save_frame(frame)
                
                # Update global variables
                latest_frame = frame
                latest_captured_frame_path = saved_path
                
                # Log the captured frame
                log_message = f"成功截取帧: {saved_path}"
                print(log_message)
                log_queue.put(log_message)
                
                # Wait for 3 seconds
                time.sleep(3)
            except Exception as e:
                error_message = f"错误: {e}"
                print(error_message)
                log_queue.put(error_message)
                break

        # Clean up
        cap.release()
        log_queue.put("截帧已停止")
    
    capture_thread = threading.Thread(target=capture_loop, daemon=True)
    capture_thread.start()
    
    return capture_thread

def stop_frame_capture(capture_thread, stop_capture_flag):
    """
    Stop frame capture
    """
    if stop_capture_flag is not None:
        stop_capture_flag.set()
        if capture_thread is not None:
            capture_thread.join(timeout=5)  # Wait up to 5 seconds for the thread to finish

def get_latest_frame():
    """
    Get the latest captured frame
    """
    global latest_frame
    return latest_frame

def get_latest_captured_frame_path():
    """
    Get the path of the latest captured frame
    """
    global latest_captured_frame_path
    return latest_captured_frame_path

def live_logs_as_html():
    """
    Generator function to provide periodic updates of logs
    """
    while True:
        try:
            log_message = log_queue.get(block=False)
            html_content = f"<div style='height:300px; overflow-y:auto; font-family:monospace; white-space:pre-wrap;'>{log_message}</div>"
            yield html_content
        except queue.Empty:
            pass
        time.sleep(0.1)
