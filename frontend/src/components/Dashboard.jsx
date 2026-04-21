import CarbonChart from './CarbonChart';
import ScoreRing from './ScoreRing';
import SimulatorPanel from './SimulatorPanel';
import RecoList from './RecoList';
import './Dashboard.css';

export default function Dashboard({ scanResult }) {
  const kwh = scanResult?.kwh_consumed || 0;
  const co2 = scanResult?.co2_kg || 0;
  const amount = scanResult?.total_amount || 0;
  const hasData = kwh > 0 || co2 > 0;

  // Score logic
  const getScoreGrade = (co2) => {
    if (co2 <= 0) return { score: 0, grade: '—' };
    if (co2 < 4000) return { score: 90, grade: 'A' };
    if (co2 < 5500) return { score: 75, grade: 'B+' };
    if (co2 < 7000) return { score: 60, grade: 'B' };
    if (co2 < 8500) return { score: 45, grade: 'C' };
    return { score: 30, grade: 'D' };
  };
  const { score, grade } = getScoreGrade(co2);

  const base = co2 || 4050;
  const chartData = [
    { month: 'Oct', actual: Math.round(base * 0.93), forecast: null },
    { month: 'Nov', actual: Math.round(base * 1.01), forecast: null },
    { month: 'Dec', actual: Math.round(base * 0.97), forecast: null },
    { month: 'Jan', actual: Math.round(base), forecast: Math.round(base) },
    { month: 'Feb', actual: null, forecast: Math.round(base * 1.04) },
    { month: 'Mar', actual: null, forecast: Math.round(base * 1.07) },
  ];

  const forecast30 = chartData.find(d => d.month === 'Feb')?.forecast || 0;

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        {!hasData && (
          <span className="badge neutral" style={{ fontSize: '12px' }}>Upload a bill to see live data</span>
        )}
      </div>

      <div className="grid-4">
        <div className="card metric-card">
          <h3>This Month CO₂</h3>
          <div className="metric-value">{hasData ? co2.toLocaleString('en-IN') : '—'} <span className="metric-unit">kg</span></div>
          {hasData && <div className="metric-trend good">from uploaded bill</div>}
        </div>
        <div className="card metric-card">
          <h3>30-Day Forecast</h3>
          <div className="metric-value">{hasData ? forecast30.toLocaleString('en-IN') : '—'} <span className="metric-unit">kg</span></div>
          {hasData && <div className="metric-trend warning">↑ projected</div>}
        </div>
        <div className="card metric-card">
          <h3>Energy Consumed</h3>
          <div className="metric-value">{hasData ? kwh.toLocaleString('en-IN') : '—'} <span className="metric-unit">kWh</span></div>
        </div>
        <div className="card metric-card">
          <h3>Bill Amount</h3>
          <div className="metric-value">{hasData ? `₹${amount.toLocaleString('en-IN')}` : '—'}</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card chart-card">
          <div className="card-header">
            <h3>Emissions Trend</h3>
            <span className="badge neutral">Last 6 Months</span>
          </div>
          <CarbonChart data={chartData} />
        </div>
        
        <div className="card score-card">
          <h3>Carbon Score</h3>
          <ScoreRing score={score} grade={grade} />
          <p className="score-desc">
            {hasData
              ? `Grade ${grade} based on ${co2.toLocaleString('en-IN')} kg CO₂/month.`
              : 'Upload a bill to calculate your carbon score.'}
          </p>
        </div>
      </div>

      <div className="grid-2">
        <SimulatorPanel currentKwh={kwh || 8500} />
        <RecoList monthlyKwh={kwh} co2Kg={co2} />
      </div>
    </div>
  );
}
