import { useState, useEffect } from 'react';
import Homepage from './components/Homepage';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import BillScanner from './components/BillScanner';
import ScanResults from './components/ScanResults';
import CarbonChart from './components/CarbonChart';
import SimulatorPanel from './components/SimulatorPanel';
import RecoList from './components/RecoList';
import ScoreRing from './components/ScoreRing';
import { generateReport } from './services/api';
import './App.css';

// LocalStorage key
const STORAGE_KEY = 'carbonlens_scan_result';

function App() {
  const [showHomepage, setShowHomepage] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState(null);

  // Restore scan result from localStorage on mount
  const [scanResult, setScanResult] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // Persist scan result to localStorage whenever it changes
  useEffect(() => {
    if (scanResult) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(scanResult));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [scanResult]);

  // Derive live values from scan result
  const liveKwh = scanResult?.kwh_consumed || 0;
  const liveCo2 = scanResult?.co2_kg || 0;
  const liveAmount = scanResult?.total_amount || 0;
  const hasData = liveKwh > 0 || liveCo2 > 0;

  // Carbon scoring logic (mirrors backend)
  const getScoreGrade = (co2) => {
    if (co2 <= 0) return { score: 0, grade: '—' };
    if (co2 < 4000) return { score: 90, grade: 'A' };
    if (co2 < 5500) return { score: 75, grade: 'B+' };
    if (co2 < 7000) return { score: 60, grade: 'B' };
    if (co2 < 8500) return { score: 45, grade: 'C' };
    return { score: 30, grade: 'D' };
  };
  const { score: carbonScore, grade: carbonGrade } = getScoreGrade(liveCo2);

  const handleScanComplete = (result) => {
    setScanResult(result);
  };

  const handleReset = () => {
    setScanResult(null);
  };

  const handleGetStarted = () => {
    setShowHomepage(false);
  };

  const handleBackToHome = () => {
    setShowHomepage(true);
  };

  // PDF Report generation — uses live scan data
  const handleGenerateReport = async () => {
    setReportLoading(true);
    setReportError(null);
    try {
      await generateReport({
        company_name: scanResult?.discom_name || 'My SME Company',
        industry: 'Manufacturing',
        monthly_kwh: liveKwh || 8500,
        co2_kg: liveCo2 || undefined,
        carbon_score: carbonScore || undefined,
        grade: carbonGrade !== '—' ? carbonGrade : undefined,
      });
    } catch (err) {
      setReportError(err.message || 'Failed to generate report');
    } finally {
      setReportLoading(false);
    }
  };

  // Build forecast data from live values
  const buildForecastData = () => {
    const base = liveCo2 || 4050;
    return [
      { month: 'Oct', actual: Math.round(base * 0.93), forecast: null },
      { month: 'Nov', actual: Math.round(base * 1.01), forecast: null },
      { month: 'Dec', actual: Math.round(base * 0.97), forecast: null },
      { month: 'Jan', actual: Math.round(base), forecast: Math.round(base) },
      { month: 'Feb', actual: null, forecast: Math.round(base * 1.04) },
      { month: 'Mar', actual: null, forecast: Math.round(base * 1.07) },
      { month: 'Apr', actual: null, forecast: Math.round(base * 1.11) },
      { month: 'May', actual: null, forecast: Math.round(base * 1.08) },
      { month: 'Jun', actual: null, forecast: Math.round(base * 1.05) },
    ];
  };

  const forecastData = buildForecastData();
  const forecast30 = forecastData.find(d => d.month === 'Feb')?.forecast || 0;
  const forecast90 = forecastData.filter(d => d.forecast && !d.actual).slice(0, 3).reduce((s, d) => s + d.forecast, 0);

  // Original CO2 for simulator
  const originalCo2 = liveKwh > 0 ? Math.round(liveKwh * 0.716) : Math.round(8500 * 0.716);

  if (showHomepage) {
    return <Homepage onGetStarted={handleGetStarted} />;
  }

  return (
    <div className="app-container">
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        onBackToHome={handleBackToHome}
      />
      
      <main className="main-content">
        {/* Dashboard */}
        {activeTab === 'dashboard' && <Dashboard scanResult={scanResult} />}
        
        {/* Upload Invoice */}
        {activeTab === 'upload' && (
          <div>
            <h1>Upload Invoice</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', marginTop: '-16px', fontSize: '14px' }}>
              Upload an image scan or a PDF bill. Both digital and scanned bills are supported.
            </p>
            {!scanResult ? (
              <BillScanner onScanComplete={handleScanComplete} />
            ) : (
              <ScanResults result={scanResult} onReset={handleReset} />
            )}
          </div>
        )}
        
        {/* Forecast */}
        {activeTab === 'forecast' && (
          <div>
            <h1>CO₂ Forecast</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', marginTop: '-16px', fontSize: '14px' }}>
              {hasData
                ? 'Predicted emissions based on your uploaded bill data.'
                : 'Upload a bill first to see personalized forecasts. Showing sample data below.'}
            </p>
            <div className="grid-2">
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3>Emissions Trend & Forecast</h3>
                  <span className="badge neutral">6-month projection</span>
                </div>
                <CarbonChart data={forecastData} />
              </div>
              <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h3>Forecast Summary</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
                  <div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>30-Day Forecast</div>
                    <div style={{ fontSize: '24px', fontWeight: '700' }}>{forecast30.toLocaleString('en-IN')} <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>kg CO₂</span></div>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>90-Day Forecast</div>
                    <div style={{ fontSize: '24px', fontWeight: '700' }}>{forecast90.toLocaleString('en-IN')} <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>kg CO₂</span></div>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Trend</div>
                    <div className="badge warning" style={{ marginTop: '4px' }}>↑ Slight upward trend</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Simulator — FULL WIDTH */}
        {activeTab === 'simulator' && (
          <div>
            <h1>What-If Simulator</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', marginTop: '-16px', fontSize: '14px' }}>
              {hasData
                ? `Simulating scenarios for your ${liveKwh.toLocaleString('en-IN')} kWh monthly consumption.`
                : 'Upload a bill to see personalized simulations. Using default values below.'}
            </p>
            <div className="simulator-page-layout">
              <div className="simulator-main-card card">
                <SimulatorPanel currentKwh={liveKwh || 8500} originalCo2={originalCo2} />
              </div>
              <div className="simulator-side">
                <div className="card">
                  <h3 style={{ marginBottom: '12px' }}>Current Baseline</h3>
                  <div className="sim-page-stat">
                    <span className="sim-page-stat-label">Monthly Energy</span>
                    <span className="sim-page-stat-value">{(liveKwh || 8500).toLocaleString('en-IN')} kWh</span>
                  </div>
                  <div className="sim-page-stat">
                    <span className="sim-page-stat-label">Monthly CO₂</span>
                    <span className="sim-page-stat-value">{originalCo2.toLocaleString('en-IN')} kg</span>
                  </div>
                  <div className="sim-page-stat">
                    <span className="sim-page-stat-label">Est. Monthly Cost</span>
                    <span className="sim-page-stat-value">₹{((liveKwh || 8500) * 8).toLocaleString('en-IN')}</span>
                  </div>
                </div>
                <div className="card">
                  <h3 style={{ marginBottom: '12px' }}>About the Simulator</h3>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7' }}>
                    Adjust EV fleet conversion and solar adoption sliders to estimate how
                    these changes could reduce your CO₂ emissions and operating costs.
                    Calculations use India's CEA 2024 grid emission factor (0.716 kg CO₂/kWh).
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* AI Insights — FULL WIDTH */}
        {activeTab === 'insights' && (
          <div>
            <h1>AI Insights</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', marginTop: '-16px', fontSize: '14px' }}>
              {hasData
                ? 'Personalized recommendations based on your uploaded bill data.'
                : 'Upload a bill to get personalized AI recommendations. Showing general tips below.'}
            </p>
            <div className="insights-page-layout">
              <div className="insights-main">
                <RecoList monthlyKwh={liveKwh} co2Kg={liveCo2} />
              </div>
              <div className="insights-side">
                <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', textAlign: 'center' }}>
                  <h3 style={{ alignSelf: 'flex-start' }}>Carbon Grade</h3>
                  {hasData ? (
                    <>
                      <ScoreRing score={carbonScore} grade={carbonGrade} />
                      <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                        Your current grade is <strong>{carbonGrade}</strong> based on {liveCo2.toLocaleString('en-IN')} kg CO₂/month.
                      </p>
                    </>
                  ) : (
                    <>
                      <ScoreRing score={0} grade="—" />
                      <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                        Upload a bill to calculate your carbon grade.
                      </p>
                    </>
                  )}
                </div>
                {hasData && (
                  <div className="card">
                    <h3 style={{ marginBottom: '12px' }}>Your Data Summary</h3>
                    <div className="sim-page-stat">
                      <span className="sim-page-stat-label">Energy Used</span>
                      <span className="sim-page-stat-value">{liveKwh.toLocaleString('en-IN')} kWh</span>
                    </div>
                    <div className="sim-page-stat">
                      <span className="sim-page-stat-label">CO₂ Emitted</span>
                      <span className="sim-page-stat-value">{liveCo2.toLocaleString('en-IN')} kg</span>
                    </div>
                    <div className="sim-page-stat">
                      <span className="sim-page-stat-label">Bill Amount</span>
                      <span className="sim-page-stat-value">₹{liveAmount.toLocaleString('en-IN')}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ESG Report */}
        {activeTab === 'report' && (
          <div>
            <h1>ESG Report</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', marginTop: '-16px', fontSize: '14px' }}>
              Auto-generated Environmental, Social, and Governance report for your business.
            </p>
            <div className="card report-card" id="report-card">
              <div className="report-card-inner">
                <div className="report-icon-wrap">
                  <div className="report-icon-bg">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#166534" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                  </div>
                </div>
                <h2 style={{ marginBottom: '8px', fontSize: '20px' }}>Generate ESG Report</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px', maxWidth: '440px', margin: '0 auto 24px', lineHeight: '1.6' }}>
                  {hasData
                    ? `Generate a report based on your ${liveKwh.toLocaleString('en-IN')} kWh consumption and ${liveCo2.toLocaleString('en-IN')} kg CO₂ emissions.`
                    : 'Upload a bill first, or generate a report with default sample data.'}
                </p>
                
                <div className="report-features">
                  <div className="report-feature">
                    <span className="report-feature-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg></span>
                    <span>Emission Metrics</span>
                  </div>
                  <div className="report-feature">
                    <span className="report-feature-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg></span>
                    <span>AI Recommendations</span>
                  </div>
                  <div className="report-feature">
                    <span className="report-feature-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></span>
                    <span>BRSR Context</span>
                  </div>
                  <div className="report-feature">
                    <span className="report-feature-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg></span>
                    <span>Savings Analysis</span>
                  </div>
                </div>

                {reportError && (
                  <div className="report-error">
                    <span>⚠</span> {reportError}
                  </div>
                )}
                
                <button 
                  className="btn report-btn" 
                  onClick={handleGenerateReport}
                  disabled={reportLoading}
                  id="btn-generate-report"
                >
                  {reportLoading ? (
                    <>
                      <span className="btn-spinner"></span>
                      Generating Report…
                    </>
                  ) : (
                    <>Generate & Download PDF</>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
