from flask import Flask, render_template, request, jsonify
import os
import subprocess
import threading
import time
import pickle
import face_recognition

app = Flask(__name__)

# Folders for saving videos and photos, and log file for recognized names
VIDEO_FOLDER = "./videos"
ACTIVE_PERSON_FOLDER = "./active_person"
RECOGNITION_LOG = "./recognized_name.txt"  # Log for storing the recognized name
os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(ACTIVE_PERSON_FOLDER, exist_ok=True)

# Variables to control recording
recording = False
record_process = None

# Load known encodings and names from train.pkl
Encodings = []
Names = []
PKL_FILE = 'train.pkl'
if os.path.exists(PKL_FILE):
    with open(PKL_FILE, 'rb') as f:
        Names = pickle.load(f)
        Encodings = pickle.load(f)
else:
    print("Warning: train.pkl not found. Facial recognition will not work.")


def record_video(duration):
    """
    Record video using GStreamer and save it to a file.
    For a USB camera running at 30 fps, we capture duration*30 frames.
    """
    global record_process
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    video_path = os.path.join(VIDEO_FOLDER, f"video_{timestamp}.mp4")
    num_buffers = duration * 30  # assuming 30 fps

    # Updated GStreamer pipeline for USB camera recording
    gst_command = [
        "gst-launch-1.0",
        "v4l2src", f"device=/dev/video1", f"num-buffers={num_buffers}",
        "!",
        "image/jpeg,width=1280,height=720,framerate=30/1",
        "!",
        "jpegdec",
        "!",
        "videoconvert",
        "!",
        "x264enc", "tune=zerolatency", "bitrate=500", "speed-preset=ultrafast",
        "!",
        "mp4mux",
        "!",
        f"filesink location={video_path}"
    ]

    try:
        record_process = subprocess.Popen(" ".join(gst_command), shell=True)
        record_process.wait(timeout=duration + 5)
    except subprocess.TimeoutExpired:
        record_process.terminate()
    finally:
        record_process = None


def capture_photo(photo_path):
    """
    Capture a single photo using GStreamer with a USB camera.
    """
    gst_command = (
        f"gst-launch-1.0 v4l2src device=/dev/video1 num-buffers=1 ! "
        f"image/jpeg,width=1280,height=720,framerate=30/1 ! "
        f"jpegdec ! videoconvert ! jpegenc ! filesink location={photo_path}"
    )
    process = subprocess.run(gst_command, shell=True, stderr=subprocess.PIPE)
    if process.returncode != 0:
        print(f"Error capturing photo: {process.stderr.decode()}")
        return False
    return True


def recognize_face(photo_path):
    """
    Recognize the person in the given photo using face_recognition.
    Returns the recognized name or "Unknown" if no match is found.
    """
    if not Encodings or not Names:
        return "Unknown (no training data available)"
    
    image = face_recognition.load_image_file(photo_path)
    face_positions = face_recognition.face_locations(image)
    all_encodings = face_recognition.face_encodings(image, face_positions)
    
    for face_encoding in all_encodings:
        matches = face_recognition.compare_faces(Encodings, face_encoding, tolerance=0.6)
        if True in matches:
            first_match_index = matches.index(True)
            return Names[first_match_index]
    
    return "Unknown"


@app.route("/")
def index():
    """Serve the HTML page."""
    return render_template("index.html")


@app.route("/start-record", methods=["POST"])
def start_record():
    """Start video recording."""
    global recording
    if recording:
        return jsonify({"message": "Already recording!"})
    recording = True
    # Duration is provided from the form; default to 5 seconds if not provided
    duration = int(request.form.get("duration", 5))
    threading.Thread(target=record_video, args=(duration,)).start()
    return jsonify({"message": f"Recording started for {duration} seconds!"})


@app.route("/stop-record", methods=["POST"])
def stop_record():
    """Stop video recording."""
    global recording, record_process
    if not recording:
        return jsonify({"message": "No recording in progress!"})
    if record_process:
        record_process.terminate()
        record_process = None
    recording = False
    return jsonify({"message": "Recording stopped!"})


@app.route("/capture-active-person", methods=["POST"])
def capture_active_person():
    """
    Capture a photo, perform facial recognition on it, and log the recognized name.
    This is only allowed when recording is not in progress.
    """
    global recording, record_process
    if recording or record_process:
        return jsonify({"message": "Cannot capture photo while recording is in progress!"}), 400

    # Delay to ensure the camera resource is free (adjust as needed)
    time.sleep(7)
    
    photo_path = os.path.join(ACTIVE_PERSON_FOLDER, "active.jpg")
    if not capture_photo(photo_path):
        return jsonify({"message": "Failed to capture active person photo!"}), 500

    recognized_name = recognize_face(photo_path)
    
    # Write the recognized name and timestamp to the log file
    with open(RECOGNITION_LOG, "w") as log_file:
        log_file.write(f"Recognized Name: {recognized_name}\n")
        log_file.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return jsonify({"message": f"Photo captured and recognized as: {recognized_name}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)



