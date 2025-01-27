from flask import Flask, render_template, Response, request, jsonify, send_from_directory
import os
import subprocess
import threading
import time
import pickle
import face_recognition


app = Flask(__name__)


# --------------------------------
# Folder Setup
# --------------------------------
PHOTO_FOLDER = "./photos"
VIDEO_FOLDER = "./videos"
ACTIVE_PERSON_FOLDER = "./active_person"
RECOGNITION_LOG = "./recognized_name.txt"
PKL_FILE = "train.pkl"


os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(ACTIVE_PERSON_FOLDER, exist_ok=True)


# --------------------------------
# Variables
# --------------------------------
DIRECTIONS = [
    "Center",
    "Slightly Left",
    "Slightly Right",
    "Slightly Up",
    "Slightly Down"
]
recording = False
record_process = None
Encodings = []
Names = []


# --------------------------------
# Load Known Encodings and Names
# --------------------------------
if os.path.exists(PKL_FILE):
    with open(PKL_FILE, "rb") as f:
        Names = pickle.load(f)
        Encodings = pickle.load(f)
else:
    print("Warning: train.pkl not found. Facial recognition will not work.")


# --------------------------------
# Helper Functions
# --------------------------------
def capture_photo(photo_path):
    """Capture a single photo using GStreamer."""
    gst_command = (
        f"gst-launch-1.0 nvarguscamerasrc num-buffers=1 ! "
        f"'video/x-raw(memory:NVMM),width=1280,height=720,framerate=60/1' ! "
        f"nvvidconv ! videoconvert ! jpegenc ! filesink location={photo_path}"
    )
    process = subprocess.run(gst_command, shell=True, stderr=subprocess.PIPE)
    if process.returncode != 0:
        print(f"Error capturing photo: {process.stderr.decode()}")
        return False
    return True


def record_video(duration):
    """Record video using GStreamer and save it to a file."""
    global record_process
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    video_path = os.path.join(VIDEO_FOLDER, f"video_{timestamp}.mp4")


    gst_command = [
        "gst-launch-1.0",
        "nvarguscamerasrc",
        f"num-buffers={duration * 60}",
        "!",
        "'video/x-raw(memory:NVMM),width=1280,height=720,framerate=60/1'",
        "!",
        "nvvidconv",
        "!",
        "videoconvert",
        "!",
        "x264enc",
        "tune=zerolatency",
        "bitrate=500",
        "speed-preset=ultrafast",
        "!",
        "mp4mux",
        "!",
        f"filesink location={video_path}"
    ]


    try:
        record_process = subprocess.Popen(" ".join(gst_command), shell=True)
        record_process.wait(timeout=duration)
    except subprocess.TimeoutExpired:
        record_process.terminate()
    finally:
        record_process = None


def recognize_face(photo_path):
    """Recognize the person in the given photo."""
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


# --------------------------------
# Routes
# --------------------------------
@app.route("/")
def index():
    """Serve the HTML page."""
    return render_template("index.html")


@app.route("/take-photos-stream", methods=["GET"])
def take_photos_stream():
    """Capture 5 photos and send instructions via SSE."""
    name = request.args.get("name", "").strip()
    if not name:
        return Response("data: Error: Name is required!\n\n", mimetype="text/event-stream")


    def generate_photos():
        for i, direction in enumerate(DIRECTIONS):
            yield f"data: Please face {direction}\n\n"
            time.sleep(2)


            # Capture photo
            photo_path = os.path.join(PHOTO_FOLDER, f"{name}_{i + 1}.jpg")
            if capture_photo(photo_path):
                yield f"data: Captured photo {i + 1} ({direction})\n\n"
            else:
                yield f"data: Failed to capture photo {i + 1}\n\n"
            time.sleep(1)


        yield "data: Photo capture complete!\n\n"


    return Response(generate_photos(), mimetype="text/event-stream")


@app.route("/capture-active-person", methods=["POST"])
def capture_active_person():
    """Capture a photo, recognize the person, and log the result."""
    global recording, record_process
    if recording or record_process:
        return jsonify({"message": "Cannot capture photo while recording is in progress!"}), 400


    # Delay to ensure the camera resource is free
    time.sleep(7)


    photo_path = os.path.join(ACTIVE_PERSON_FOLDER, "active.jpg")
    if not capture_photo(photo_path):
        return jsonify({"message": "Failed to capture active person photo!"}), 500


    # Recognize the person in the photo
    recognized_name = recognize_face(photo_path)


    # Write the recognized name to the log file
    with open(RECOGNITION_LOG, "w") as log_file:
        log_file.write(f"Recognized Name: {recognized_name}\n")
        log_file.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")


    return jsonify({"message": f"Photo captured and recognized as: {recognized_name}"})


@app.route("/start-record", methods=["POST"])
def start_record():
    """Start video recording."""
    global recording
    if recording:
        return jsonify({"message": "Already recording!"})
    recording = True
    duration = int(request.form.get("duration", 5))  # Default to 5 seconds
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


@app.route("/photos/<filename>")
def serve_photo(filename):
    """Serve a photo from the photos directory."""
    return send_from_directory(PHOTO_FOLDER, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)





