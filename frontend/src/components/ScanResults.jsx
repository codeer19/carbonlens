import { Zap, DollarSign, Cloud, Calendar, Fuel, Building2, CheckCircle, AlertTriangle } from 'lucide-react'
import './ScanResults.css'

/**
 * ScanResults — Displays extracted bill data after scanning or PDF parsing.
 */
function ScanResults({ result, onReset }) {
  if (!result) return null

  const isSuccess = result.success
  const method = result.extraction_method === 'pdf_three_layer' ? 'PDF (Three-Layer)' : 'Image (OCR)'

  return (
    <div className="scan-results" id="scan-results">
      <div className="results-card">
        {/* Status Header */}
        <div className={`results-status ${isSuccess ? 'success' : 'failed'}`}>
          <div className="status-icon-wrap">
            {isSuccess ? <CheckCircle size={22} /> : <AlertTriangle size={22} />}
          </div>
          <div className="status-info">
            <h3 className="status-title">
              {isSuccess ? 'Data Extracted Successfully' : 'Extraction Issue'}
            </h3>
            <p className="status-method">via {method}</p>
          </div>
        </div>

        {isSuccess ? (
          <>
            {/* Data Grid */}
            <div className="results-grid">
              <DataCard
                icon={<Zap size={18} />}
                label="Electricity Consumed"
                value={result.kwh_consumed}
                unit="kWh"
                highlight
              />
              <DataCard
                icon={<DollarSign size={18} />}
                label="Total Amount"
                value={result.total_amount}
                unit="₹"
                prefix="₹"
              />
              <DataCard
                icon={<Cloud size={18} />}
                label="CO₂ Emissions"
                value={result.co2_kg}
                unit="kg CO₂"
                highlight
                accent
              />
              <DataCard
                icon={<Calendar size={18} />}
                label="Billing Date"
                value={result.billing_date || result.bill_date}
                isText
              />
              <DataCard
                icon={<Fuel size={18} />}
                label="Fuel Consumed"
                value={result.fuel_litres}
                unit="litres"
              />
              <DataCard
                icon={<Building2 size={18} />}
                label="DISCOM"
                value={result.discom_name}
                isText
              />
            </div>

            {/* Confidence Indicators */}
            {(result.ocr_confidence > 0 || result.extraction_confidence > 0) && (
              <div className="confidence-section">
                <h4 className="confidence-title">Confidence Scores</h4>
                <div className="confidence-bars">
                  {result.ocr_confidence > 0 && (
                    <ConfidenceBar label="OCR Accuracy" value={result.ocr_confidence} />
                  )}
                  {result.extraction_confidence > 0 && (
                    <ConfidenceBar label="Data Extraction" value={result.extraction_confidence} />
                  )}
                </div>
              </div>
            )}

            {/* Manual Review Warning */}
            {result.needs_manual_review && (
              <div className="review-warning">
                <AlertTriangle size={16} />
                <p>Low confidence detected. Please verify the extracted values before using them.</p>
              </div>
            )}
          </>
        ) : (
          <div className="error-detail">
            <p>{result.error || 'Could not extract data from this bill.'}</p>
            {result.raw_text_preview && (
              <details className="raw-text-details">
                <summary>View raw text</summary>
                <pre className="raw-text">{result.raw_text_preview}</pre>
              </details>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="results-actions">
          <button className="btn btn-ghost" onClick={onReset} id="btn-scan-another">
            ← Scan Another Bill
          </button>
        </div>
      </div>
    </div>
  )
}

/* Sub-components */
function DataCard({ icon, label, value, unit, prefix, isText, highlight, accent }) {
  const isEmpty = value === null || value === undefined
  const displayValue = isEmpty
    ? '—'
    : isText
      ? value
      : `${prefix || ''}${Number(value).toLocaleString('en-IN')}`

  return (
    <div className={`data-card ${highlight ? 'highlight' : ''} ${accent ? 'accent' : ''} ${isEmpty ? 'empty' : ''}`}>
      <div className="data-icon">{icon}</div>
      <div className="data-body">
        <span className="data-label">{label}</span>
        <span className="data-value">{displayValue}</span>
        {!isEmpty && !isText && unit && <span className="data-unit">{unit}</span>}
      </div>
    </div>
  )
}

function ConfidenceBar({ label, value }) {
  const color = value >= 80 ? '#166534' : value >= 60 ? '#92400E' : '#991B1B'
  return (
    <div className="conf-bar-item">
      <div className="conf-bar-header">
        <span className="conf-bar-label">{label}</span>
        <span className="conf-bar-value" style={{ color }}>{Math.round(value)}%</span>
      </div>
      <div className="conf-bar-track">
        <div className="conf-bar-fill" style={{ width: `${value}%`, background: color }}></div>
      </div>
    </div>
  )
}

export default ScanResults
