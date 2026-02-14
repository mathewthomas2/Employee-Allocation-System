import cv2
import os

video_path = "videos/emp1.MOV"

if not os.path.exists(video_path):
    print(f"Error: Video file not found at {video_path}")
    exit(1)

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Error: Could not open video {video_path}. Codec issue?")
    exit(1)

print(f"Success! Video {video_path} opened successfully.")
print(f"FPS: {cap.get(cv2.CAP_PROP_FPS)}")
print(f"Frame Count: {cap.get(cv2.CAP_PROP_FRAME_COUNT)}")

cap.release()
print("Test Complete.")
