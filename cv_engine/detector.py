from ultralytics import YOLO
import cv2

class PersonDetector:
    def __init__(self, model_path='yolov8n.pt'):
        """
        Initialize the YOLOv8 model.
        Download 'yolov8n.pt' automatically if not present.
        """
        print(f"Loading YOLO model from {model_path}...")
        self.model = YOLO(model_path)
        print("Model loaded successfully.")

    def detect(self, frame):
        """
        Detect people in the frame.
        Returns a list of bounding boxes: [(x1, y1, x2, y2, confidence), ...]
        """
        results = self.model(frame, verbose=False)
        people = []

        # YOLOv8 results structure
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Class ID 0 is 'person' in COCO dataset
                if int(box.cls[0]) == 0:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    people.append((int(x1), int(y1), int(x2), int(y2), conf))
        
        return people
