"""
CarbonLens — Three-Layer Bill Extractor (parser.py)
=====================================================
Step 1 & 2 of the 7-step workflow.

Three-layer extraction pipeline for electricity bills and GST invoices:

  Layer 1 — DIGITAL PDF (PyMuPDF fitz)
      Extract text directly from the PDF. If the extracted text exceeds
      50 characters, it is a digitally-generated bill — use this text.

  Layer 2 — SCANNED / PHYSICAL BILL (Tesseract OCR)
      If Layer 1 returns fewer than 50 characters, the PDF is likely a
      scanned image of a physical bill. Convert the first page to a
      300 DPI PNG using PyMuPDF, open with Pillow, and run pytesseract
      with lang='eng+hin' (English + Hindi) to OCR the image.

  Layer 3 — MANUAL FALLBACK
      If both Layer 1 and Layer 2 return fewer than 50 characters,
      return a JSON response with manual_required: true.

On success from either Layer 1 or Layer 2, the extracted text is sent
to the Groq API (Llama 3.3-70B-Versatile) with a structured prompt
to extract: kwh, fuel_litres, bill_date (YYYY-MM),
total_amount, and discom_name — returned as clean JSON.

NOTE FOR WINDOWS USERS:
    Users must install the Tesseract-OCR engine separately.
    Download from: https://github.com/UB-Mannheim/tesseract/wiki
    After installation, set the path in your code or environment:
        pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    On Linux/macOS, install via package manager (apt/brew install tesseract-ocr).

Privacy-first: Only the plain extracted text (not the raw PDF/image)
is sent to the Groq API.
"""

import json
import os
import io
import re
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from app.core.config import TESSERACT_PATH

load_dotenv()

# ---------------------------------------------------------------------------
# NOTE: Users must install Tesseract engine separately and set
# tesseract_cmd path for Windows. Example:
#   pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# ---------------------------------------------------------------------------
if TESSERACT_PATH and os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

INDIA_GRID_FACTOR = 0.716  # kg CO2 per kWh (CEA 2024)

# Minimum character threshold — if extracted text is below this,
# the layer is considered to have failed.
MIN_TEXT_THRESHOLD = 50

# ---------------------------------------------------------------------------
# Grok extraction prompt
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """\
You are an expert Indian electricity bill and GST invoice parser.
Given the raw text extracted from a bill document, extract the following
fields and return ONLY valid JSON — no markdown, no explanation, no code fences:

{
  "kwh": <number or null>,
  "fuel_litres": <number or null>,
  "bill_date": "<YYYY-MM or null>",
  "total_amount": <number or null>,
  "discom_name": "<string or null>"
}

Rules:
- kwh: Total electricity consumed in kWh. Look for "Units Consumed",
  "kWh", "Energy Charges", "Total Units", or similar.
- fuel_litres: Fuel/diesel consumed in litres. Often absent in
  electricity bills — return null if not found.
- bill_date: Billing month in YYYY-MM format. Parse any Indian date
  format (DD/MM/YYYY, DD-MM-YYYY, MMM-YYYY, etc.) and convert to
  just the year-month (e.g. "2025-03").
- total_amount: Total payable amount in Indian Rupees (Rs / ₹ / INR).
  Look for "Total Amount", "Net Payable", "Grand Total", "Amount Payable".
- discom_name: Name of the electricity distribution company (DISCOM),
  e.g. "BSES Rajdhani", "Tata Power", "PSPCL", "UHBVN", "MSEDCL", etc.
  Return null if not identifiable.

If a field cannot be determined with confidence, set it to null.
Return ONLY the JSON object, nothing else.
"""


