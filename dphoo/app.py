from flask import Flask, render_template, jsonify, send_from_directory
import os
import subprocess
import time

app = Flask(__name__)

# Folder to save photos
PHOTO_FOLDER = "./photos"
os.makedirs(PHOTO_FOLDER, exist_ok=True)

@app.route("/")
def index():
    """Serve the HTML page."""
    return render_template("index.html")

def capture_photo(photo_path):
    """Capture a single photo using GStreamer."""
    gst_command = (
        f"gst-launch-1.0 nvarguscamerasrc num-buffers=1 ! "
        f"'video/x-raw(memory:NVMM),width=1280,height=720,framerate=60/1' ! "
        f"nvvidconv ! videoconvert ! jpegenc ! filesink location={photo_path}"
    )

    # Run the GStreamer command to capture the photo
    process = subprocess.run(gst_command, shell=True, stderr=subprocess.PIPE)
    if process.returncode != 0:
        print(f"Error capturing photo: {process.stderr.decode()}")
        return False
    return True

@app.route("/take-photos", methods=["POST"])
def take_photos():
    """Capture 5 photos and save them."""
    photos = []
    for i in range(5):
        time.sleep(2)  # Pause to allow user to adjust position
        photo_path = os.path.join(PHOTO_FOLDER, f"photo_{i + 1}.jpg")
        if not capture_photo(photo_path):
            return jsonify({"message": f"Failed to capture photo {i + 1}!"}), 500
        photos.append(f"/photos/{os.path.basename(photo_path)}")

    return jsonify({"message": "Photos captured successfully!", "photos": photos})

# Route to serve photos
@app.route("/photos/<filename>")
def serve_photo(filename):
    """Serve a photo from the photos directory."""
    return send_from_directory(PHOTO_FOLDER, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)



