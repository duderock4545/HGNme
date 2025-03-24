// Function to load the Tiny Face Detector model from /static/models
async function loadModels() {
  await faceapi.nets.tinyFaceDetector.load('/static/models');
  console.log("Face API models loaded");
}


document.getElementById("startBtn").addEventListener("click", async () => {
  // Reveal the MJPEG feed container
  document.getElementById("feedContainer").style.display = "block";
  // Load face-api models
  await loadModels();


  // Start periodic face detection every 500ms
  setInterval(async () => {
    const img = document.getElementById("liveFeed");
    // Ensure image is loaded
    if (!img.complete || !img.naturalWidth) {
      return;
    }
    
    // Run face detection on the image element
    const detection = await faceapi.detectSingleFace(img, new faceapi.TinyFaceDetectorOptions());
    const instructionDiv = document.getElementById("instruction");
    
    if (detection) {
      // Calculate the horizontal center of the detected face
      const { x, width } = detection.box;
      const faceCenter = x + width / 2;
      const imgCenter = img.naturalWidth / 2;
      const tolerance = 30; // pixel tolerance
      
      if (faceCenter < imgCenter - tolerance) {
        instructionDiv.innerText = "Move Right";
      } else if (faceCenter > imgCenter + tolerance) {
        instructionDiv.innerText = "Move Left";
      } else {
        instructionDiv.innerText = "Centered";
      }
    } else {
      instructionDiv.innerText = "No face detected";
    }
  }, 500);
});