# ---------------------------------------------------------------------------
# Response schema (used by main.py via `from modules.parser import ParsedInvoice`)
# ---------------------------------------------------------------------------
class ParsedInvoice(BaseModel):
    """Structured result from the three-layer invoice parsing pipeline."""
    kwh_consumed: Optional[float] = Field(None, description="Electricity consumed in kWh")
    fuel_litres: Optional[float] = Field(None, description="Fuel consumed in litres")
    bill_date: Optional[str] = Field(None, description="Billing month (YYYY-MM)")
    total_amount: Optional[float] = Field(None, description="Total bill amount in Rs")
    discom_name: Optional[str] = Field(None, description="DISCOM / utility company name")
    co2_kg: Optional[float] = Field(None, description="Estimated CO2 in kg")
    raw_text: str = Field("", description="Raw text extracted from the PDF")
    extraction_layer: Optional[str] = Field(None, description="Which layer succeeded: 'digital', 'ocr', or None")
    manual_entry_required: bool = Field(False, description="True if auto-extraction failed")
    error: Optional[str] = Field(None, description="Error message if extraction failed")


# ---------------------------------------------------------------------------
# Layer 1 — Extract text directly from PDF using PyMuPDF (digital bills)
# ---------------------------------------------------------------------------
def layer1_extract_digital_text(pdf_bytes: bytes) -> str:
    """
    Opens a PDF from raw bytes and concatenates text from all pages.
    Returns the full extracted text. If the PDF is a scanned image,
    this will return very little or no text.
    """
    text_parts: list[str] = []

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text("text")
            if page_text:
                text_parts.append(page_text.strip())
        doc.close()
    except Exception as e:
        raise RuntimeError(f"PyMuPDF failed to read PDF: {e}")

    return "\n\n".join(text_parts)


# ---------------------------------------------------------------------------
# Layer 2 — OCR scanned bill using Tesseract (physical / scanned bills)
# ---------------------------------------------------------------------------
def layer2_ocr_scanned_bill(pdf_bytes: bytes) -> str:
    """
    Converts the first page of the PDF to a 300 DPI PNG image using
    PyMuPDF, opens it with Pillow, and runs pytesseract OCR with
    lang='eng+hin' (English + Hindi) to extract text.
    
    Returns the OCR-extracted text string.
    """
    try:
        # Open the PDF and get the first page
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc.load_page(0)  # first page only

        # Render the page to a pixmap at 300 DPI
        # Default DPI is 72; scale factor = 300 / 72 ≈ 4.17
        zoom = 300 / 72
        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)

        # Convert pixmap to PNG bytes → open with Pillow
        png_bytes = pixmap.tobytes("png")
        image = Image.open(io.BytesIO(png_bytes))

        doc.close()

        # Run Tesseract OCR with English + Hindi language support
        ocr_text = pytesseract.image_to_string(image, lang="eng+hin")

        return ocr_text.strip() if ocr_text else ""

    except Exception as e:
        raise RuntimeError(f"OCR (Tesseract) failed: {e}")


