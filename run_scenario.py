import os
import sys
import cv2
import requests
import threading
import numpy as np
from collections import Counter

# --- MEMORY SAVERS (must be set BEFORE importing torch/cv2) ---
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENCV_FFMPEG_THREADS"] = "1"

import torch
torch.set_grad_enabled(False)
torch.set_num_threads(1)

cv2.setNumThreads(1)

# Add cv_engine to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cv_engine"))

from detector import PersonDetector
from ocr_module import TextReader

BACKEND_URL = "http://127.0.0.1:8000/update_real_status"


def send_update(emp_id, status="Idle", unattended_customer=False, location="Unknown"):
    def _send():
        try:
            payload = {
                "employee_id": emp_id,
                "status": status,
                "unattended_customer": unattended_customer,
                "location": location
            }
            requests.post(BACKEND_URL, json=payload, timeout=2)
            print(f"SENT: {emp_id} -> {status} | Unattended: {unattended_customer} @ {location}")
        except Exception as e:
            print(f"Backend send failed: {e}")
    threading.Thread(target=_send, daemon=True).start()


class CameraState:
    """Tracks per-camera state without needing a separate process."""
    def __init__(self, video_path, location_name):
        self.video_path = video_path
        self.location_name = location_name
        self.cap = cv2.VideoCapture(video_path)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Only buffer 1 frame at a time
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
    """Process one frame for a camera using shared AI models."""
    # Full resolution processing for accurate OCR badge detection
    frame = cv2.resize(frame, (1280, 720))
    cam.frame_count += 1

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

    # OCR every 30 frames or if tracking lost
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
                    print(f"[{cam.location_name}] OCR: {found_id}")
                    cam.id_history.append(found_id)
                    if len(cam.id_history) > 5:
                        cam.id_history.pop(0)
                    counts = Counter(cam.id_history)
                    cam.current_stable_id = counts.most_common(1)[0][0]
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

    # Determine status using PROXIMITY CHECK (not just "is any customer in frame")
    # Employee is only Occupied if a customer is physically close to them
    is_occupied = False
    if len(employees) > 0 and len(customers) > 0:
        emp = employees[0]
        emp_cx = (emp[0] + emp[2]) / 2
        emp_cy = (emp[1] + emp[3]) / 2
        for cust in customers:
            cust_cx = (cust[0] + cust[2]) / 2
            cust_cy = (cust[1] + cust[3]) / 2
            dist = np.sqrt((emp_cx - cust_cx)**2 + (emp_cy - cust_cy)**2)
            if dist < 300:  # 300px proximity threshold at 1280x720
                is_occupied = True
                break

    if employee_idx == -1:
        raw_status = "Out of Zone"
    elif is_occupied:
        raw_status = "Occupied"
    else:
        raw_status = "Idle"

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

    # Unattended detection
    is_unattended = len(customers) > 0 and len(employees) == 0
    if cam.frame_count <= 30:
        is_unattended = False

    # Draw employees
    for (x1, y1, x2, y2, conf) in employees:
        box_color = (0, 0, 255) if cam.current_stable_status == "Occupied" else (0, 255, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
        label = f"{cam.current_stable_id} - {cam.current_stable_status}"
        cv2.putText(frame, label, (x1, max(0, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

    # Draw customers
    for (x1, y1, x2, y2, conf) in customers:
        box_color = (0, 165, 255) if is_unattended else (255, 0, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
        label = "Unattended!" if is_unattended else "Customer"
        cv2.putText(frame, label, (x1, max(0, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)

    # Send update if state changed
    emp_id_to_send = cam.current_stable_id if cam.current_stable_id != "Scanning..." else "UNKNOWN"
    if (emp_id_to_send != cam.last_sent_id or
            cam.current_stable_status != cam.last_sent_status or
            is_unattended != cam.last_sent_unattended):
        send_update(emp_id_to_send, cam.current_stable_status, is_unattended, cam.location_name)
        cam.last_sent_id = emp_id_to_send
        cam.last_sent_status = cam.current_stable_status
        cam.last_sent_unattended = is_unattended

    return frame


def run_case(case_folder):
    case_path = os.path.join("videos", case_folder)

    if not os.path.exists(case_path):
        print(f"Error: Folder '{case_path}' does not exist.")
        return

    video_extensions = ['.mov', '.mp4', '.avi', '.mkv']
    videos_to_run = [
        os.path.join(case_path, f)
        for f in sorted(os.listdir(case_path))
        if any(f.lower().endswith(ext) for ext in video_extensions)
    ]

    if not videos_to_run:
        print(f"No videos found in '{case_path}'.")
        return

    print(f"Found {len(videos_to_run)} videos in {case_path}.")
    print("=" * 60)
    print("Loading AI Models ONCE for all cameras...")
    detector = PersonDetector()
    ocr = TextReader()
    print("=" * 60)
    print("AI Models loaded! Opening video streams...\n")

    cameras = []
    for video_path in videos_to_run:
        location_name = os.path.splitext(os.path.basename(video_path))[0]
        cameras.append(CameraState(video_path, location_name))

    active = [c for c in cameras if c.alive]
    print(f"\n{len(active)} cameras active. Press Q in any window to stop.\n")

    while active:
        finished = []
        for cam in active:
            ret, frame = cam.cap.read()
            if not ret:
                print(f"[{cam.location_name}] Video ended.")
                cam.cap.release()
                finished.append(cam)
                continue
            processed = process_frame(cam, frame, detector, ocr)
            cv2.imshow(f"Camera: {cam.location_name}", processed)

        for cam in finished:
            active.remove(cam)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nStopping simulation...")
            break

    for cam in cameras:
        if cam.cap.isOpened():
            cam.cap.release()
    cv2.destroyAllWindows()
    print("Simulation ended.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_scenario.py <case_folder>")
        print("Example: python run_scenario.py case1")
    else:
        run_case(sys.argv[1])
