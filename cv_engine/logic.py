import numpy as np

class InteractionDetector:
    def __init__(self, proximity_threshold=100):
        """
        Initialize Interaction Logic.
        proximity_threshold: Pixel distance to consider 'Occupied'.
        """
        self.threshold = proximity_threshold

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

    def is_occupied(self, employee_box, other_people_boxes):
        """
        Check if employee is close to any customer.
        Returns: (True, distance) if engaged, else (False, min_distance)
        """
        if not other_people_boxes:
            return False, float('inf')
        
        min_dist = float('inf')
        engaged = False
        
        for person_box in other_people_boxes:
            dist = self.calculate_distance(employee_box, person_box)
            if dist < min_dist:
                min_dist = dist
            
            if dist < self.threshold:
                engaged = True
                # Could break here, but let's find absolute min
        
        return engaged, min_dist
