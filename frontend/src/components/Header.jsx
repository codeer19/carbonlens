import './Header.css'

function Header() {
  return (
    <header className="header" id="header">
      <div className="header-inner">
        <a href="/" className="header-logo" id="header-logo">
          <span className="logo-icon">🌿</span>
          <span className="logo-text">CarbonLens</span>
        </a>
        <nav className="header-nav" id="header-nav">
          <a href="#scanner" className="nav-link">Scan Bill</a>
          <a href="#how-it-works" className="nav-link">How It Works</a>
          <a href="#history" className="nav-link">History</a>
        </nav>
        <div className="header-badge">
          <span className="badge-live-dot"></span>
          AI Nexus 2026
        </div>
      </div>
    </header>
  )
}

export default Header
