import cv2
import sys
import time
import requests
import threading
import numpy as np
from collections import Counter
from detector import PersonDetector
from ocr_module import TextReader
from logic import InteractionDetector

import os

# Backend URL
BACKEND_URL = "http://127.0.0.1:8000/update_real_status"

def send_update(emp_id, status="Idle", unattended_customer=False, location="Unknown"):
    """Sends status update to backend in a separate thread to avoid freezing video."""
    def _send():
        try:
            payload = {"employee_id": emp_id, "status": status, "unattended_customer": unattended_customer, "location": location}
            requests.post(BACKEND_URL, json=payload)
            print(f"SENT TO BACKEND: {emp_id} -> {status} | Unattended: {unattended_customer} @ {location}")
        except Exception as e:
            print(f"Failed to send to backend: {e}")
    
    threading.Thread(target=_send).start()

def main(video_file="videos/emp1.MOV"):
    # 1. Initialize Systems
    print("Initializing Computer Vision System...")
    detector = PersonDetector()
    ocr = TextReader()
    # 300 pixels is usually a good threshold for 1080p/4K security cam footage
    interaction_logic = InteractionDetector(proximity_threshold=300) 
    
    # 2. Open Video
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"Error: Could not open {video_file}")
        return

    # 2. Extract Location Name from Video filename
    video_filename = os.path.basename(video_file)
    location_name, _ = os.path.splitext(video_filename)

    print(f"Processing {video_file} (Location: {location_name})...")
    
    frame_count = 0
    id_history = []
    idle_counter = 0
    current_stable_id = "Scanning..."
    current_stable_status = "Idle"
    last_sent_id = None
    last_sent_status = None
    last_sent_unattended = None
    last_emp_center = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break # End of video
        
        frame_count += 1
        
        # 3. Detect People
        people = detector.detect(frame)
        
        employees = []
        customers = []
        
        # 4a. Spatial Tracking: Find closest person to last known employee center
        employee_idx = -1
        if last_emp_center is not None and len(people) > 0:
            min_dist = float('inf')
            for i, person in enumerate(people):
                x1, y1, x2, y2, _ = person
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                dist = np.sqrt((cx - last_emp_center[0])**2 + (cy - last_emp_center[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    employee_idx = i
            
            # If moved more than 150px in one frame, we assume we lost tracking
            if min_dist > 150:
                employee_idx = -1
                last_emp_center = None

        # 4b. OCR Logic (Every 30 frames or if tracking lost)
        if frame_count % 30 == 0 or employee_idx == -1:
            people_to_scan = [employee_idx] if employee_idx != -1 else range(len(people))
            
            for idx in people_to_scan:
                if idx == -1 or idx >= len(people): continue
                x1, y1, x2, y2, _ = people[idx]
                h, w, _ = frame.shape
                x1_c, y1_c = max(0, int(x1)), max(0, int(y1))
                x2_c, y2_c = min(w, int(x2)), min(h, int(y2))
                
                person_roi = frame[y1_c:y2_c, x1_c:x2_c]
                
                if person_roi.size > 0:
                    found_id = ocr.find_employee_id(person_roi)
                    if found_id:
                        print(f"Raw OCR: {found_id} on person {idx}")
                        id_history.append(found_id)
                        if len(id_history) > 5:
                            id_history.pop(0)
                        
                        if id_history:
                            counts = Counter(id_history)
                            most_common, _ = counts.most_common(1)[0]
                            current_stable_id = most_common
                            
                        # We successfully found/re-confirmed the employee
                        employee_idx = idx
                        last_emp_center = ((x1 + x2) / 2, (y1 + y2) / 2)
                        break # Found our employee, stop scanning others

        # 4c. Classify People based on Tracking
        for i, person in enumerate(people):
            x1, y1, x2, y2, conf = person
            if i == employee_idx:
                employees.append(person)
                last_emp_center = ((x1 + x2) / 2, (y1 + y2) / 2) # Update tracking center
            else:
                # FILTER: Only add customers if they are actual people with high confidence (>60%)
                # This prevents posters, reflections, or shadows from turning into "Ghost" customers
                if conf > 0.60:
                    customers.append(person)

        # --- LOGIC: Determine Status ---
        # Assumption: One employee in the frame can handle all customers in the frame.
        if employee_idx == -1:
            raw_status = "Out of Zone"
        else:
            raw_status = "Idle"
            if len(employees) > 0 and len(customers) > 0:
                raw_status = "Occupied"

        # --- STABILIZE STATUS (Asymmetric Cooldown) ---
        # Switch to Occupied or Out of Zone instantly, but require 30 frames
        # of continuous Idle detections to switch back to Idle.
        if raw_status == "Occupied":
            current_stable_status = "Occupied"
            idle_counter = 0
        elif raw_status == "Out of Zone":
            current_stable_status = "Out of Zone"
            idle_counter = 0
        else:
            idle_counter += 1
            if idle_counter > 30: # 30 frames of continuous "Idle"
                current_stable_status = "Idle"

        # --- UNATTENDED CUSTOMER LOGIC ---
        # If there are customers but NO employees in the frame at all, they are unattended.
        is_unattended = len(customers) > 0 and len(employees) == 0
        
        # SAFETY: Do not trigger Unattended if the camera just turned on. 
        # Give the OCR 30 frames (1 second) to find an ID badge before panicking.
        if frame_count <= 30:
            is_unattended = False

        # 5. Process Employees (Draw box, label)
        for (x1, y1, x2, y2, conf) in employees:
            # Draw Box (Red if Busy, Green if Idle)
            box_color = (0, 0, 255) if current_stable_status == "Occupied" else (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            
            # Display Stable ID and Status
            label = f"{current_stable_id} - {current_stable_status}"
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2)

        # ONLY send update to backend if something changed
        # We also send updates if there's no employee (UNKNOWN), but we need to alert about unattended customers
        emp_id_to_send = current_stable_id if current_stable_id != "Scanning..." else "UNKNOWN"
        
        if emp_id_to_send != last_sent_id or current_stable_status != last_sent_status or is_unattended != last_sent_unattended:
            send_update(emp_id_to_send, current_stable_status, is_unattended, location_name)
            last_sent_id = emp_id_to_send
            last_sent_status = current_stable_status
            last_sent_unattended = is_unattended

        # 6. Process Customers (Just draw a simple box without ID)
        for (x1, y1, x2, y2, conf) in customers:
             box_color = (0, 165, 255) if is_unattended else (255, 0, 0) # Orange if unattended, Blue if attended
             cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2) 
             label = "Unattended Cust" if is_unattended else "Customer"
             cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)

        # 7. Show Frame
        frame_resized = cv2.resize(frame, (1280, 720)) 
        cv2.imshow("Employee Monitoring System (Press 'Q' to Quit)", frame_resized)

        # Press Q to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
