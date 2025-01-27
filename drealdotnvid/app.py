from flask import Flask, render_template, Response, request, jsonify, send_from_directory
import os
import subprocess
import threading
import time

app = Flask(__name__)

# --------------------------------
# Shared Setup
# --------------------------------
PHOTO_FOLDER = "./photos"
VIDEO_FOLDER = "./videos"
os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)

DIRECTIONS = [
    "Center",
    "Slightly Left",
    "Slightly Right",
    "Slightly Up",
    "Slightly Down"
]

recording = False
record_process = None


# --------------------------------
# Photo Capture Functionality
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

@app.route("/photos/<filename>")
def serve_photo(filename):
    """Serve a photo from the photos directory."""
    return send_from_directory(PHOTO_FOLDER, filename)


# --------------------------------
# Video Recording Functionality
# --------------------------------
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


# --------------------------------
# Main Interface
# --------------------------------
@app.route("/")
def index():
    """Serve the combined HTML page."""
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


