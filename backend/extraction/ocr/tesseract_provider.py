import io
from .base import OCRProvider

try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None

class TesseractProvider(OCRProvider):
    @property
    def provider_id(self) -> str:
        return "tesseract"

    def is_available(self) -> bool:
        if Image is None or pytesseract is None:
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract_text_from_image_bytes(
        self,
        image_bytes: bytes,
        dpi: int = 144,
    ) -> str:
        if not self.is_available():
            return ""
        
        try:
            image = Image.open(io.BytesIO(image_bytes))
            # 1. Convert to grayscale
            image = image.convert("L")
            # 2. Basic adaptive thresholding can be done via PIL ImageFilter or point,
            # but simple "L" is often enough for pytesseract basic usage.
            # point thresholding example (128):
            image = image.point(lambda x: 0 if x < 128 else 255, '1')
            
            text = pytesseract.image_to_string(image, config=f'--dpi {dpi}')
            return text
        except Exception:
            return ""
