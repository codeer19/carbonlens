"""
Tesseract OCR Service for CarbonLens
Handles image-to-text extraction from electricity bills, fuel invoices, etc.
"""

import io
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
from typing import Optional, Dict, Any
import cv2
from app.core.config import TESSERACT_PATH, POPPLER_PATH


class OCRService:
    """Service for extracting text from bill images using Tesseract OCR."""
    
    def __init__(self, lang: str = 'eng+hin'):
        """
        Initialize OCR service.
        
        Args:
            lang: Tesseract language pack (default: English + Hindi)
        """
        self.lang = lang
        # Configure tesseract path
        if TESSERACT_PATH and os.path.exists(TESSERACT_PATH):
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        
        # Configure tesseract for better accuracy on bills
        self.config = '--psm 6 --oem 3'  # Assume single uniform block of text
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy.
        
        Steps:
        1. Convert to grayscale
        2. Resize to improve DPI (optimal 300 DPI)
        3. Denoise
        4. Apply adaptive thresholding
        5. Deskew if needed
        """
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Convert to numpy for OpenCV processing
        img_array = np.array(image)
        
        # Resize if too small (bills need at least 1000px width for good OCR)
        h, w = img_array.shape
        if w < 1000:
            scale = 1000 / w
            new_w = int(w * scale)
            new_h = int(h * scale)
            img_array = cv2.resize(img_array, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Denoise
        img_array = cv2.fastNlMeansDenoising(img_array, None, 10, 7, 21)
        
        # Adaptive thresholding for better contrast
        img_array = cv2.adaptiveThreshold(
            img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Convert back to PIL
        processed = Image.fromarray(img_array)
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(processed)
        processed = enhancer.enhance(2.0)
        
        return processed
    
    def extract_text(self, image_bytes: bytes, preprocess: bool = True) -> Dict[str, Any]:
        """
        Extract text from image bytes.
        
        Args:
            image_bytes: Raw image bytes (JPEG, PNG, etc.)
            preprocess: Whether to apply preprocessing
            
        Returns:
            Dict with extracted text, confidence, and metadata
        """
        try:
            # Load image from bytes
            image = Image.open(io.BytesIO(image_bytes))
            
            # Preprocess if enabled
            if preprocess:
                image = self.preprocess_image(image)
            
            # Run OCR with confidence data
            data = pytesseract.image_to_data(
                image, lang=self.lang, config=self.config,
                output_type=pytesseract.Output.DICT
            )
            
            # Build extracted text
            lines = []
            confidences = []
            
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                if int(data['conf'][i]) > 0:  # Filter low confidence
                    text = data['text'][i].strip()
                    if text:
                        lines.append(text)
                        confidences.append(int(data['conf'][i]))
            
            full_text = ' '.join(lines)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                'success': True,
                'text': full_text,
                'lines': lines,
                'confidence': avg_confidence,
                'word_count': len(lines),
                'preprocessed': preprocess
            }
            
        except Exception as e:
            return {
                'success': False,
                'text': '',
                'error': str(e),
                'confidence': 0
            }
    
    def extract_from_pdf_scan(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Convert PDF to images and extract text from each page.
        
        Args:
            pdf_bytes: Raw PDF bytes (scanned document)
            
        Returns:
            Dict with combined text from all pages
        """
        try:
            from pdf2image import convert_from_bytes
            
            # Convert PDF to images (300 DPI for good OCR)
            images = convert_from_bytes(pdf_bytes, dpi=300, poppler_path=POPPLER_PATH)
            
            all_texts = []
            page_results = []
            
            for i, image in enumerate(images):
                # Convert PIL to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                # Extract text
                result = self.extract_text(img_bytes, preprocess=True)
                page_results.append({
                    'page': i + 1,
                    'success': result['success'],
                    'confidence': result['confidence']
                })
                
                if result['success']:
                    all_texts.append(result['text'])
            
            combined_text = '\n'.join(all_texts)
            
            return {
                'success': True,
                'text': combined_text,
                'pages': len(images),
                'page_results': page_results,
                'total_confidence': sum(r['confidence'] for r in page_results) / len(page_results) if page_results else 0
            }
            
        except ImportError:
            return {
                'success': False,
                'error': 'pdf2image not installed. Run: pip install pdf2image'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Singleton instance
ocr_service = OCRService()


def extract_bill_text(image_bytes: bytes, file_type: str = 'image') -> Dict[str, Any]:
    """
    Convenience function to extract text from bill image or scanned PDF.
    
    Args:
        image_bytes: Raw file bytes
        file_type: 'image' or 'pdf'
        
    Returns:
        Extraction result dict
    """
    if file_type.lower() == 'pdf':
        return ocr_service.extract_from_pdf_scan(image_bytes)
    else:
        return ocr_service.extract_text(image_bytes, preprocess=True)
