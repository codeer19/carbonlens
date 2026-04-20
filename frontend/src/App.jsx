import { useState } from 'react';
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

function App() {
  const [showHomepage, setShowHomepage] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [scanResult, setScanResult] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState(null);

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

  // PDF Report generation
  const handleGenerateReport = async () => {
    setReportLoading(true);
    setReportError(null);
    try {
      await generateReport({
        company_name: 'My SME Company',
        industry: 'Manufacturing',
        monthly_kwh: 8500,
      });
    } catch (err) {
      setReportError(err.message || 'Failed to generate report');
    } finally {
      setReportLoading(false);
    }
  };

  // Sample forecast data
  const forecastData = [
    { month: 'Oct', actual: 3800, forecast: null },
    { month: 'Nov', actual: 4100, forecast: null },
    { month: 'Dec', actual: 3950, forecast: null },
    { month: 'Jan', actual: 4050, forecast: 4050 },
    { month: 'Feb', actual: null, forecast: 4200 },
    { month: 'Mar', actual: null, forecast: 4350 },
    { month: 'Apr', actual: null, forecast: 4500 },
    { month: 'May', actual: null, forecast: 4400 },
    { month: 'Jun', actual: null, forecast: 4250 },
  ];

  // ── Show Homepage (Landing Page) ──
  if (showHomepage) {
    return <Homepage onGetStarted={handleGetStarted} />;
  }

  // ── Show Dashboard App ──
  return (
    <div className="app-container">
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        onBackToHome={handleBackToHome}
      />
      
      <main className="main-content">
        {/* ── Dashboard ── */}
        {activeTab === 'dashboard' && <Dashboard />}
        
        {/* ── Upload Invoice ── */}
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
        
        {/* ── Forecast ── */}
        {activeTab === 'forecast' && (
          <div>
            <h1>CO₂ Forecast</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', marginTop: '-16px', fontSize: '14px' }}>
              Predicted emissions based on your historical consumption data.
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
                    <div style={{ fontSize: '24px', fontWeight: '700' }}>4,200 <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>kg CO₂</span></div>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>90-Day Forecast</div>
                    <div style={{ fontSize: '24px', fontWeight: '700' }}>13,150 <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>kg CO₂</span></div>
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

        {/* ── Simulator ── */}
        {activeTab === 'simulator' && (
          <div>
            <h1>What-If Simulator</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', marginTop: '-16px', fontSize: '14px' }}>
              Adjust the sliders to see how switching to EVs or solar energy could reduce your carbon footprint.
            </p>
            <div style={{ maxWidth: '600px' }}>
              <SimulatorPanel currentKwh={8500} />
            </div>
          </div>
        )}

        {/* ── AI Insights ── */}
        {activeTab === 'insights' && (
          <div>
            <h1>AI Insights</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', marginTop: '-16px', fontSize: '14px' }}>
              AI-generated recommendations for reducing your carbon footprint, available in English and Hindi.
            </p>
            <div className="grid-2">
              <RecoList />
              <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', textAlign: 'center' }}>
                <h3 style={{ alignSelf: 'flex-start' }}>Carbon Grade</h3>
                <ScoreRing score={75} grade="B+" />
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                  Your current grade is <strong>B+</strong>. Implementing the AI recommendations could improve your score to <strong>A</strong>.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── ESG Report ── */}
        {activeTab === 'report' && (
          <div>
            <h1>ESG Report</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', marginTop: '-16px', fontSize: '14px' }}>
              Auto-generated Environmental, Social, and Governance report for your business.
            </p>
            <div className="card report-card" id="report-card">
              <div className="report-card-inner">
                <div className="report-icon-wrap">
                  <div className="report-icon-bg">📊</div>
                </div>
                <h2 style={{ marginBottom: '8px', fontSize: '20px' }}>Generate ESG Report</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px', maxWidth: '440px', margin: '0 auto 24px', lineHeight: '1.6' }}>
                  Generate a comprehensive ESG compliance report with environmental metrics, AI recommendations,
                  emission breakdowns, and regulatory context — all as a professional PDF document.
                </p>
                
                <div className="report-features">
                  <div className="report-feature">
                    <span className="report-feature-icon">📈</span>
                    <span>Emission Metrics</span>
                  </div>
                  <div className="report-feature">
                    <span className="report-feature-icon">🤖</span>
                    <span>AI Recommendations</span>
                  </div>
                  <div className="report-feature">
                    <span className="report-feature-icon">📋</span>
                    <span>BRSR Context</span>
                  </div>
                  <div className="report-feature">
                    <span className="report-feature-icon">💰</span>
                    <span>Savings Analysis</span>
                  </div>
                </div>

                {reportError && (
                  <div className="report-error">
                    <span>⚠️</span> {reportError}
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
                    <>📄 Generate & Download PDF</>
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
