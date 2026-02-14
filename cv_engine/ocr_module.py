import easyocr
import cv2
import numpy as np

class TextReader:
    def __init__(self, languages=['en']):
        """
        Initialize EasyOCR Reader.
        """
        print("Initializing OCR Engine (this may take a moment)...")
        # gpu=False (safer for first run), gpu=True requires CUDA
        self.reader = easyocr.Reader(languages, gpu=False)
        print("OCR Engine Ready.")

    def read_text(self, image):
        """
        Extract text from an image (crop of a person).
        Returns a list of detected strings.
        """
        # EasyOCR expects RGB, OpenCV uses BGR
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # detail=0 returns just the strings
        results = self.reader.readtext(img_rgb, detail=0)
        return results

    def find_employee_id(self, image):
        """
        Scans image for text matching 'EMP' pattern.
        Returns the ID string if found, else None.
        """
        texts = self.read_text(image)
        for text in texts:
            # Simple filter: Check for "EMP" (case insensitive)
            clean_text = text.upper().strip()
            if "EMP" in clean_text:
                return clean_text
        return None
