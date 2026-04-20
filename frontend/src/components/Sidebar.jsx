import { Home, FileUp, TrendingUp, Sliders, Lightbulb, FileText, ArrowLeft } from 'lucide-react';
import './Sidebar.css';

export default function Sidebar({ activeTab, setActiveTab, onBackToHome }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <Home size={18} /> },
    { id: 'upload', label: 'Upload Invoice', icon: <FileUp size={18} /> },
    { id: 'forecast', label: 'Forecast', icon: <TrendingUp size={18} /> },
    { id: 'simulator', label: 'Simulator', icon: <Sliders size={18} /> },
    { id: 'insights', label: 'AI Insights', icon: <Lightbulb size={18} /> },
    { id: 'report', label: 'ESG Report', icon: <FileText size={18} /> },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="logo-icon">🌿</span>
        <span className="logo-text">CarbonLens</span>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => setActiveTab(item.id)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">
        {onBackToHome && (
          <button className="nav-item back-home-btn" onClick={onBackToHome}>
            <ArrowLeft size={16} />
            <span>Back to Home</span>
          </button>
        )}
        <div className="badge neutral" style={{ marginTop: '8px' }}>SME Edition</div>
      </div>
    </aside>
  );
}
