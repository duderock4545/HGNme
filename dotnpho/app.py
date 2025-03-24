import cv2
from flask import Flask, render_template, Response, request, jsonify, send_from_directory
import threading
import time
import os

app = Flask(__name__)

# Directory to save photos
PHOTO_FOLDER = './photos'
os.makedirs(PHOTO_FOLDER, exist_ok=True)

# Directions for the user to face
DIRECTIONS = [
    "Center",
    "Slightly Left",
    "Slightly Right",
    "Slightly Up",
    "Slightly Down"
]

# Global variables for shared camera access
cap = None           # The VideoCapture instance
outputFrame = None   # The latest frame read from the camera
lock = threading.Lock()
bg_thread_started = False

def init_camera():
    """Lazily initialize the camera if it hasn't been opened yet."""
    global cap
    if cap is None:
        # Try using device index 1 (adjust if necessary)
        cap = cv2.VideoCapture(2)
        if not cap.isOpened():
            print("Error: Could not open video device. Try a different index or close other apps using the camera.")
            return False
    return True

def update_frame():
    """Background thread that continuously captures frames from the camera."""
    global outputFrame, cap
    if not init_camera():
        return
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        with lock:
            outputFrame = frame.copy()
        time.sleep(0.03)  # Aim for roughly 30 fps

def start_background_thread():
    """Start the background thread once if not already started."""
    global bg_thread_started
    if not bg_thread_started:
        threading.Thread(target=update_frame, daemon=True).start()
        bg_thread_started = True

@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')

def gen_frames():
    """Generator that yields the live feed frames as JPEG-encoded data."""
    if not init_camera():
        yield b""
        return
    start_background_thread()
    while True:
        with lock:
            if outputFrame is None:
                continue
            ret, buffer = cv2.imencode('.jpg', outputFrame)
            if not ret:
                continue
            frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Return the live feed stream."""
    start_background_thread()
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/take-photos-stream', methods=['GET'])
def take_photos_stream():
    """
    SSE endpoint that instructs the user to face various directions,
    waits a few seconds for each, then captures a photo from the shared frame.
    Photos are saved as <name>_1.jpg, <name>_2.jpg, etc.
    """
    name = request.args.get('name', 'photo').strip()
    if not name:
        return Response("data: Error: Name is required!\n\n", mimetype="text/event-stream")
    
    if not init_camera():
        return Response("data: Error: Could not open camera\n\n", mimetype="text/event-stream")
    start_background_thread()
    
    def generate():
        for i, direction in enumerate(DIRECTIONS):
            yield f"data: Please face {direction}\n\n"
            time.sleep(2)  # Allow time for the user to adjust
            photo_filename = f"{name}_{i+1}.jpg"
            filepath = os.path.join(PHOTO_FOLDER, photo_filename)
            with lock:
                if outputFrame is None:
                    yield f"data: Failed to capture photo {i+1} (no frame available)\n\n"
                    continue
                cv2.imwrite(filepath, outputFrame)
            yield f"data: Captured photo {i+1} ({direction}) as {photo_filename}\n\n"
            time.sleep(1)  # Short pause before next instruction
        yield "data: Photo capture complete!\n\n"
    
    return Response(generate(), mimetype="text/event-stream")

@app.route('/photos/<filename>')
def serve_photo(filename):
    """Serve a photo from the photos folder."""
    return send_from_directory(PHOTO_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



