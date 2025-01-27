from flask import Flask, Response, render_template
import cv2

app = Flask(__name__)

def generate_frames():
    """Generate frames from GStreamer pipeline."""
    # Define the GStreamer pipeline with appsink
    gst_pipeline = (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM),width=1280,height=720,framerate=60/1 ! "
        "nvvidconv ! video/x-raw,format=(string)BGRx ! "
        "videoconvert ! video/x-raw,format=(string)BGR ! appsink"
    )

    # Open the camera feed
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        raise RuntimeError("Error: Unable to access the camera with GStreamer pipeline.")

    # Read frames and encode them as JPEG
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

@app.route('/video-feed')
def video_feed():
    """Route to serve the MJPEG video feed."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    """Serve the main webpage."""
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)



