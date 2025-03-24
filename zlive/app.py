import cv2
from flask import Flask, render_template, Response

app = Flask(__name__)

def gen_frames():
    # Open the camera device; adjust the index if necessary (0 for /dev/video0, 1 for /dev/video1)
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Could not open video device.")
        return

    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            # Optionally, you can resize or process the frame here
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            # Yield a frame in byte format as a multipart response
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    # Render the HTML template with a button to start the stream
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    # Return the streaming response
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Run the app on all network interfaces for local testing
    app.run(host='0.0.0.0', port=5000, debug=True)



