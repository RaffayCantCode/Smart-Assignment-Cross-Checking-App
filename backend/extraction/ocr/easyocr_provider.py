import io
from .base import OCRProvider

try:
    import easyocr
    from PIL import Image
    import numpy as np
except ImportError:
    easyocr = None
    Image = None
    np = None

class EasyOCRProvider(OCRProvider):
    def __init__(self):
        self._reader = None

    @property
    def provider_id(self) -> str:
        return "easyocr"

    def is_available(self) -> bool:
        return easyocr is not None and Image is not None and np is not None

    def _get_reader(self):
        if self._reader is None:
            # Load model lazily
            self._reader = easyocr.Reader(['en'])
        return self._reader

    def extract_text_from_image_bytes(
        self,
        image_bytes: bytes,
        dpi: int = 144,
    ) -> str:
        if not self.is_available():
            return ""
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_array = np.array(image)
            reader = self._get_reader()
            results = reader.readtext(img_array, detail=0)
            return "\n".join(results)
        except Exception:
            return ""
