"""
CarbonLens — FastAPI Backend
India's first SME carbon intelligence platform.

Routes:
  POST /scan             → Scan bill image via OCR + Groq AI (Llama 3.3-70B) extraction
  POST /parse            → Upload & parse PDF bill (PyMuPDF + fallback)
  POST /forecast         → Predict CO2 for 30/90/180 days ahead
  POST /simulate         → Run what-if scenario simulation
  GET  /recommendations  → Get AI-generated reduction recommendations
"""

import os
import io
import base64
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

import sys, pathlib
# Add the 'backend' directory to sys.path so we can import 'app' and 'modules'
backend_dir = str(pathlib.Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from modules.parser import parse_invoice as run_parser, ParsedInvoice

from app.core.config import (
    GROQ_API_KEY,
    INDIA_GRID_FACTOR,
    AVG_ELECTRICITY_COST,
    CORS_ORIGINS,
    ALLOWED_IMAGE_TYPES,
    FUEL_EMISSION_FACTORS,
)
from app.services.bill_processor import BillProcessor, get_bill_processor, TESSERACT_AVAILABLE
from app.services.report_generator import generate_esg_report

# ML Predictor (XGBoost models)
try:
    from ml.inference import get_predictor, CarbonLensPredictor
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("[WARN] ML models not available — using fallback predictions")

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv()


# ---------------------------------------------------------------------------
# Pydantic request / response schemas
# ---------------------------------------------------------------------------
class ScanResponse(BaseModel):
    """Structured data extracted from a scanned bill image via OCR + Groq (Llama 3.3-70B)."""
    success: bool = Field(..., description="Whether extraction succeeded")
    kwh_consumed: Optional[float] = Field(None, description="Electricity consumed in kWh")
    fuel_litres: Optional[float] = Field(None, description="Fuel consumed in litres")
    fuel_type: Optional[str] = Field(None, description="Type of fuel")
    billing_date: Optional[str] = Field(None, description="Billing date (YYYY-MM-DD)")
    total_amount: Optional[float] = Field(None, description="Total bill amount in Rs")
    co2_kg: Optional[float] = Field(None, description="Estimated CO2 in kg")
    bill_type: str = Field(default="electricity", description="electricity, fuel, or gas")
    discom_name: Optional[str] = Field(None, description="Utility company name")
    meter_number: Optional[str] = Field(None, description="Meter number")
    billing_period: Optional[str] = Field(None, description="Billing period")
    ocr_confidence: float = Field(default=0, description="OCR confidence %")
    extraction_confidence: float = Field(default=0, description="Data extraction confidence %")
    needs_manual_review: bool = Field(default=False, description="True if low confidence")
    raw_text_preview: Optional[str] = Field(None, description="First 500 chars of OCR text")
    error: Optional[str] = Field(None, description="Error message if failed")


class ParseResponse(BaseModel):
    """Structured data extracted from an uploaded PDF bill."""
    success: bool = Field(default=True, description="Whether extraction succeeded")
    kwh_consumed: float = Field(default=0, description="Electricity consumed in kWh")
    fuel_litres: Optional[float] = Field(None, description="Fuel consumed in litres")
    billing_date: str = Field(default="unknown", description="Billing date (YYYY-MM-DD)")
    total_amount: float = Field(default=0, description="Total bill amount in Rs")
    co2_kg: float = Field(default=0, description="Estimated CO2 in kg")
    discom_name: Optional[str] = Field(None, description="DISCOM name")
    error: Optional[str] = Field(None, description="Error message if any")


class ForecastRequest(BaseModel):
    """Historical kWh readings for forecasting."""
    monthly_kwh: list[float] = Field(..., description="List of monthly kWh readings (oldest→newest)")
    horizon_days: int = Field(default=90, description="Forecast horizon: 30, 90, or 180 days")
    industry: str = Field(default="textile", description="Industry type")
    state: str = Field(default="maharashtra", description="Indian state")


class ForecastResponse(BaseModel):
    """Predicted emissions timeline with confidence intervals."""
    forecast_kwh: list[float] = Field(..., description="Predicted monthly kWh")
    forecast_co2_kg: list[float] = Field(..., description="Predicted monthly CO2 (kg)")
    confidence_lower: list[float] = Field(default=[], description="Lower bound (10th percentile)")
    confidence_upper: list[float] = Field(default=[], description="Upper bound (90th percentile)")
    confidence_level: float = Field(default=0, description="Model confidence %")
    horizon_days: int
    model: str = Field(default="xgboost", description="Model used for prediction")


class SimulateRequest(BaseModel):
    """What-if scenario inputs."""
    current_monthly_kwh: float = Field(..., description="Current monthly kWh")
    ev_percent: float = Field(default=0, ge=0, le=100, description="% fleet switched to EV")
    solar_percent: float = Field(default=0, ge=0, le=100, description="% energy from solar")
    peak_shift_hours: float = Field(default=0, ge=0, le=8, description="Hours shifted off-peak")
    industry: str = Field(default="textile", description="Industry type")
    state: str = Field(default="maharashtra", description="Indian state")


class SimulateResponse(BaseModel):
    """Scenario simulation results with confidence."""
    co2_saved_kg_month: float
    cost_saved_rs_year: float
    new_monthly_co2_kg: float
    original_monthly_co2_kg: float
    confidence_range: Optional[dict] = Field(None, description="CO2 saved lower/upper bounds")
    confidence_level: float = Field(default=0, description="Prediction confidence %")
    reduction_percent: float = Field(default=0, description="% CO2 reduction")
    model: str = Field(default="xgboost", description="Model used")


class RecommendationResponse(BaseModel):
    """AI-generated recommendations with ML-backed scoring."""
    recommendations_en: str = Field(..., description="Recommendations in English")
    recommendations_hi: str = Field(..., description="Recommendations in Hindi")
    carbon_score: int = Field(..., ge=0, le=100, description="Carbon score (0-100)")
    grade: str = Field(..., description="Grade: A / B+ / B / C / D")
    confidence: float = Field(default=0, description="Scoring model confidence %")
    grade_probabilities: Optional[dict] = Field(None, description="Probability for each grade")
    model: str = Field(default="xgboost", description="Model used")


# ---------------------------------------------------------------------------
# Bill processor singleton
# ---------------------------------------------------------------------------
bill_processor: Optional[BillProcessor] = None


def get_processor() -> BillProcessor:
    global bill_processor
    if bill_processor is None:
        bill_processor = get_bill_processor(groq_api_key=GROQ_API_KEY)
    return bill_processor


# ---------------------------------------------------------------------------
# App lifespan (startup / shutdown hooks)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — initialize processor
    print("[CarbonLens] Backend starting...")
    get_processor()
    if GROQ_API_KEY:
        print("  [OK] Groq API key configured (Llama 3.3-70B)")
    else:
        print("  [WARN] GROQ_API_KEY not set - extraction will fail")
    
    # Initialize ML predictor
    if ML_AVAILABLE:
        try:
            predictor = get_predictor()
            status = predictor.get_status()
            if status['models_loaded']:
                print("  [OK] XGBoost ML models loaded")
                print(f"       Forecast: {'✓' if status['forecast_ready'] else '✗'}")
                print(f"       Scoring:  {'✓' if status['scoring_ready'] else '✗'}")
                print(f"       Simulate: {'✓' if status['simulation_ready'] else '✗'}")
            else:
                print("  [WARN] ML models not trained yet — run: python ml/run_training.py")
        except Exception as e:
            print(f"  [WARN] ML init failed: {e}")
    else:
        print("  [WARN] ML module not available — using fallback predictions")
    
    yield
    # Shutdown
    print("[CarbonLens] Backend shutting down...")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CarbonLens API",
    description="India's first SME carbon intelligence platform — OCR + AI powered",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS — allow the React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health-check
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "app": "CarbonLens",
        "status": "running",
        "version": "0.2.0",
        "features": ["ocr_scan", "pdf_parse", "forecast", "simulate", "recommendations"],
    }


