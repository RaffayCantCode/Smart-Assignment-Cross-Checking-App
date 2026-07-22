import os
import shutil
from typing import TYPE_CHECKING
from .base import OCRProvider, OCRResult

if TYPE_CHECKING:
    from PIL import Image

class TesseractProvider(OCRProvider):
    def __init__(self):
        self._is_available = False
        self._check_tesseract()

    def _check_tesseract(self):
        try:
            import pytesseract
            # Try to find Tesseract in PATH or common Windows locations
            if not shutil.which("tesseract"):
                common_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        break
            pytesseract.get_tesseract_version()
            self._is_available = True
        except Exception:
            self._is_available = False

    @property
    def provider_id(self) -> str:
        return "tesseract"

    def is_available(self) -> bool:
        return self._is_available

    def extract_text_from_image(
        self,
        image: 'Image.Image',
    ) -> OCRResult:
        if not self.is_available():
            return OCRResult("", 0.0)
        
        try:
            import pytesseract
            
            # Simple thresholding
            image = image.convert("L").point(lambda x: 0 if x < 128 else 255, '1')

            # Use image_to_data to get text and confidence without running twice
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            lines = []
            current_line = []
            confidences = []
            
            last_block, last_par, last_line = -1, -1, -1
            
            for i in range(len(data['text'])):
                word = data['text'][i]
                conf = data['conf'][i]
                
                block_num = data['block_num'][i]
                par_num = data['par_num'][i]
                line_num = data['line_num'][i]
                
                if int(conf) > -1:
                    if (block_num, par_num, line_num) != (last_block, last_par, last_line):
                        if current_line:
                            lines.append(" ".join(current_line))
                            current_line = []
                        # Add paragraph breaks if block or par changes
                        if last_block != -1 and (block_num != last_block or par_num != last_par):
                            lines.append("") # Empty line for paragraph break
                            
                        last_block, last_par, last_line = block_num, par_num, line_num
                    
                    if word.strip():
                        current_line.append(word)
                        confidences.append(float(conf))
            
            if current_line:
                lines.append(" ".join(current_line))
                
            text = "\n".join(lines)
            mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
            
            return OCRResult(text=text.strip(), confidence=mean_conf)
        except Exception:
            return OCRResult("", 0.0)
