# CarbonLens — Project Documentation

> **India's First AI-Powered Carbon Intelligence Platform for SMEs**  
> Team Kompasz · AI Nexus 2026 Hackathon

---

## Overview

CarbonLens is a full-stack web application that helps Indian Small and Medium Enterprises (SMEs) track, analyze, and reduce their carbon footprint. Users scan utility bills (electricity, fuel, gas) using OCR + AI, and receive instant CO₂ emission insights, AI-powered recommendations, carbon scoring, emission forecasting, what-if simulations, and downloadable ESG compliance reports.

---

## Tech Stack

| Layer      | Technology                                    |
|------------|-----------------------------------------------|
| Frontend   | React 19 + Vite 8, Recharts, Lucide Icons     |
| Backend    | FastAPI (Python), Uvicorn                      |
| OCR        | Tesseract OCR (pytesseract) + Pillow + OpenCV  |
| AI / LLM   | Groq API (Llama 3.3-70B) — text extraction            |
| PDF Parse  | PyMuPDF (fitz) — digital PDF text extraction   |
| Reports    | FPDF2 — ESG PDF report generation              |
| Styling    | Vanilla CSS (Inter font, minimal light theme)  |

---

## Project Structure

```
carbonlens/
├── backend/
│   ├── .env                      # Environment variables (GROK_API_KEY, etc.)
│   ├── requirements.txt          # Python dependencies
│   ├── app/
│   │   ├── main.py               # FastAPI app — all route handlers
│   │   ├── core/
│   │   │   └── config.py         # App configuration (emission factors, CORS, etc.)
│   │   ├── services/
│   │   │   ├── bill_processor.py # Main OCR + Grok pipeline orchestrator
│   │   │   ├── ocr_service.py    # Tesseract OCR wrapper (image preprocessing)
│   │   │   ├── grok_extractor.py # Groq API text → structured JSON extraction
│   │   │   └── report_generator.py # ESG PDF report builder (FPDF2)
│   │   ├── routers/              # (Placeholder route files)
│   │   ├── models/
│   │   ├── schemas/
│   │   └── utils/
│   └── modules/
│       └── parser.py             # Three-layer PDF parser (PyMuPDF → OCR → fallback)
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx               # Main app — routing between Homepage & Dashboard
│   │   ├── App.css
│   │   ├── index.css             # Global design system (CSS variables, typography)
│   │   ├── services/
│   │   │   └── api.js            # API client — all fetch calls to backend
│   │   └── components/
│   │       ├── Homepage.jsx/css  # Landing page with hero, features, CTA
│   │       ├── Sidebar.jsx/css   # Navigation sidebar
│   │       ├── Dashboard.jsx/css # Overview dashboard with metrics
│   │       ├── BillScanner.jsx/css # Triple-mode scanner (Camera, Image, PDF)
│   │       ├── ScanResults.jsx/css # Extracted data display with confidence
│   │       ├── CarbonChart.jsx   # Recharts line chart (actual vs forecast)
│   │       ├── ScoreRing.jsx     # SVG circular carbon grade display
│   │       ├── SimulatorPanel.jsx/css # EV + Solar what-if sliders
│   │       ├── RecoList.jsx/css  # AI recommendations (English + Hindi)
│   │       ├── Header.jsx/css    # Page header
│   │       └── Footer.jsx/css    # Page footer
├── database/
├── docs/
├── test_data/
└── uploads/
```

---

## API Endpoints

| Method | Endpoint              | Description                                    |
|--------|-----------------------|------------------------------------------------|
| GET    | `/`                   | Health check — returns app status               |
| GET    | `/health`             | Detailed health check (Tesseract, Groq status) |
| POST   | `/scan`               | Scan bill image via OCR + Groq AI extraction    |
| POST   | `/scan/base64`        | Scan from base64-encoded image (camera capture)|
| POST   | `/parse`              | Parse PDF bill (PyMuPDF + OCR + Groq)           |
| POST   | `/forecast`           | Predict CO₂ for 30/90/180 days                 |
| POST   | `/simulate`           | Run what-if scenario simulation                 |
| GET    | `/recommendations`    | Get AI reduction recommendations (EN + HI)     |
| POST   | `/report/generate`    | Generate & download ESG PDF report              |

---

## Bill Scanning Pipeline

CarbonLens uses a dual-strategy approach for scanning bills:

