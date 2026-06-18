import cv2
import os

# The URL of your simulated camera
url = "rtsp://localhost:8554/camera1"

# Force TCP transport (matching your video-ingestion config)
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

print(f"Connecting to {url}...")
cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("❌ Cannot open stream. Is the simulator running?")
    exit(1)

print("✅ Connected! Press 'q' in the video window to quit.")

while True:
    ret, frame = cap.read()
    
    if not ret:
        print("❌ Stream ended or corrupted.")
        break
    
    # Check if frame is all black
    if frame.max() == 0:
        print("⚠️ Warning: Frame is completely black (all zeros).")
    
    # Display the frame
    cv2.imshow("RTSP Stream Test (Press 'q' to quit)", frame)
    
    # Wait 1ms and check if 'q' was pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
