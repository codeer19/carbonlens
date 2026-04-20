import CarbonChart from './CarbonChart';
import ScoreRing from './ScoreRing';
import SimulatorPanel from './SimulatorPanel';
import RecoList from './RecoList';
import './Dashboard.css';

export default function Dashboard() {
  const chartData = [
    { month: 'Oct', actual: 3800, forecast: null },
    { month: 'Nov', actual: 4100, forecast: null },
    { month: 'Dec', actual: 3950, forecast: null },
    { month: 'Jan', actual: 4050, forecast: 4050 },
    { month: 'Feb', actual: null, forecast: 4200 },
    { month: 'Mar', actual: null, forecast: 4350 },
  ];

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <div className="header-actions">
          <button className="btn btn-secondary">Download Report</button>
        </div>
      </div>

      <div className="grid-4">
        <div className="card metric-card">
          <h3>This Month CO₂</h3>
          <div className="metric-value">2,890 <span className="metric-unit">kg</span></div>
          <div className="metric-trend good">↓ 4% vs last month</div>
        </div>
        <div className="card metric-card">
          <h3>30-Day Forecast</h3>
          <div className="metric-value">3,100 <span className="metric-unit">kg</span></div>
          <div className="metric-trend warning">↑ expected rise</div>
        </div>
        <div className="card metric-card">
          <h3>Energy Consumed</h3>
          <div className="metric-value">4,050 <span className="metric-unit">kWh</span></div>
        </div>
        <div className="card metric-card">
          <h3>Potential Savings</h3>
          <div className="metric-value">₹12k <span className="metric-unit">/yr</span></div>
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
          <ScoreRing score={75} grade="B+" />
          <p className="score-desc">Good progress! Implementing AI insights can improve your score to A.</p>
        </div>
      </div>

      <div className="grid-2">
        <SimulatorPanel />
        <RecoList />
      </div>
    </div>
  );
}
