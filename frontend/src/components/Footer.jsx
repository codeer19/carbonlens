import './Footer.css'

function Footer() {
  return (
    <footer className="footer" id="footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <span className="footer-logo">🌿 CarbonLens</span>
          <p className="footer-tagline">India's first SME carbon intelligence platform</p>
        </div>
        <div className="footer-meta">
          <span className="footer-team">Team Kompasz · AI Nexus 2026</span>
          <span className="footer-divider">·</span>
          <span className="footer-powered">Powered by Groq AI + Tesseract OCR</span>
        </div>
      </div>
    </footer>
  )
}

export default Footer
