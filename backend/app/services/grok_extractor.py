"""
Grok API Integration for CarbonLens
Extracts structured data from OCR text using Grok's xAI API.
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExtractedBillData:
    """Structured bill data extracted by Grok."""
    kwh_consumed: Optional[float] = None
    billing_date: Optional[str] = None
    total_amount: Optional[float] = None
    fuel_litres: Optional[float] = None
    fuel_type: Optional[str] = None  # diesel, petrol, lpg, cng
    bill_type: str = 'electricity'  # electricity, fuel, gas
    discom_name: Optional[str] = None  # MSEB, TNEB, etc.
    meter_number: Optional[str] = None
    billing_period: Optional[str] = None
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'kwh_consumed': self.kwh_consumed,
            'billing_date': self.billing_date,
            'total_amount': self.total_amount,
            'fuel_litres': self.fuel_litres,
            'fuel_type': self.fuel_type,
            'bill_type': self.bill_type,
            'discom_name': self.discom_name,
            'meter_number': self.meter_number,
            'billing_period': self.billing_period,
            'confidence': self.confidence
        }


class GrokExtractor:
    """Service to extract structured bill data using Grok API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Grok extractor.
        
        Args:
            api_key: Grok API key (or from GROK_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('GROK_API_KEY')
        self.base_url = 'https://api.x.ai/v1/chat/completions'
        self.model = 'grok-2-latest'
    
    def _build_prompt(self, ocr_text: str) -> str:
        """
        Build extraction prompt for Grok.
        """
        prompt = f"""You are an expert at extracting structured data from Indian utility bills.
        The text below is OCR output from an electricity bill, fuel invoice, or gas bill.
        Extract the following fields and return ONLY a valid JSON object:

        Required fields:
        - kwh_consumed: Number of kWh consumed (as float, or null if not electricity bill)
        - billing_date: Bill date in YYYY-MM-DD format (or null)
        - total_amount: Total bill amount in INR (as float, or null)
        - fuel_litres: Litres of fuel if fuel bill (as float, or null)
        - fuel_type: Type of fuel - "diesel", "petrol", "lpg", "cng" (or null)
        - bill_type: "electricity", "fuel", or "gas"
        - discom_name: DISCOM/utility name like "MSEB", "TNEB", "BESCOM" (or null)
        - meter_number: Electricity meter number (or null)
        - billing_period: Billing period like "Jan 2024" or "01-01-2024 to 31-01-2024" (or null)

        Rules:
        1. Look for keywords like "units", "kWh", "consumption", "energy charges" for kwh_consumed
        2. Look for "bill date", "issue date", "date" for billing_date
        3. Look for "total amount", "net amount", "amount payable", "grand total" for total_amount
        4. Indian dates often in DD/MM/YYYY or DD-MM-YYYY format
        5. Amounts may have ₹ or Rs. prefix
        6. If a field is not found, return null (not 0)
        7. Return ONLY the JSON, no markdown, no explanations

        OCR Text:
        {ocr_text}

        JSON Output:"""
        
        return prompt
    
    def _parse_grok_response(self, response_text: str) -> ExtractedBillData:
        """
        Parse Grok's JSON response into ExtractedBillData.
        """
        try:
            # Clean up response (remove markdown code blocks if present)
            cleaned = response_text.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parse JSON
            data = json.loads(cleaned)
            
            return ExtractedBillData(
                kwh_consumed=self._parse_number(data.get('kwh_consumed')),
                billing_date=data.get('billing_date'),
                total_amount=self._parse_number(data.get('total_amount')),
                fuel_litres=self._parse_number(data.get('fuel_litres')),
                fuel_type=data.get('fuel_type'),
                bill_type=data.get('bill_type', 'electricity'),
                discom_name=data.get('discom_name'),
                meter_number=data.get('meter_number'),
                billing_period=data.get('billing_period'),
                confidence=self._calculate_confidence(data)
            )
            
        except json.JSONDecodeError as e:
            return ExtractedBillData(
                bill_type='unknown',
                confidence=0.0
            )
        except Exception as e:
            return ExtractedBillData(
                bill_type='unknown',
                confidence=0.0
            )
    
    def _parse_number(self, value: Any) -> Optional[float]:
        """Safely parse a number from various formats."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove currency symbols, commas
            cleaned = value.replace('₹', '').replace('Rs.', '').replace('Rs', '')
            cleaned = cleaned.replace(',', '').strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None
    
    def _calculate_confidence(self, data: Dict) -> float:
        """Calculate extraction confidence based on filled fields."""
        required_for_electricity = ['kwh_consumed', 'billing_date', 'total_amount']
        required_for_fuel = ['fuel_litres', 'fuel_type', 'billing_date', 'total_amount']
        
        bill_type = data.get('bill_type', 'electricity')
        
        if bill_type == 'electricity':
            required = required_for_electricity
        elif bill_type == 'fuel':
            required = required_for_fuel
        else:
            required = ['billing_date', 'total_amount']
        
        filled = sum(1 for field in required if data.get(field) is not None)
        return (filled / len(required)) * 100 if required else 0
    
    def extract(self, ocr_text: str) -> Dict[str, Any]:
        """
        Extract structured data from OCR text using Grok API.
        
        Args:
            ocr_text: Raw OCR text from Tesseract
            
        Returns:
            Dict with extracted data and metadata
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'Grok API key not configured. Set GROK_API_KEY environment variable.',
                'data': ExtractedBillData().to_dict()
            }
        
        try:
            # Import here to avoid dependency if not using Grok
            import requests
            
            prompt = self._build_prompt(ocr_text)
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': 'You extract structured data from Indian utility bills. Return only valid JSON.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.1,  # Low temp for consistent structured output
                'max_tokens': 500
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'Grok API error: {response.status_code} - {response.text}',
                    'data': ExtractedBillData().to_dict()
                }
            
            result = response.json()
            extracted_text = result['choices'][0]['message']['content']
            
            # Parse the extracted data
            bill_data = self._parse_grok_response(extracted_text)
            
            return {
                'success': True,
                'data': bill_data.to_dict(),
                'raw_response': extracted_text,
                'model': self.model
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': ExtractedBillData().to_dict()
            }


# Singleton instance (will be initialized with API key when provided)
grok_extractor: Optional[GrokExtractor] = None


def initialize_grok(api_key: Optional[str] = None):
    """Initialize the Grok extractor singleton."""
    global grok_extractor
    grok_extractor = GrokExtractor(api_key)
    return grok_extractor


def extract_bill_data(ocr_text: str) -> Dict[str, Any]:
    """
    Convenience function to extract bill data from OCR text.
    
    Args:
        ocr_text: Raw OCR text
        
    Returns:
        Extraction result dict
    """
    global grok_extractor
    if grok_extractor is None:
        # Try to initialize from environment
        grok_extractor = GrokExtractor()
    
    return grok_extractor.extract(ocr_text)