# ---------------------------------------------------------------------------
# Grok API — Send extracted text for structured field extraction
# ---------------------------------------------------------------------------
def extract_fields_with_groq(raw_text: str) -> dict:
    """
    Sends extracted bill text to the Groq API (Llama 3.3-70B) and asks for
    structured JSON output with: kwh, fuel_litres, bill_date,
    total_amount, discom_name.

    Returns parsed dict or raises on failure.
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file. "
            "Get a free key at https://console.groq.com/"
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a precise data extraction assistant. Return only valid JSON.",
            },
            {
                "role": "user",
                "content": (
                    f"{EXTRACTION_PROMPT}\n\n"
                    f"--- BEGIN BILL TEXT ---\n"
                    f"{raw_text[:8000]}\n"
                    f"--- END BILL TEXT ---"
                ),
            },
        ],
        "max_tokens": 512,
        "temperature": 0,
    }

    try:
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Groq API request failed: {e}")

    # Parse the API response
    resp_json = response.json()

    try:
        response_text = resp_json["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected Groq API response format: {e}")

    # Extract JSON from the response (handle markdown fences if any)
    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not json_match:
        raise ValueError(
            f"Groq did not return valid JSON. Response: {response_text[:300]}"
        )

    return json.loads(json_match.group())


# ---------------------------------------------------------------------------
# Main parse function — Three-layer pipeline
# ---------------------------------------------------------------------------
def parse_invoice(pdf_bytes: bytes) -> ParsedInvoice:
    """
    Three-layer bill extraction pipeline:

      Layer 1: PyMuPDF direct text extraction (digital bills)
               → if text > 50 chars, use it.

      Layer 2: Tesseract OCR on first page at 300 DPI (scanned bills)
               → if text > 50 chars, use it.

      Layer 3: Both failed → return manual_required: true.

    On success from Layer 1 or 2, sends text to Groq API for structured
    field extraction (kwh, fuel_litres, bill_date, total_amount, discom_name).
    """

    raw_text = ""
    extraction_layer = None

    # -----------------------------------------------------------------------
    # Layer 1 — Digital PDF text extraction
    # -----------------------------------------------------------------------
    try:
        digital_text = layer1_extract_digital_text(pdf_bytes)
        if len(digital_text.strip()) > MIN_TEXT_THRESHOLD:
            raw_text = digital_text
            extraction_layer = "digital"
            print(f"  [OK] Layer 1 (digital): extracted {len(raw_text)} chars")
    except RuntimeError as e:
        print(f"  [WARN] Layer 1 (digital) failed: {e}")

    # -----------------------------------------------------------------------
    # Layer 2 — OCR for scanned / physical bills
    # -----------------------------------------------------------------------
    if not extraction_layer:
        try:
            ocr_text = layer2_ocr_scanned_bill(pdf_bytes)
            if len(ocr_text.strip()) > MIN_TEXT_THRESHOLD:
                raw_text = ocr_text
                extraction_layer = "ocr"
                print(f"  [OK] Layer 2 (OCR): extracted {len(raw_text)} chars")
            else:
                print(f"  [WARN] Layer 2 (OCR): only {len(ocr_text.strip())} chars — insufficient")
        except RuntimeError as e:
            print(f"  [WARN] Layer 2 (OCR) failed: {e}")

    # -----------------------------------------------------------------------
    # Layer 3 — Both layers failed → manual entry required
    # -----------------------------------------------------------------------
    if not extraction_layer:
        print("  [ERROR] Layer 3: both extraction methods failed — manual entry required")
        return ParsedInvoice(
            raw_text=raw_text[:2000] if raw_text else "",
            extraction_layer=None,
            manual_entry_required=True,
            error=(
                "Could not extract sufficient text from this PDF. "
                "Both digital text extraction and OCR returned fewer than "
                f"{MIN_TEXT_THRESHOLD} characters. Please enter bill data manually."
            ),
        )

    # -----------------------------------------------------------------------
    # Success — Send extracted text to Groq API for structured extraction
    # -----------------------------------------------------------------------
    try:
        fields = extract_fields_with_groq(raw_text)
    except Exception as e:
        return ParsedInvoice(
            raw_text=raw_text[:2000],
            extraction_layer=extraction_layer,
            manual_entry_required=True,
            error=f"Text was extracted ({extraction_layer}) but Groq API parsing failed: {e}",
        )

    # Compute CO2 if kWh is available
    kwh = fields.get("kwh")
    co2 = round(kwh * INDIA_GRID_FACTOR, 2) if kwh else None

    # Check if we have enough structured data
    manual_required = kwh is None and fields.get("total_amount") is None

    return ParsedInvoice(
        kwh_consumed=fields.get("kwh"),
        fuel_litres=fields.get("fuel_litres"),
        bill_date=fields.get("bill_date"),
        total_amount=fields.get("total_amount"),
        discom_name=fields.get("discom_name"),
        co2_kg=co2,
        raw_text=raw_text[:2000],
        extraction_layer=extraction_layer,
        manual_entry_required=manual_required,
        error=None if not manual_required else "Groq could not extract key fields from the bill text.",
    )
