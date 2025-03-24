import cv2
from flask import Flask, render_template, Response, request, jsonify, send_from_directory
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

def capture_photo(cap):
    """Capture a single frame from the given VideoCapture instance."""
    ret, frame = cap.read()
    if not ret:
        return None
    return frame

@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')

@app.route('/take-photos-stream', methods=['GET'])
def take_photos_stream():
    """
    SSE endpoint that instructs the user to face various directions,
    waits a few seconds for each, then captures a photo from the camera.
    Photos are saved as <name>_1.jpg, <name>_2.jpg, etc.
    """
    name = request.args.get('name', 'photo').strip()
    if not name:
        return Response("data: Error: Name is required!\n\n", mimetype="text/event-stream")
    
    # Open the camera device. Use index 2 (for /dev/video2) if that works better.
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        return Response("data: Error: Could not open video device.\n\n", mimetype="text/event-stream")
    
    # Optional: allow the camera a moment to warm up
    time.sleep(1)
    
    def generate():
        for i, direction in enumerate(DIRECTIONS):
            yield f"data: Please face {direction}\n\n"
            # Wait a few seconds for the user to adjust
            time.sleep(2)
            
            # Capture a photo
            frame = capture_photo(cap)
            if frame is None:
                yield f"data: Failed to capture photo {i+1} for {direction}\n\n"
                continue
            
            photo_filename = f"{name}_{i+1}.jpg"
            filepath = os.path.join(PHOTO_FOLDER, photo_filename)
            cv2.imwrite(filepath, frame)
            yield f"data: Captured photo {i+1} ({direction}) as {photo_filename}\n\n"
            time.sleep(1)
            
        yield "data: Photo capture complete!\n\n"
        cap.release()
    
    return Response(generate(), mimetype="text/event-stream")

@app.route('/photos/<filename>')
def serve_photo(filename):
    """Serve a photo from the photos folder."""
    return send_from_directory(PHOTO_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



