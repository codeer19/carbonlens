import { useState } from 'react';
import './SimulatorPanel.css';

export default function SimulatorPanel({ currentKwh = 8500 }) {
  const [evPercent, setEvPercent] = useState(0);
  const [solarPercent, setSolarPercent] = useState(0);
  
  // Basic frontend calculation based on backend logic
  // CO2 saved = (ev_percent × 22) + (solar_percent × 8)
  // Cost saved = CO2_saved × 0.716 × 8 × 12 / 1000
  const co2Saved = (evPercent * 22) + (solarPercent * 8);
  const costSaved = co2Saved * 0.716 * 8 * 12 / 1000;

  return (
    <div className="card simulator-panel">
      <h3>Scenario Simulator</h3>
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
        </div>
      </div>
      
      <div className="sim-results">
        <div className="sim-stat">
          <span className="sim-label">Est. CO₂ Saved</span>
          <span className="sim-value good">-{Math.round(co2Saved)} kg/mo</span>
        </div>
        <div className="sim-stat">
          <span className="sim-label">Est. Cost Saved</span>
          <span className="sim-value">₹{Math.round(costSaved).toLocaleString()}/yr</span>
        </div>
      </div>
    </div>
  );
}
