import numpy as np
import cv2

class InteractionDetector:
    def __init__(self, proximity_threshold=100):
        """
        Initialize Interaction Logic.
        proximity_threshold: Pixel distance to consider 'Occupied'.
        """
        self.threshold = proximity_threshold

    def is_employee(self, frame, box):
        """
        Checks if the person in the box is wearing a dark blue/black uniform.
        Uses HSV color space for better illumination invariance.
        """
        x1, y1, x2, y2 = map(int, box)
        # Ensure box is within frame
        h_f, w_f, _ = frame.shape
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w_f, x2), min(h_f, y2)
        
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return False

        # Convert to HSV
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # Define range for Dark Blue / Black
        # Hue: Blue is roughly 100-140. 
        # Saturation: Can be low (blackish) or high (blueish)
        # Value: Low indicates dark colors
        lower_dark_blue = np.array([90, 40, 0])
        upper_dark_blue = np.array([150, 255, 80]) # V is max 80 (quite dark)
        
        # Also define true black/dark grey just in case lighting makes it lose color
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 40]) # Very low Value

        mask_blue = cv2.inRange(hsv_roi, lower_dark_blue, upper_dark_blue)
        mask_black = cv2.inRange(hsv_roi, lower_black, upper_black)
        
        # Combine masks
        mask = cv2.bitwise_or(mask_blue, mask_black)

        # Calculate ratio of uniform color in the bounding box
        # We focus on a much tighter center-chest area to avoid:
        # 1. Background shelves on the sides
        # 2. Pants and belts on the bottom
        # 3. Heads/Hair on the top
        h, w = mask.shape
        chest_y1 = int(0.25 * h)  # Start 25% down
        chest_y2 = int(0.45 * h)  # End 45% down
        chest_x1 = int(0.35 * w)  # Ignore 35% on left
        chest_x2 = int(0.65 * w)  # Ignore 35% on right
        
        chest_mask = mask[chest_y1:chest_y2, chest_x1:chest_x2]
        
        non_zero_pixels = cv2.countNonZero(chest_mask)
        total_pixels = chest_mask.size
        
        if total_pixels == 0:
             return False
             
        ratio = non_zero_pixels / total_pixels
        
        # If more than 45% of this very tight center area is dark blue/black, it's an employee.
        return ratio > 0.45

    def calculate_distance(self, box1, box2):
        """
        Calculate Euclidean distance between centers of two boxes.
        Box format: (x1, y1, x2, y2)
        """
        # Center of Box 1
        c1_x = (box1[0] + box1[2]) / 2
        c1_y = (box1[1] + box1[3]) / 2
        
        # Center of Box 2
        c2_x = (box2[0] + box2[2]) / 2
        c2_y = (box2[1] + box2[3]) / 2
        
        # Euclidean Distance
        return np.sqrt((c1_x - c2_x)**2 + (c1_y - c2_y)**2)