# ---------------------------------------------------------------------------
# POST /scan — PRIMARY: Scan bill image via Tesseract OCR + Groq AI (Llama 3.3-70B)
# ---------------------------------------------------------------------------
@app.post("/scan", response_model=ScanResponse)
async def scan_bill(file: UploadFile = File(...)):
    """
    Accepts an image (JPEG, PNG, WebP, BMP, TIFF) or scanned PDF of a bill.
    
    Pipeline:
    1. Tesseract OCR extracts raw text from the image
    2. Groq API (Llama 3.3-70B) parses the OCR text into structured bill data
    3. CO2 is computed using India grid emission factor
    
    Returns structured bill data with confidence scores.
    """
    # Validate file type
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    content_type = file.content_type or ""
    
    is_pdf = ext == ".pdf" or content_type == "application/pdf"
    is_image = (
        content_type in ALLOWED_IMAGE_TYPES
        or ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
    )
    
    if not is_pdf and not is_image:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type or ext}. Upload an image (JPEG, PNG) or scanned PDF."
        )
    
    # Read file bytes
    contents = await file.read()
    
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")
    
    # Determine file type for processor
    file_type = "pdf" if is_pdf else "image"
    
    # Run the OCR + Groq pipeline
    processor = get_processor()
    result = processor.process(
        file_bytes=contents,
        file_type=file_type,
        filename=filename,
    )
    
    # Extract data from result
    data = result.get("data") or {}
    ocr_info = result.get("ocr") or {}
    
    # Compute CO2
    kwh = data.get("kwh_consumed")
    fuel = data.get("fuel_litres")
    fuel_type = data.get("fuel_type")
    
    co2_kg = None
    if kwh:
        co2_kg = round(kwh * INDIA_GRID_FACTOR, 2)
    elif fuel and fuel_type and fuel_type in FUEL_EMISSION_FACTORS:
        co2_kg = round(fuel * FUEL_EMISSION_FACTORS[fuel_type], 2)
    
    return ScanResponse(
        success=result.get("success", False),
        kwh_consumed=kwh,
        fuel_litres=fuel,
        fuel_type=fuel_type,
        billing_date=data.get("billing_date"),
        total_amount=data.get("total_amount"),
        co2_kg=co2_kg,
        bill_type=data.get("bill_type") or "electricity",
        discom_name=data.get("discom_name"),
        meter_number=data.get("meter_number"),
        billing_period=data.get("billing_period"),
        ocr_confidence=ocr_info.get("confidence", 0),
        extraction_confidence=data.get("confidence", 0),
        needs_manual_review=result.get("needs_manual_review", False),
        raw_text_preview=ocr_info.get("text", "")[:500] if ocr_info.get("text") else None,
        error=result.get("error"),
    )


