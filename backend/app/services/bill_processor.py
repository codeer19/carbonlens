"""
Bill Processing Pipeline for CarbonLens
Orchestrates: Image Upload → OCR → Groq (Llama 3.3-70B) Extraction

Supports two strategies:
  1. Tesseract OCR (if installed) → Groq text extraction
  2. Groq Vision-compatible fallback (Llama 4 Scout) — works WITHOUT Tesseract
"""

from typing import Dict, Any, Optional
from datetime import datetime
import base64
import logging
import os
import json
import re
from app.core.config import TESSERACT_PATH

logger = logging.getLogger(__name__)

# Check if Tesseract is available
TESSERACT_AVAILABLE = False
try:
    import pytesseract
    # Auto-configure Windows path
    if TESSERACT_PATH and os.path.exists(TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    
    # Quick check if tesseract binary exists and is functional
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
    logger.info("Tesseract OCR is available")
except Exception as e:
    logger.warning(f"Tesseract OCR not available: {e} — using Groq Vision fallback")


class BillProcessor:
    """
    Main bill processing pipeline.
    
    Workflow:
    1. Receive image/PDF bytes
    2. Try Tesseract OCR first (if available)
    3. If Tesseract fails or not installed → use Groq Vision fallback (PDF→image→OCR→text→Llama)
    4. Extract structured data from text via Groq (Llama 3.3-70B)
    5. Return structured bill data
    """
    
    def __init__(self, groq_api_key: Optional[str] = None):
        """
        Initialize bill processor.
        
        Args:
            groq_api_key: Groq API key for structured extraction via Llama 3.3-70B
        """
        self.groq_api_key = groq_api_key or os.getenv('GROQ_API_KEY', '')
        self.groq_base_url = 'https://api.groq.com/openai/v1/chat/completions'
        self.groq_model = 'llama-3.3-70b-versatile'
        # Multimodal model for vision/fallback tasks
        self.groq_vision_model = 'llama-3.2-90b-vision-preview'
        
        # Try to initialize OCR service if Tesseract is available
        self.ocr_service = None
        if TESSERACT_AVAILABLE:
            try:
                from .ocr_service import OCRService
                self.ocr_service = OCRService(lang='eng+hin')
            except Exception:
                pass
        
        # Try to initialize Groq extractor
        self.groq_extractor = None
        try:
            from .grok_extractor import initialize_groq, GroqExtractor
            self.groq_extractor = initialize_groq(groq_api_key) if groq_api_key else GroqExtractor()
        except Exception:
            pass
        
        # Confidence thresholds
        self.ocr_min_confidence = 60
        self.extraction_min_confidence = 50
    
    def process(self, file_bytes: bytes, file_type: str = 'image', 
                filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a bill image or PDF through the full pipeline.
        
        Strategy:
        1. If Tesseract available → try OCR first → Groq text extraction
        2. If Tesseract fails or unavailable → Groq Vision fallback (render→OCR→extract)
        """
        result = {
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'filename': filename,
            'file_type': file_type,
            'ocr': None,
            'extraction': None,
            'data': None,
            'needs_manual_review': False,
            'error': None
        }
        
        try:
            ocr_text = None
            ocr_confidence = 0
            method_used = None
            
            # ── STRATEGY 1: Try Tesseract OCR (if available) ──
            if self.ocr_service and TESSERACT_AVAILABLE:
                try:
                    logger.info(f"Trying Tesseract OCR for {filename or 'uploaded file'}")
                    if file_type.lower() == 'pdf':
                        ocr_result = self.ocr_service.extract_from_pdf_scan(file_bytes)
                    else:
                        ocr_result = self.ocr_service.extract_text(file_bytes, preprocess=True)
                    
                    if ocr_result.get('success') and len(ocr_result.get('text', '').strip()) > 30:
                        ocr_text = ocr_result['text']
                        ocr_confidence = ocr_result.get('confidence', 0)
                        method_used = 'tesseract_ocr'
                        result['ocr'] = ocr_result
                        logger.info(f"Tesseract extracted {len(ocr_text)} chars, confidence: {ocr_confidence}%")
                    else:
                        logger.warning("Tesseract returned insufficient text")
                except Exception as e:
                    logger.warning(f"Tesseract OCR failed: {e}")
            
            # ── STRATEGY 2: Groq Vision fallback (render image + send text to Llama) ──
            if not ocr_text:
                logger.info("Using Groq Vision fallback for direct image extraction")
                vision_result = self._extract_via_groq_vision(file_bytes, file_type)
                
                if vision_result.get('success'):
                    result['data'] = vision_result['data']
                    result['ocr'] = {
                        'success': True,
                        'text': vision_result.get('raw_text', ''),
                        'confidence': vision_result.get('confidence', 75),
                        'method': 'groq_vision'
                    }
                    result['success'] = True
                    result['needs_manual_review'] = vision_result.get('confidence', 75) < 60
                    logger.info("Groq Vision extraction successful")
                    return result
                else:
                    result['error'] = vision_result.get('error', 'Vision extraction failed')
                    result['needs_manual_review'] = True
                    return result
            
            # ── If we have OCR text, extract structured data with Groq ──
            if ocr_text and len(ocr_text.strip()) > 20:
                if self.groq_extractor:
                    extraction_result = self.groq_extractor.extract(ocr_text)
                    result['extraction'] = extraction_result
                    
                    if extraction_result.get('success'):
                        extraction_data = extraction_result.get('data', {})
                        validated_data = self._validate_extracted_data(extraction_data)
                        result['data'] = validated_data
                        result['success'] = True
                        
                        extraction_confidence = extraction_data.get('confidence', 0)
                        if ocr_confidence < self.ocr_min_confidence or extraction_confidence < self.extraction_min_confidence:
                            result['needs_manual_review'] = True
                    else:
                        # Groq text extraction failed, try vision as fallback
                        logger.info("Groq text extraction failed, trying vision fallback")
                        vision_result = self._extract_via_groq_vision(file_bytes, file_type)
                        if vision_result.get('success'):
                            result['data'] = vision_result['data']
                            result['success'] = True
                        else:
                            result['error'] = extraction_result.get('error', 'Extraction failed')
                            result['needs_manual_review'] = True
                else:
                    result['error'] = 'No extraction service available'
                    result['needs_manual_review'] = True
            else:
                result['error'] = 'Could not extract text from image. Tesseract OCR may not be installed or configured correctly.'
                result['needs_manual_review'] = True
                
        except Exception as e:
            logger.exception("Bill processing failed")
            result['error'] = str(e)
            result['needs_manual_review'] = True
        
        return result
    
    def _extract_via_groq_vision(self, file_bytes: bytes, file_type: str) -> Dict[str, Any]:
        """
        Send image directly to Groq Vision API (Llama 3.2-90B-Vision-Preview) for extraction.
        This works WITHOUT Tesseract — Groq handles the vision extraction natively.
        """
        if not self.groq_api_key:
            return {
                'success': False,
                'error': 'Groq API key not configured. Set GROQ_API_KEY in .env file.'
            }
        
        # Override the vision model specifically for this fallback
        self.groq_vision_model = 'llama-3.2-90b-vision-preview'
        
        try:
            import requests
            
            # Convert to base64
            b64_image = base64.b64encode(file_bytes).decode('utf-8')
            
            # Detect MIME type
            if file_type == 'pdf':
                # For PDFs, try to render first page to image using PyMuPDF
                try:
                    import fitz
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    page = doc.load_page(0)
                    zoom = 300 / 72
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    png_bytes = pix.tobytes("png")
                    doc.close()
                    b64_image = base64.b64encode(png_bytes).decode('utf-8')
                    mime_type = "image/png"
                except Exception as e:
                    logger.warning(f"PDF to image conversion failed: {e}")
                    return {'success': False, 'error': f'Cannot convert PDF to image: {e}'}
            else:
                # Detect image type from bytes
                if file_bytes[:3] == b'\xff\xd8\xff':
                    mime_type = 'image/jpeg'
                elif file_bytes[:4] == b'\x89PNG':
                    mime_type = 'image/png'
                elif file_bytes[:4] == b'RIFF':
                    mime_type = 'image/webp'
                else:
                    mime_type = 'image/jpeg'  # default
            
            # Build Groq Vision request
            prompt = """You are an expert at extracting structured data from Indian utility bills.
This is an image of an electricity bill, fuel invoice, or gas bill.
Extract the following fields and return ONLY a valid JSON object (no markdown, no explanation):

{
  "kwh_consumed": <number or null>,
  "billing_date": "<YYYY-MM-DD or null>",
  "total_amount": <number or null>,
  "fuel_litres": <number or null>,
  "fuel_type": "<diesel/petrol/lpg/cng or null>",
  "bill_type": "<electricity/fuel/gas>",
  "discom_name": "<utility company name or null>",
  "meter_number": "<meter number or null>",
  "billing_period": "<billing period string or null>"
}

Rules:
1. Look for "units", "kWh", "consumption", "energy charges" for kwh_consumed
2. Indian dates are DD/MM/YYYY or DD-MM-YYYY — convert to YYYY-MM-DD
3. Amounts may have ₹ or Rs. prefix — extract just the number
4. If a field is not found, return null
5. Return ONLY the JSON object"""

            headers = {
                'Authorization': f'Bearer {self.groq_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.groq_vision_model,
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': prompt
                            },
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:{mime_type};base64,{b64_image}'
                                }
                            }
                        ]
                    }
                ],
                'temperature': 0.1,
                'max_tokens': 600
            }
            
            response = requests.post(
                self.groq_base_url,
                headers=headers,
                json=payload,
                timeout=45
            )
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'Groq Vision API error: {response.status_code} - {response.text[:300]}'
                }
            
            resp_json = response.json()
            response_text = resp_json['choices'][0]['message']['content'].strip()
            
            # Parse JSON from response
            cleaned = response_text
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group()
            
            data = json.loads(cleaned)
            
            # Parse numbers safely
            for key in ['kwh_consumed', 'total_amount', 'fuel_litres']:
                val = data.get(key)
                if isinstance(val, str):
                    cleaned_val = val.replace('₹', '').replace('Rs.', '').replace('Rs', '').replace(',', '').strip()
                    try:
                        data[key] = float(cleaned_val)
                    except (ValueError, TypeError):
                        data[key] = None
            
            # Calculate confidence
            filled = sum(1 for k in ['kwh_consumed', 'billing_date', 'total_amount'] if data.get(k) is not None)
            confidence = (filled / 3) * 100
            data['confidence'] = confidence
            
            return {
                'success': True,
                'data': data,
                'raw_text': response_text,
                'confidence': confidence,
                'method': 'groq_vision'
            }
            
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'Could not parse Groq response as JSON: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'Groq Vision extraction failed: {e}'}
    
    def _validate_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize extracted bill data.
        """
        validated = data.copy()
        
        # Validate kWh range (reasonable for Indian SME)
        kwh = validated.get('kwh_consumed')
        if kwh is not None:
            if kwh < 0 or kwh > 1000000:  # 1M kWh is absurd for SME
                validated['kwh_consumed'] = None
                validated['confidence'] = max(0, validated.get('confidence', 0) - 20)
        
        # Validate fuel litres
        fuel = validated.get('fuel_litres')
        if fuel is not None:
            if fuel < 0 or fuel > 100000:
                validated['fuel_litres'] = None
        
        # Validate amount
        amount = validated.get('total_amount')
        if amount is not None:
            if amount < 0 or amount > 10000000:  # 1Cr is too high
                validated['total_amount'] = None
        
        # Parse date if present
        billing_date = validated.get('billing_date')
        if billing_date:
            try:
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y']:
                    try:
                        parsed = datetime.strptime(billing_date, fmt)
                        validated['billing_date'] = parsed.strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
            except Exception:
                pass  # Keep original if parsing fails
        
        return validated
    
    def process_batch(self, files: list) -> list:
        """
        Process multiple bills in batch.
        """
        results = []
        for file_info in files:
            result = self.process(
                file_bytes=file_info['bytes'],
                file_type=file_info.get('type', 'image'),
                filename=file_info.get('filename')
            )
            results.append(result)
        return results


# Factory function for dependency injection
def get_bill_processor(groq_api_key: Optional[str] = None) -> BillProcessor:
    """Get or create BillProcessor instance."""
    return BillProcessor(groq_api_key=groq_api_key)
