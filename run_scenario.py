import os
import sys
import cv2
import time
import requests
import threading
import numpy as np
from collections import Counter

# --- MEMORY SAVERS ---
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENCV_FFMPEG_THREADS"] = "1" # Force FFmpeg to use 1 thread

import torch
torch.set_grad_enabled(False)
torch.set_num_threads(1)

cv2.setNumThreads(1) # Force OpenCV to use 1 thread

from cv_engine.detector import PersonDetector
from cv_engine.ocr_module import TextReader

# Backend URL
BACKEND_URL = "http://127.0.0.1:8000/update_real_status"

def send_update(emp_id, status="Idle", unattended_customer=False, location="Unknown"):
    """Sends status update to backend in a separate thread."""
    def _send():
        try:
            payload = {"employee_id": emp_id, "status": status, "unattended_customer": unattended_customer, "location": location}
            requests.post(BACKEND_URL, json=payload)
            print(f"SENT TO BACKEND: {emp_id} -> {status} | Unattended: {unattended_customer} @ {location}")
        except Exception as e:
            print(f"Failed to send to backend: {e}")
    threading.Thread(target=_send).start()


class CameraState:
    """Holds the per-camera tracking state (replaces per-process variables)."""
    def __init__(self, video_path, location_name):
        self.video_path = video_path
        self.location_name = location_name
        self.cap = cv2.VideoCapture(video_path)
        self.frame_count = 0
        self.id_history = []
        self.idle_counter = 0
        self.current_stable_id = "Scanning..."
        self.current_stable_status = "Idle"
        self.last_sent_id = None
        self.last_sent_status = None
        self.last_sent_unattended = None
        self.last_emp_center = None
        self.alive = self.cap.isOpened()
        if not self.alive:
            print(f"  [ERROR] Could not open {video_path}")
        else:
            print(f"  [OK] Opened {video_path} (Location: {location_name})")


def process_frame(cam, frame, detector, ocr):
    """Process a single frame for a given camera state. Mirrors the old main() loop body."""
    # Resize immediately to save memory
    frame = cv2.resize(frame, (1280, 720))
    cam.frame_count += 1

    # Detect people
    people = detector.detect(frame)

    employees = []
    customers = []

    # Spatial tracking
    employee_idx = -1
    if cam.last_emp_center is not None and len(people) > 0:
        min_dist = float('inf')
        for i, person in enumerate(people):
            x1, y1, x2, y2, _ = person
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            dist = np.sqrt((cx - cam.last_emp_center[0])**2 + (cy - cam.last_emp_center[1])**2)
            if dist < min_dist:
                min_dist = dist
                employee_idx = i
        if min_dist > 150:
            employee_idx = -1
            cam.last_emp_center = None

    # OCR Logic (Every 30 frames or if tracking lost)
    if cam.frame_count % 30 == 0 or employee_idx == -1:
        people_to_scan = [employee_idx] if employee_idx != -1 else range(len(people))
        for idx in people_to_scan:
            if idx == -1 or idx >= len(people):
                continue
            x1, y1, x2, y2, _ = people[idx]
            h, w, _ = frame.shape
            x1_c, y1_c = max(0, int(x1)), max(0, int(y1))
            x2_c, y2_c = min(w, int(x2)), min(h, int(y2))
            person_roi = frame[y1_c:y2_c, x1_c:x2_c]
            if person_roi.size > 0:
                found_id = ocr.find_employee_id(person_roi)
                if found_id:
                    print(f"[{cam.location_name}] Raw OCR: {found_id} on person {idx}")
                    cam.id_history.append(found_id)
                    if len(cam.id_history) > 5:
                        cam.id_history.pop(0)
                    if cam.id_history:
                        counts = Counter(cam.id_history)
                        most_common, _ = counts.most_common(1)[0]
                        cam.current_stable_id = most_common
                    employee_idx = idx
                    cam.last_emp_center = ((x1 + x2) / 2, (y1 + y2) / 2)
                    break

    # Classify people
    for i, person in enumerate(people):
        x1, y1, x2, y2, conf = person
        if i == employee_idx:
            employees.append(person)
            cam.last_emp_center = ((x1 + x2) / 2, (y1 + y2) / 2)
        else:
            if conf > 0.40:
                customers.append(person)

    # Determine status
    if employee_idx == -1:
        raw_status = "Out of Zone"
    else:
        raw_status = "Idle"
        if len(employees) > 0 and len(customers) > 0:
            raw_status = "Occupied"

    # Stabilize status
    if raw_status == "Occupied":
        cam.current_stable_status = "Occupied"
        cam.idle_counter = 0
    elif raw_status == "Out of Zone":
        cam.current_stable_status = "Out of Zone"
        cam.idle_counter = 0
    else:
        cam.idle_counter += 1
        if cam.idle_counter > 30:
            cam.current_stable_status = "Idle"

    # Unattended customer logic
    is_unattended = len(customers) > 0 and len(employees) == 0
    if cam.frame_count <= 30:
        is_unattended = False

    # Draw employees
    for (x1, y1, x2, y2, conf) in employees:
        box_color = (0, 0, 255) if cam.current_stable_status == "Occupied" else (0, 255, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
        label = f"{cam.current_stable_id} - {cam.current_stable_status}"
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2)

    # Send update only if changed
    emp_id_to_send = cam.current_stable_id if cam.current_stable_id != "Scanning..." else "UNKNOWN"
    if emp_id_to_send != cam.last_sent_id or cam.current_stable_status != cam.last_sent_status or is_unattended != cam.last_sent_unattended:
        send_update(emp_id_to_send, cam.current_stable_status, is_unattended, cam.location_name)
        cam.last_sent_id = emp_id_to_send
        cam.last_sent_status = cam.current_stable_status
        cam.last_sent_unattended = is_unattended

    # Draw customers
    for (x1, y1, x2, y2, conf) in customers:
        box_color = (0, 165, 255) if is_unattended else (255, 0, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
        label = "Unattended Cust" if is_unattended else "Customer"
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)

    return frame


