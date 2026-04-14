let cameraStream = null;
let isDetecting = false;
let detectionInterval = null;

// Initialize the camera
async function initCamera() {
  const videoElement = document.getElementById("cameraFeed");
  const canvasElement = document.getElementById("videoFeed");
  const loadingOverlay = document.getElementById("loadingOverlay");

  try {
    // Request camera access with preferred settings
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "user",
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
    });

    cameraStream = stream;
    videoElement.srcObject = stream;

    // Wait for video to be ready
    await new Promise((resolve) => {
      videoElement.onloadedmetadata = () => {
        videoElement.play();
        resolve();
      };
    });

    // Set canvas dimensions to match video
    const ctx = canvasElement.getContext("2d");
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;

    // Start rendering camera feed to canvas
    renderFrame(videoElement, canvasElement, ctx);

    // Hide loading overlay
    loadingOverlay.classList.add("fade-out");
    setTimeout(() => {
      loadingOverlay.style.display = "none";
    }, 500);

    // Start face detection
    startDetection();

    return true;
  } catch (error) {
    console.error("Error accessing camera:", error);
    // Update loading overlay with error message
    const loadingOverlay = document.getElementById("loadingOverlay");
    const loadingContent = loadingOverlay.querySelector(".flex.flex-col");

    if (loadingContent) {
      loadingContent.innerHTML = `
        <svg class="w-16 h-16 text-red-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
        <p class="text-red-700 font-semibold text-lg">Gagal mengakses kamera</p>
        <p class="text-red-600 text-sm mt-2">Mohon berikan izin kamera dan refresh halaman</p>
        <button onclick="location.reload()" class="mt-4 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors">
          Refresh Halaman
        </button>
      `;
    }
    return false;
  }
}

// Render video frame to canvas
function renderFrame(video, canvas, ctx) {
  if (video.paused || video.ended) return;

  // Draw video frame to canvas
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  // Continue rendering
  requestAnimationFrame(() => renderFrame(video, canvas, ctx));
}

// Start face detection
function startDetection() {
  if (isDetecting) return;

  isDetecting = true;

  // Capture frame and send for detection every second
  detectionInterval = setInterval(() => {
    if (cameraStream && !document.hidden) {
      captureAndDetect();
    }
  }, 1000);
}

// Capture frame and send for detection
function captureAndDetect() {
  const canvas = document.getElementById("videoFeed");
  if (!canvas) return;

  // Get frame as base64 encoded image
  try {
    const imageData = canvas.toDataURL("image/jpeg", 0.7);

    // Send to server for detection
    fetch("/detect_face", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: imageData }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.detected_name) {
          document.getElementById("detectedName").textContent = data.detected_name;
        }
      })
      .catch((error) => {
        console.error("Error in face detection:", error);
      });
  } catch (error) {
    console.error("Error capturing frame:", error);
  }
}

// Stop camera and detection
function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }

  if (detectionInterval) {
    clearInterval(detectionInterval);
    detectionInterval = null;
  }

  isDetecting = false;
}

// Handle page visibility changes
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    // Page is not visible, reduce detection frequency
    if (detectionInterval) {
      clearInterval(detectionInterval);
      detectionInterval = setInterval(captureAndDetect, 3000); // Slow down to every 3 seconds
    }
  } else {
    // Page is visible again, restore normal frequency
    if (detectionInterval) {
      clearInterval(detectionInterval);
      detectionInterval = setInterval(captureAndDetect, 1000); // Back to every 1 second
    }
  }
});

// Initialize camera when page loads
document.addEventListener("DOMContentLoaded", initCamera);

// Clean up when page unloads
window.addEventListener("beforeunload", stopCamera);
