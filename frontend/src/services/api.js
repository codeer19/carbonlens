/**
 * CarbonLens — API Service
 * Handles all communication with the FastAPI backend.
 * All prediction endpoints use real XGBoost ML models with confidence levels.
 */

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : `http://${window.location.hostname}:8000`;

/**
 * Scan a bill image via OCR + Groq AI extraction.
 * @param {File} file - Image file (JPEG, PNG, etc.) or scanned PDF
 * @returns {Promise<Object>} Structured bill data with confidence scores
 */
export async function scanBill(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/scan`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Scan failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Scan a bill from base64-encoded image data (camera capture).
 * @param {string} base64Data - Base64-encoded image (data URI or raw)
 * @param {string} [filename] - Optional filename
 * @returns {Promise<Object>} Structured bill data
 */
export async function scanBillBase64(base64Data, filename = 'camera_capture.jpg') {
  const res = await fetch(`${API_BASE}/scan/base64`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_data: base64Data, filename }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Scan failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Parse a PDF bill via three-layer extractor:
 *   Layer 1: PyMuPDF digital text extraction
 *   Layer 2: Tesseract OCR (for scanned/physical bills)
 *   Layer 3: Manual fallback
 * Extracted text is sent to Groq API for structured parsing.
 * @param {File} file - PDF file
 * @returns {Promise<Object>} Parsed bill data
 */
export async function parsePDF(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/parse`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === 'object' ? err.detail.error : err.detail || `Parse failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Forecast future CO2 emissions using XGBoost ML model.
 * Returns predictions with 80% confidence intervals.
 * @param {number[]} monthlyKwh - Historical monthly kWh readings
 * @param {number} horizonDays - 30, 90, or 180
 * @param {string} industry - Industry type
 * @param {string} state - Indian state
 * @returns {Promise<Object>} Forecast data with confidence bands
 */
export async function forecastEmissions(monthlyKwh, horizonDays = 90, industry = 'textile', state = 'maharashtra') {
  const res = await fetch(`${API_BASE}/forecast`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      monthly_kwh: monthlyKwh,
      horizon_days: horizonDays,
      industry,
      state,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Forecast failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Run what-if scenario simulation using XGBoost ML model.
 * Returns CO2/cost savings with confidence intervals.
 * @param {Object} params - Simulation parameters
 * @returns {Promise<Object>} Simulation results with confidence
 */
export async function simulateScenario(params) {
  const res = await fetch(`${API_BASE}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_monthly_kwh: params.current_monthly_kwh,
      ev_percent: params.ev_percent || 0,
      solar_percent: params.solar_percent || 0,
      peak_shift_hours: params.peak_shift_hours || 0,
      industry: params.industry || 'textile',
      state: params.state || 'maharashtra',
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Simulation failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Get AI-generated carbon reduction recommendations with ML-backed scoring.
 * Uses XGBoost classifier with calibrated confidence.
 * @param {number} monthlyKwh
 * @param {string} industry
 * @param {string} state
 * @returns {Promise<Object>} Recommendations with grade probabilities
 */
export async function getRecommendations(monthlyKwh = 8500, industry = 'textile', state = 'maharashtra') {
  const res = await fetch(
    `${API_BASE}/recommendations?monthly_kwh=${monthlyKwh}&industry=${industry}&state=${state}`
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Recommendations failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Get ML model status and training metrics.
 * @returns {Promise<Object>} Model status
 */
export async function getMLStatus() {
  const res = await fetch(`${API_BASE}/ml/status`);
  return res.json();
}

/**
 * Generate and download an ESG PDF report.
 * @param {Object} params - Report parameters
 * @param {string} params.company_name - Company name
 * @param {string} params.industry - Industry sector
 * @param {number} params.monthly_kwh - Monthly kWh consumption
 * @param {number} [params.co2_kg] - Monthly CO2 (auto-calculated if empty)
 * @param {number} [params.carbon_score] - Carbon score 0-100
 * @param {string} [params.grade] - Grade: A/B+/B/C/D
 * @returns {Promise<void>} Triggers PDF download
 */
export async function generateReport(params = {}) {
  const body = {
    company_name: params.company_name || 'My SME Company',
    industry: params.industry || 'Manufacturing',
    monthly_kwh: params.monthly_kwh || 8500,
    ...(params.co2_kg && { co2_kg: params.co2_kg }),
    ...(params.carbon_score && { carbon_score: params.carbon_score }),
    ...(params.grade && { grade: params.grade }),
  };

  const res = await fetch(`${API_BASE}/report/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Report generation failed: ${res.status}`);
  }

  // Download the PDF blob — force correct MIME type
  const arrayBuffer = await res.arrayBuffer();
  const blob = new Blob([arrayBuffer], { type: 'application/pdf' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = 'CarbonLens_ESG_Report.pdf';
  document.body.appendChild(a);
  a.click();
  // Cleanup after a short delay to ensure download starts
  setTimeout(() => {
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }, 200);
}

/**
 * Health check.
 * @returns {Promise<Object>}
 */
export async function healthCheck() {
  const res = await fetch(`${API_BASE}/`);
  return res.json();
}