# ---------------------------------------------------------------------------
# POST /scan/base64 — Scan from base64-encoded image (for camera capture)
# ---------------------------------------------------------------------------
class Base64ScanRequest(BaseModel):
    """Base64-encoded image data for scanning."""
    image_data: str = Field(..., description="Base64-encoded image (data URI or raw base64)")
    filename: Optional[str] = Field(default="camera_capture.jpg", description="Optional filename")


@app.post("/scan/base64", response_model=ScanResponse)
async def scan_bill_base64(req: Base64ScanRequest):
    """
    Accepts a base64-encoded image (from camera capture or canvas).
    Strips the data URI prefix if present and processes through OCR + Groq.
    """
    try:
        # Strip data URI prefix if present (e.g., "data:image/jpeg;base64,...")
        image_data = req.image_data
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]
        
        # Decode base64
        file_bytes = base64.b64decode(image_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {e}")
    
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Decoded image is empty.")
    
    # Process through OCR + Groq
    processor = get_processor()
    result = processor.process(
        file_bytes=file_bytes,
        file_type="image",
        filename=req.filename,
    )
    
    data = result.get("data") or {}
    ocr_info = result.get("ocr") or {}
    
    kwh = data.get("kwh_consumed")
    fuel = data.get("fuel_litres")
    fuel_type = data.get("fuel_type")
    
    co2_kg = None
    if kwh:
        co2_kg = round(kwh * INDIA_GRID_FACTOR, 2)
    elif fuel and fuel_type and fuel_type in FUEL_EMISSION_FACTORS:
        co2_kg = round(fuel * FUEL_EMISSION_FACTORS[fuel_type], 2)
    
    return ScanResponse(
        success=result.get("success", False),
        kwh_consumed=kwh,
        fuel_litres=fuel,
        fuel_type=fuel_type,
        billing_date=data.get("billing_date"),
        total_amount=data.get("total_amount"),
        co2_kg=co2_kg,
        bill_type=data.get("bill_type") or "electricity",
        discom_name=data.get("discom_name"),
        meter_number=data.get("meter_number"),
        billing_period=data.get("billing_period"),
        ocr_confidence=ocr_info.get("confidence", 0),
        extraction_confidence=data.get("confidence", 0),
        needs_manual_review=result.get("needs_manual_review", False),
        raw_text_preview=ocr_info.get("text", "")[:500] if ocr_info.get("text") else None,
        error=result.get("error"),
    )


# ---------------------------------------------------------------------------
# POST /parse — SECONDARY: Upload & parse PDF bill (PyMuPDF + Claude)
# ---------------------------------------------------------------------------
@app.post("/parse", response_model=ParseResponse)
async def parse_invoice_route(file: UploadFile = File(...)):
    """
    Accepts a PDF electricity bill or GST invoice.
    Extracts kWh consumed, fuel litres, billing date, and total amount
    using PyMuPDF for text extraction + Claude API for structured parsing.
    Falls back to regex extraction, then manual_entry_required flag.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Read file bytes
    contents = await file.read()
    print(f"[CarbonLens] Parsing PDF: {file.filename} ({len(contents)} bytes)")

    try:
        # Run the real parser pipeline (PyMuPDF → Groq → regex fallback)
        result: ParsedInvoice = run_parser(contents)
        
        if result.manual_entry_required:
            print(f"  [WARN] PDF extraction failed: {result.error}")
            return ParseResponse(
                success=False,
                kwh_consumed=0,
                billing_date="unknown",
                total_amount=0,
                co2_kg=0,
                error=result.error or "Could not extract data from this bill."
            )

        print(f"  [OK] PDF extracted: {result.kwh_consumed} kWh, {result.total_amount} Rs")
        return ParseResponse(
            success=True,
            kwh_consumed=result.kwh_consumed or 0,
            fuel_litres=result.fuel_litres,
            billing_date=result.bill_date or "unknown",
            total_amount=result.total_amount or 0,
            co2_kg=result.co2_kg or 0,
            discom_name=result.discom_name,
        )
    except Exception as e:
        print(f"  [ERROR] PDF parser crashed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal parser error: {e}")


# ---------------------------------------------------------------------------
# POST /forecast — Predict CO2 for 30 / 90 / 180 days
# ---------------------------------------------------------------------------
@app.post("/forecast", response_model=ForecastResponse)
async def forecast_emissions(req: ForecastRequest):
    """
    Takes historical monthly kWh data and returns a CO2 forecast
    using trained XGBoost models with 80% confidence intervals.
    """
    if req.horizon_days not in (30, 90, 180):
        raise HTTPException(status_code=400, detail="horizon_days must be 30, 90, or 180.")

    if len(req.monthly_kwh) < 1:
        raise HTTPException(status_code=400, detail="Provide at least 1 month of kWh data.")

    # Use XGBoost ML model if available
    if ML_AVAILABLE:
        try:
            predictor = get_predictor()
            result = predictor.predict_forecast(
                monthly_kwh=req.monthly_kwh,
                horizon_days=req.horizon_days,
                industry=req.industry,
                state=req.state,
                grid_factor=INDIA_GRID_FACTOR,
            )
            return ForecastResponse(
                forecast_kwh=result["forecast_kwh"],
                forecast_co2_kg=result["forecast_co2_kg"],
                confidence_lower=result.get("confidence_lower", []),
                confidence_upper=result.get("confidence_upper", []),
                confidence_level=result.get("confidence_level", 0),
                horizon_days=req.horizon_days,
                model=result.get("model", "xgboost"),
            )
        except Exception as e:
            print(f"[WARN] ML forecast failed, using fallback: {e}")

    # --- Fallback: weighted-moving-average ---
    n = max(1, req.horizon_days // 30)
    avg_kwh = sum(req.monthly_kwh) / len(req.monthly_kwh)
    forecast_kwh = [round(avg_kwh, 2)] * n
    forecast_co2 = [round(k * INDIA_GRID_FACTOR, 2) for k in forecast_kwh]

    return ForecastResponse(
        forecast_kwh=forecast_kwh,
        forecast_co2_kg=forecast_co2,
        confidence_lower=[round(c * 0.85, 2) for c in forecast_co2],
        confidence_upper=[round(c * 1.15, 2) for c in forecast_co2],
        confidence_level=40.0,
        horizon_days=req.horizon_days,
        model="fallback_average",
    )


# ---------------------------------------------------------------------------
# POST /simulate — What-if scenario simulation
# ---------------------------------------------------------------------------
@app.post("/simulate", response_model=SimulateResponse)
async def simulate_scenario(req: SimulateRequest):
    """
    Runs a what-if analysis using trained XGBoost models.
    Returns CO2 savings, cost savings, and confidence intervals.
    """
    # Use XGBoost ML model if available
    if ML_AVAILABLE:
        try:
            predictor = get_predictor()
            result = predictor.predict_simulation(
                current_monthly_kwh=req.current_monthly_kwh,
                ev_percent=req.ev_percent,
                solar_percent=req.solar_percent,
                peak_shift_hours=req.peak_shift_hours,
                industry=req.industry,
                state=req.state,
            )
            return SimulateResponse(
                co2_saved_kg_month=result["co2_saved_kg_month"],
                cost_saved_rs_year=result["cost_saved_rs_year"],
                new_monthly_co2_kg=result["new_monthly_co2_kg"],
                original_monthly_co2_kg=result["original_monthly_co2_kg"],
                confidence_range=result.get("confidence_range"),
                confidence_level=result.get("confidence_level", 0),
                reduction_percent=result.get("reduction_percent", 0),
                model=result.get("model", "xgboost"),
            )
        except Exception as e:
            print(f"[WARN] ML simulation failed, using fallback: {e}")

    # --- Fallback ---
    original_co2 = req.current_monthly_kwh * INDIA_GRID_FACTOR
    co2_saved = (req.ev_percent * 22) + (req.solar_percent * 8)
    cost_saved = co2_saved * INDIA_GRID_FACTOR * AVG_ELECTRICITY_COST * 12 / 1000
    new_co2 = max(0, original_co2 - co2_saved)

    return SimulateResponse(
        co2_saved_kg_month=round(co2_saved, 2),
        cost_saved_rs_year=round(cost_saved, 2),
        new_monthly_co2_kg=round(new_co2, 2),
        original_monthly_co2_kg=round(original_co2, 2),
        confidence_level=35.0,
        model="fallback_linear",
    )


# ---------------------------------------------------------------------------
# GET /recommendations — AI-generated reduction tips
# ---------------------------------------------------------------------------
@app.get("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    monthly_kwh: float = 8500,
    industry: str = "textile",
    state: str = "maharashtra",
):
    """
    Returns plain-English + Hindi recommendations with ML-backed carbon scoring.
    Uses trained XGBoost classifier with calibrated confidence.
    """
    co2 = monthly_kwh * INDIA_GRID_FACTOR
    
    # Use ML scoring model if available
    score, grade, confidence, grade_probs, model_name = 0, "C", 0.0, None, "fallback"
    
    if ML_AVAILABLE:
        try:
            predictor = get_predictor()
            scoring_result = predictor.predict_score(
                monthly_kwh=monthly_kwh,
                industry=industry,
                state=state,
            )
            score = scoring_result["carbon_score"]
            grade = scoring_result["grade"]
            confidence = scoring_result.get("confidence", 0)
            grade_probs = scoring_result.get("grade_probabilities")
            model_name = scoring_result.get("model", "xgboost")
        except Exception as e:
            print(f"[WARN] ML scoring failed, using fallback: {e}")
    
    # Fallback scoring
    if model_name == "fallback":
        if co2 < 4000:
            score, grade = 90, "A"
        elif co2 < 5500:
            score, grade = 75, "B+"
        elif co2 < 7000:
            score, grade = 60, "B"
        elif co2 < 8500:
            score, grade = 45, "C"
        else:
            score, grade = 30, "D"
        confidence = 40.0

    # Generate context-aware recommendations
    reco_en, reco_hi = _generate_recommendations(co2, grade, industry, monthly_kwh)

    return RecommendationResponse(
        recommendations_en=reco_en,
        recommendations_hi=reco_hi,
        carbon_score=score,
        grade=grade,
        confidence=round(confidence, 1),
        grade_probabilities=grade_probs,
        model=model_name,
    )


def _generate_recommendations(co2: float, grade: str, industry: str, kwh: float) -> tuple:
    """Generate bilingual recommendations based on grade and industry."""
    recs_by_grade = {
        "A": {
            "en": (
                f"Excellent! Your monthly CO₂ is {co2:.0f} kg — you're an industry leader. "
                "Maintain your current practices and consider obtaining Carbon Neutral certification. "
                "Explore carbon credit trading to monetize your low footprint."
            ),
            "hi": (
                f"उत्कृष्ट! आपका मासिक CO₂ {co2:.0f} kg है — आप उद्योग में अग्रणी हैं। "
                "अपनी वर्तमान प्रथाओं को बनाए रखें और कार्बन न्यूट्रल प्रमाणन प्राप्त करने पर विचार करें।"
            ),
        },
        "B+": {
            "en": (
                f"Good performance! Your monthly CO₂ is {co2:.0f} kg. "
                f"For {industry} sector, shifting 20% energy to solar can save ~{co2*0.15:.0f} kg CO₂/month. "
                "Installing smart meters and IoT monitoring can optimize peak-hour usage by 12-18%."
            ),
            "hi": (
                f"अच्छा प्रदर्शन! आपका मासिक CO₂ {co2:.0f} kg है। "
                f"20% ऊर्जा सोलर से लेने पर ~{co2*0.15:.0f} kg CO₂/माह बचत होगी। "
                "स्मार्ट मीटर और IoT मॉनिटरिंग से पीक-आवर उपयोग 12-18% कम होगा।"
            ),
        },
        "B": {
            "en": (
                f"Your monthly CO₂ is {co2:.0f} kg — average for {industry} sector. "
                "Priority actions: (1) Switch 30% energy to solar — saves ~₹{kwh*0.3*8:.0f}/month, "
                "(2) Replace old motors with IE3/IE4 rated — 15% energy saving, "
                "(3) Shift heavy loads to off-peak hours (10 PM–6 AM) — ₹12,000/year savings."
            ),
            "hi": (
                f"आपका मासिक CO₂ {co2:.0f} kg है — {industry} क्षेत्र में औसत। "
                "प्राथमिक कदम: (1) 30% ऊर्जा सोलर से लें, "
                "(2) पुरानी मोटरों को IE3/IE4 से बदलें — 15% ऊर्जा बचत, "
                "(3) भारी लोड ऑफ-पीक (रात 10-6) में चलाएं।"
            ),
        },
        "C": {
            "en": (
                f"⚠️ Your monthly CO₂ is {co2:.0f} kg — below average for {industry}. "
                "Urgent recommendations: (1) Conduct BEE energy audit — typically finds 20-30% waste, "
                "(2) Install rooftop solar (min 40% capacity) — ROI in 3-4 years, "
                "(3) Switch fleet to EV/CNG — saves 40-60% fuel CO₂, "
                "(4) Apply for PAT scheme benefits under BEE."
            ),
            "hi": (
                f"⚠️ आपका मासिक CO₂ {co2:.0f} kg है — {industry} में औसत से कम। "
                "तत्काल सुझाव: (1) BEE ऊर्जा ऑडिट कराएं — 20-30% बर्बादी मिलती है, "
                "(2) रूफटॉप सोलर लगाएं (40% क्षमता) — 3-4 साल में ROI, "
                "(3) फ्लीट को EV/CNG में बदलें।"
            ),
        },
        "D": {
            "en": (
                f"🚨 Critical! Monthly CO₂ is {co2:.0f} kg — urgent action required. "
                "Immediate steps: (1) BEE mandatory energy audit — you may qualify for PAT penalties, "
                "(2) Install 50%+ solar capacity immediately, "
                "(3) Replace all lighting with LED (saves 40% lighting energy), "
                "(4) Implement VFDs on all motors >5 HP, "
                "(5) Consider BRSR compliance before regulatory deadlines."
            ),
            "hi": (
                f"🚨 गंभीर! मासिक CO₂ {co2:.0f} kg है — तत्काल कार्रवाई आवश्यक। "
                "तत्काल कदम: (1) BEE अनिवार्य ऊर्जा ऑडिट, "
                "(2) 50%+ सोलर क्षमता तुरंत स्थापित करें, "
                "(3) सभी लाइटिंग LED से बदलें, "
                "(4) सभी 5 HP+ मोटरों पर VFD लगाएं।"
            ),
        },
    }
    rec = recs_by_grade.get(grade, recs_by_grade["C"])
    return rec["en"], rec["hi"]


# ---------------------------------------------------------------------------
# POST /report/generate — Generate and download ESG PDF report
# ---------------------------------------------------------------------------
class ReportRequest(BaseModel):
    """Request body for ESG report generation."""
    company_name: str = Field(default="My SME Company", description="Company name")
    industry: str = Field(default="Manufacturing", description="Industry sector")
    monthly_kwh: float = Field(default=8500, description="Monthly kWh consumption")
    co2_kg: Optional[float] = Field(None, description="Monthly CO2 in kg (auto-calculated if empty)")
    carbon_score: Optional[int] = Field(None, description="Carbon score 0-100")
    grade: Optional[str] = Field(None, description="Grade: A/B+/B/C/D")


@app.post("/report/generate")
async def generate_report(req: ReportRequest):
    """
    Generate and return an ESG PDF report as a downloadable file.
    """
    # Auto-calculate CO2 if not provided
    co2 = req.co2_kg or round(req.monthly_kwh * INDIA_GRID_FACTOR, 2)
    
    # Auto-calculate score/grade if not provided
    if req.carbon_score is not None:
        score = req.carbon_score
    else:
        if co2 < 4000:
            score = 90
        elif co2 < 5500:
            score = 75
        elif co2 < 7000:
            score = 60
        elif co2 < 8500:
            score = 45
        else:
            score = 30
    
    if req.grade:
        grade = req.grade
    else:
        if score >= 90:
            grade = "A"
        elif score >= 75:
            grade = "B+"
        elif score >= 60:
            grade = "B"
        elif score >= 45:
            grade = "C"
        else:
            grade = "D"
    
    try:
        pdf_bytes = generate_esg_report(
            company_name=req.company_name,
            industry=req.industry,
            monthly_kwh=req.monthly_kwh,
            co2_kg=co2,
            carbon_score=score,
            grade=grade,
        )
        
        filename = f"CarbonLens_ESG_Report_{req.company_name.replace(' ', '_')}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")


# ---------------------------------------------------------------------------
# GET /health — Detailed health check for frontend
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    ml_status = {}
    if ML_AVAILABLE:
        try:
            predictor = get_predictor()
            ml_status = predictor.get_status()
        except Exception:
            ml_status = {"models_loaded": False}
    
    return {
        "status": "healthy",
        "tesseract_available": TESSERACT_AVAILABLE,
        "groq_configured": bool(GROQ_API_KEY),
        "ml_models": ml_status,
        "version": "0.3.0",
    }


# ---------------------------------------------------------------------------
# GET /ml/status — ML model status and training metrics
# ---------------------------------------------------------------------------
@app.get("/ml/status")
async def ml_model_status():
    """Get detailed ML model status, training metrics, and confidence info."""
    if not ML_AVAILABLE:
        return {
            "available": False,
            "message": "ML module not installed. Run: python ml/run_training.py",
        }
    try:
        predictor = get_predictor()
        status = predictor.get_status()
        return {
            "available": True,
            **status,
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
        }
