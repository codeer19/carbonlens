# CarbonLens 🌿

India's first SME carbon intelligence platform.

**Hackathon:** AI Nexus 2026, Chandigarh University  
**Team:** Kompasz (4 members)

## Problem
63M Indian SMEs produce 45% of industrial CO2 but have zero affordable tools to track or reduce it.

## Tech Stack
- **Frontend:** React + Recharts
- **Backend:** Python FastAPI
- **AI/LLM:** Claude API + LangChain
- **Forecasting:** Prophet + scikit-learn
- **Database:** SQLite (dev) / PostgreSQL (prod)

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # add your API keys
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## The 7-Step Workflow
1. Upload electricity bill PDF or GST invoice
2. AI extracts kWh, fuel litres, billing date, amount
3. Emission engine converts to kg CO2 (India grid factor: 0.716)
4. Forecast CO2 for 30/90/180 days
5. Scenario simulator runs what-if analysis
6. LLM generates recommendations in Hindi + English
7. Dashboard renders charts + auto-generates ESG PDF report
