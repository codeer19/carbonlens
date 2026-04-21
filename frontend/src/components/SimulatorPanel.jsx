import { useState, useEffect, useCallback } from 'react';
import { simulateScenario } from '../services/api';
import './SimulatorPanel.css';

export default function SimulatorPanel({ currentKwh = 8500, originalCo2 }) {
  const [evPercent, setEvPercent] = useState(0);
  const [solarPercent, setSolarPercent] = useState(0);
  const [peakShift, setPeakShift] = useState(0);
  const [loading, setLoading] = useState(false);
  const [mlResult, setMlResult] = useState(null);

  const baseCo2 = originalCo2 || Math.round(currentKwh * 0.716);

  // Debounced API call
  const fetchSimulation = useCallback(async () => {
    if (evPercent === 0 && solarPercent === 0 && peakShift === 0) {
      setMlResult(null);
      return;
    }

    setLoading(true);
    try {
      const result = await simulateScenario({
        current_monthly_kwh: currentKwh || 8500,
        ev_percent: evPercent,
        solar_percent: solarPercent,
        peak_shift_hours: peakShift,
        industry: 'textile',
        state: 'maharashtra',
      });
      setMlResult(result);
    } catch (err) {
      console.error('Simulation API error:', err);
      setMlResult(null);
    } finally {
      setLoading(false);
    }
  }, [evPercent, solarPercent, peakShift, currentKwh]);

  // Debounce — call API 400ms after slider stops
  useEffect(() => {
    const timer = setTimeout(fetchSimulation, 400);
    return () => clearTimeout(timer);
  }, [fetchSimulation]);

  // Use ML result if available, else local fallback
  const totalCo2Saved = mlResult?.co2_saved_kg_month || 0;
  const newCo2 = mlResult?.new_monthly_co2_kg || Math.max(0, baseCo2 - totalCo2Saved);
  const costSaved = mlResult?.cost_saved_rs_year || 0;
  const reductionPercent = mlResult?.reduction_percent || (baseCo2 > 0 ? Math.round((totalCo2Saved / baseCo2) * 100) : 0);
  const confidenceLevel = mlResult?.confidence_level || 0;
  const confidenceRange = mlResult?.confidence_range;
  const modelUsed = mlResult?.model || 'waiting';

  return (
    <div className="simulator-panel-v2">
      <div className="sim-header-row">
        <h3 className="sim-section-title">Scenario Controls</h3>
        {modelUsed && modelUsed !== 'waiting' && (
          <span className={`sim-model-badge ${modelUsed.includes('xgboost') ? 'ml' : 'fallback'}`}>
            {modelUsed.includes('xgboost') ? '🤖 XGBoost ML' : '⚡ Heuristic'}
          </span>
        )}
      </div>
      <div className="sliders-container">
        <div className="slider-group">
          <div className="slider-header">
            <label>EV Fleet Conversion</label>
            <span className="slider-value">{evPercent}%</span>
          </div>
          <input 
            type="range" 
            min="0" 
            max="100" 
            value={evPercent} 
            onChange={(e) => setEvPercent(Number(e.target.value))} 
          />
          <div className="slider-hint">Percentage of vehicles switched to electric</div>
        </div>
        
        <div className="slider-group">
          <div className="slider-header">
            <label>Solar Energy Adoption</label>
            <span className="slider-value">{solarPercent}%</span>
          </div>
          <input 
            type="range" 
            min="0" 
            max="100" 
            value={solarPercent} 
            onChange={(e) => setSolarPercent(Number(e.target.value))} 
          />
          <div className="slider-hint">Percentage of energy sourced from solar panels</div>
        </div>

        <div className="slider-group">
          <div className="slider-header">
            <label>Off-Peak Hour Shifting</label>
            <span className="slider-value">{peakShift} hrs</span>
          </div>
          <input 
            type="range" 
            min="0" 
            max="8" 
            value={peakShift} 
            onChange={(e) => setPeakShift(Number(e.target.value))} 
          />
          <div className="slider-hint">Hours of heavy load shifted to off-peak (10 PM–6 AM)</div>
        </div>
      </div>
      
      <div className="sim-results-v2">
        <div className={`sim-result-card savings ${loading ? 'loading' : ''}`}>
          <span className="sim-result-label">CO₂ Reduced</span>
          <span className="sim-result-value">
            {loading ? '...' : `-${Math.round(totalCo2Saved).toLocaleString('en-IN')} kg/mo`}
          </span>
          {confidenceRange && !loading && (
            <span className="sim-result-range">
              Range: {Math.round(confidenceRange.co2_saved_lower).toLocaleString('en-IN')}–{Math.round(confidenceRange.co2_saved_upper).toLocaleString('en-IN')} kg
            </span>
          )}
        </div>
        <div className={`sim-result-card ${loading ? 'loading' : ''}`}>
          <span className="sim-result-label">New Monthly CO₂</span>
          <span className="sim-result-value">{loading ? '...' : `${Math.round(newCo2).toLocaleString('en-IN')} kg`}</span>
        </div>
        <div className={`sim-result-card ${loading ? 'loading' : ''}`}>
          <span className="sim-result-label">Reduction</span>
          <span className="sim-result-value">{loading ? '...' : `${reductionPercent}%`}</span>
        </div>
        <div className={`sim-result-card ${loading ? 'loading' : ''}`}>
          <span className="sim-result-label">Est. Annual Savings</span>
          <span className="sim-result-value">{loading ? '...' : `₹${Math.round(costSaved).toLocaleString('en-IN')}`}</span>
        </div>
      </div>

      {/* Confidence indicator */}
      {confidenceLevel > 0 && !loading && (
        <div className="sim-confidence">
          <div className="sim-confidence-header">
            <span>Model Confidence</span>
            <span className="sim-confidence-value">{Math.round(confidenceLevel)}%</span>
          </div>
          <div className="sim-confidence-bar">
            <div
              className="sim-confidence-fill"
              style={{
                width: `${Math.min(100, confidenceLevel)}%`,
                backgroundColor: confidenceLevel >= 80 ? '#166534' : confidenceLevel >= 60 ? '#ca8a04' : '#dc2626',
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
