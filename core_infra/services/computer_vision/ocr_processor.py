"""OCR Processor for Computer Vision Service"""

class OCRProcessor:
    def __init__(self):
        import pytesseract
        self.tesseract = pytesseract
        
    def extract_text(self, image_data: bytes) -> str:
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(image_data))
        return self.tesseract.image_to_string(image) 