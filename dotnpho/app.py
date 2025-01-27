from flask import Flask, render_template, Response, send_from_directory, request
import os
import subprocess
import time

app = Flask(__name__)

# Folder to save photos
PHOTO_FOLDER = "./photos"
os.makedirs(PHOTO_FOLDER, exist_ok=True)

# Photo directions
DIRECTIONS = [
    "Center",
    "Slightly Left",
    "Slightly Right",
    "Slightly Up",
    "Slightly Down"
]

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
            # Send direction to the client
            yield f"data: Please face {direction}\n\n"
            time.sleep(2)  # Allow the user to adjust their position

            # Capture photo
            photo_path = os.path.join(PHOTO_FOLDER, f"{name}_{i + 1}.jpg")
            if capture_photo(photo_path):
                yield f"data: Captured photo {i + 1} ({direction})\n\n"
            else:
                yield f"data: Failed to capture photo {i + 1}\n\n"

            time.sleep(1)  # Pause before the next instruction

        yield "data: Photo capture complete!\n\n"

    return Response(generate_photos(), mimetype="text/event-stream")

@app.route("/photos/<filename>")
def serve_photo(filename):
    """Serve a photo from the photos directory."""
    return send_from_directory(PHOTO_FOLDER, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


