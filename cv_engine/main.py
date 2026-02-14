import cv2
from detector import PersonDetector
from ocr_module import TextReader
import time
from collections import Counter
import requests
import threading

# Backend URL
BACKEND_URL = "http://127.0.0.1:8000/update_real_status"

def send_update(emp_id, status="Idle"):
    """Sends status update to backend in a separate thread to avoid freezing video."""
    def _send():
        try:
            payload = {"employee_id": emp_id, "status": status}
            requests.post(BACKEND_URL, json=payload)
            print(f"SENT TO BACKEND: {emp_id} -> {status}")
        except Exception as e:
            print(f"Failed to send to backend: {e}")
    
    threading.Thread(target=_send).start()

def main(video_file="videos/emp1.MOV"):
    # 1. Initialize Systems
    print("Initializing Computer Vision System...")
    detector = PersonDetector()
    ocr = TextReader()
    
    # 2. Open Video
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"Error: Could not open {video_file}")
        return

    print(f"Processing {video_file}...")
    
    frame_count = 0
    # Store last 5 detected IDs to stabilize output
    id_history = []
    current_stable_id = "Scanning..."
    last_sent_id = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break # End of video
        
        frame_count += 1
        
        # 3. Detect People
        people = detector.detect(frame)

        # 4. Process Each Person
        for (x1, y1, x2, y2, conf) in people:
            # Draw Green Box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # --- OCR LOGIC (Every 30 frames) ---
            if frame_count % 30 == 0:
                h, w, _ = frame.shape
                x1_c, y1_c = max(0, x1), max(0, y1)
                x2_c, y2_c = min(w, x2), min(h, y2)
                
                person_roi = frame[y1_c:y2_c, x1_c:x2_c]
                
                if person_roi.size > 0:
                    found_id = ocr.find_employee_id(person_roi)
                    if found_id:
                        print(f"Raw OCR: {found_id}")
                        id_history.append(found_id)
                        # Keep only last 5 entries
                        if len(id_history) > 5:
                            id_history.pop(0)
                        
                        # Find most common ID
                        if id_history:
                            counts = Counter(id_history)
                            most_common, _ = counts.most_common(1)[0]
                            current_stable_id = most_common
                            
                            # SEND TO BACKEND if ID changed
                            if current_stable_id != last_sent_id:
                                send_update(current_stable_id, "Idle")
                                last_sent_id = current_stable_id

            # Display Stable ID
            label = f"{current_stable_id} ({conf:.2f})"
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # 5. Show Frame
        # Resize to fit screen
        frame_resized = cv2.resize(frame, (1280, 720)) 
        cv2.imshow("Employee Monitoring System (Press 'Q' to Quit)", frame_resized)

        # Press Q to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
