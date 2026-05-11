import easyocr
import cv2
import numpy as np
import re

class TextReader:
    def __init__(self, languages=['en']):
        print("Initializing OCR Engine (this may take a moment)...")
        self.reader = easyocr.Reader(languages, gpu=False)
        print("OCR Engine Ready.")

    def _preprocess(self, image):
        """
        Upscale and sharpen the image before OCR.
        This is the key fix for low-resolution 640x360 person crops.
        """
        # Upscale 3x using high-quality cubic interpolation
        h, w = image.shape[:2]
        image = cv2.resize(image, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)

        # Convert to grayscale (OCR is more accurate on single-channel images)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Sharpen to make text edges crisp
        sharpen_kernel = np.array([[-1, -1, -1],
                                   [-1,  9, -1],
                                   [-1, -1, -1]])
        sharpened = cv2.filter2D(gray, -1, sharpen_kernel)

        # Increase contrast
        sharpened = cv2.convertScaleAbs(sharpened, alpha=1.5, beta=10)

        return sharpened

    def _correct_id(self, text):
        """
        Fix common OCR misreads for Employee ID badges.
        """
        # Remove any leading junk characters before EMP
        text = re.sub(r'^[^E]*(?=EMP)', '', text, flags=re.IGNORECASE)

        # Replace letter O with digit 0 after underscore (EMP_O3 -> EMP_03)
        text = re.sub(r'(?<=_)O', '0', text)

        # Replace letter I or l with digit 1 (EMP_0l -> EMP_01)
        text = text.replace('_0l', '_01').replace('_0I', '_01')

        # Ensure underscore exists between EMP and number (EMP01 -> EMP_01)
        text = re.sub(r'(EMP)(\d)', r'\1_\2', text, flags=re.IGNORECASE)

        # Fix 7 → 1 confusion at the TRAILING digit position
        # OCR commonly confuses 1 and 7 in badge fonts (EMP_07 -> EMP_01)
        text = re.sub(r'(EMP_0)7$', r'\g<1>1', text)

        # Uppercase and strip whitespace
        return text.upper().strip()

    def read_text(self, image):
        """Extract text from a person crop. Returns list of strings."""
        processed = self._preprocess(image)
        results = self.reader.readtext(processed, detail=0)
        return results

    def find_employee_id(self, image):
        """
        Scans image for text matching EMP_XX pattern.
        Returns cleaned ID string if found, else None.
        """
        texts = self.read_text(image)
        for text in texts:
            clean = text.upper().strip()
            # Match anything containing EMP (loose match first)
            if "EMP" in clean:
                corrected = self._correct_id(clean)
                return corrected
        return None
