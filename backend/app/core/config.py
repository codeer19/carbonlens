"""
CarbonLens — Application Configuration
Loads all settings from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# LLM Configuration (Groq — Llama 3.3-70B)
# ---------------------------------------------------------------------------
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ---------------------------------------------------------------------------
# Carbon Emission Factors (India-specific)
# ---------------------------------------------------------------------------
INDIA_GRID_FACTOR = 0.716   # kg CO2 per kWh (CEA 2024)
AVG_ELECTRICITY_COST = 8    # Rs per kWh (average Indian industrial tariff)

# Fuel emission factors (kg CO2 per litre)
FUEL_EMISSION_FACTORS = {
    "diesel": 2.68,
    "petrol": 2.31,
    "lpg": 1.51,
    "cng": 2.75,  # kg CO2 per kg CNG
}

# ---------------------------------------------------------------------------
# OCR Settings
# ---------------------------------------------------------------------------
TESSERACT_PATH = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
POPPLER_PATH = os.getenv("POPPLER_PATH", None)  # Path to poppler/bin
OCR_LANG = "eng+hin"
OCR_MIN_CONFIDENCE = 60      # Minimum OCR confidence %
EXTRACTION_MIN_CONFIDENCE = 50  # Minimum LLM extraction confidence %

# ---------------------------------------------------------------------------
# App Settings
# ---------------------------------------------------------------------------
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# ---------------------------------------------------------------------------
# Upload Settings
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE_MB = 10
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"}
ALLOWED_FILE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".pdf"}

# ---------------------------------------------------------------------------
# Backward compatibility alias (used in main.py imports)
# ---------------------------------------------------------------------------
GROK_API_KEY = GROQ_API_KEY