def run_case(case_folder):
    case_path = os.path.join("videos", case_folder)

    if not os.path.exists(case_path):
        print(f"Error: Folder '{case_path}' does not exist.")
        return

    video_extensions = ['.mov', '.mp4', '.avi', '.mkv']
    videos_to_run = []

    for file in sorted(os.listdir(case_path)):
        if any(file.lower().endswith(ext) for ext in video_extensions):
            videos_to_run.append(os.path.join(case_path, file))

    if not videos_to_run:
        print(f"No videos found in '{case_path}'. Add some .MOV or .mp4 files.")
        return

    print(f"Found {len(videos_to_run)} videos in {case_path}.")
    print("=" * 60)

    # ===== LOAD AI MODELS ONCE =====
    print("Loading AI Models (this only happens ONCE for ALL cameras)...")
    detector = PersonDetector()
    ocr = TextReader()
    print("=" * 60)
    print("AI Models loaded! Starting Multi-Camera Simulation...\n")

    # ===== OPEN ALL VIDEO STREAMS =====
    cameras = []
    for video_path in videos_to_run:
        video_filename = os.path.basename(video_path)
        location_name, _ = os.path.splitext(video_filename)
        cam = CameraState(video_path, location_name)
        cameras.append(cam)

    active_cameras = [c for c in cameras if c.alive]
    print(f"\n{len(active_cameras)} cameras active. Processing in round-robin...\n")
    print("Press 'Q' on any video window to stop.\n")

    # ===== ROUND-ROBIN PROCESSING LOOP =====
    while active_cameras:
        to_remove = []
        for cam in active_cameras:
            ret, frame = cam.cap.read()
            if not ret:
                print(f"[{cam.location_name}] Video ended.")
                cam.cap.release()
                to_remove.append(cam)
                continue

            # Process and display
            processed_frame = process_frame(cam, frame, detector, ocr)
            window_name = f"Camera: {cam.location_name}"
            cv2.imshow(window_name, processed_frame)

        # Remove finished cameras
        for cam in to_remove:
            active_cameras.remove(cam)

        # Check for quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nUser pressed Q. Shutting down...")
            break

    # Cleanup
    for cam in cameras:
        if cam.cap.isOpened():
            cam.cap.release()
    cv2.destroyAllWindows()
    print("Simulation ended.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_scenario.py <case_folder_name>")
        print("Example: python run_scenario.py case1")
    else:
        run_case(sys.argv[1])