### Strategy 1: Tesseract OCR → Groq Text Extraction (Llama 3.3-70B)
1. Image received → preprocessed (grayscale, threshold, denoise)
2. Tesseract OCR extracts raw text from the image
3. Raw text sent to Groq API with structured extraction prompt
4. Llama 3.3-70B returns JSON with kWh, amount, dates, DISCOM, etc.
5. CO₂ calculated using India grid factor (0.716 kg CO₂/kWh)

### Strategy 2: Groq Vision Fallback
1. If Tesseract is unavailable or returns poor text
2. Image/PDF is rendered to text via PyMuPDF or Tesseract fallback
3. Extracted text is sent to Groq Llama 3.3-70B
4. Works as a bridge for environments with/without Tesseract

### Three-Layer PDF Parser
1. **Layer 1:** PyMuPDF digital text extraction
2. **Layer 2:** Tesseract OCR fallback (for scanned PDFs)
3. **Layer 3:** Manual entry flag if both fail

---

## Frontend Pages / Tabs

1. **Homepage** — Landing page with hero section, features grid, how-it-works steps, impact stats, CTA
2. **Dashboard** — Overview with 4 metric cards, emission trend chart, carbon score ring, simulator, recommendations
3. **Upload Invoice** — Triple-mode scanner:
   - **Camera Scan** — Live webcam capture to scan hard copies directly
   - **Upload Image** — Drag & drop image files
   - **Upload PDF** — Drag & drop PDF bills
4. **Forecast** — CO₂ emission chart with 30/90/180 day projections
5. **Simulator** — What-if sliders (EV fleet %, Solar %) with live CO₂/cost savings
6. **AI Insights** — Bilingual recommendations (English + Hindi) + Carbon grade ring
7. **ESG Report** — Generate & download professional ESG compliance PDF

---

## Design System

- **Font:** Inter (Google Fonts)
- **Theme:** Light, minimal, white/cream background
- **Colors:**
  - Primary: `#111111` (dark)
  - Accent: `#166534` (forest green)
  - Background: `#FAFAF8`
  - Card: `#FFFFFF`
  - Border: `#E8E8E4`
  - Text Secondary: `#888888`
- **Cards:** White with subtle border, `border-radius: 14px`
- **Badges:** Pill-shaped with colored backgrounds
- **Animations:** Subtle hover effects, transitions

---

## India-Specific Configuration

| Parameter               | Value                  | Source      |
|-------------------------|------------------------|-------------|
| Grid Emission Factor    | 0.716 kg CO₂/kWh      | CEA 2024    |
| Avg Electricity Cost    | ₹8/kWh                | Industrial  |
| Diesel Emission Factor  | 2.68 kg CO₂/litre     | IPCC        |
| Petrol Emission Factor  | 2.31 kg CO₂/litre     | IPCC        |
| LPG Emission Factor     | 1.51 kg CO₂/litre     | IPCC        |
| CNG Emission Factor     | 2.75 kg CO₂/kg        | IPCC        |
| OCR Languages           | English + Hindi        | —           |

---

## ESG Report Contents

The auto-generated PDF report includes:
1. Executive Summary
2. Key Environmental Metrics (table)
3. Emissions Breakdown (Scope 1, 2, 3)
4. Carbon Score Analysis (A–D grading scale)
5. AI-Powered Recommendations (5 actionable items)
6. Potential Impact Summary (CO₂ & cost savings table)
7. Indian Regulatory Context (BRSR, PAT, CCTS, NAPCC)
8. Disclaimer

---

## How to Run

### Backend
```bash
cd carbonlens/backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd carbonlens/frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`, backend on `http://localhost:8000`.

### Environment Variables (.env)
```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=sqlite:///./carbonlens.db
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## Key Dependencies

### Backend (Python)
- `fastapi`, `uvicorn` — Web framework
- `pytesseract`, `pillow`, `opencv-python` — OCR pipeline
- `fpdf2` — PDF report generation
- `PyMuPDF` — PDF text extraction
- `requests` — Groq API calls
- `python-dotenv` — Environment config
- `pydantic` — Data validation

### Frontend (Node.js)
- `react` 19, `react-dom` — UI framework
- `recharts` — Charts
- `lucide-react` — Icons
- `vite` 8 — Build tool

---

## Carbon Score Grading

| Grade | Score Range | Description                                |
|-------|------------|--------------------------------------------|
| A     | 90–100     | Excellent — Industry leader in sustainability |
| B+    | 75–89      | Good — Above average                       |
| B     | 60–74      | Average — Meets basic standards            |
| C     | 45–59      | Below Average — Improvement needed          |
| D     | 0–44       | Poor — Urgent action required               |

---

*Built for AI Nexus 2026 by Team Kompasz*
