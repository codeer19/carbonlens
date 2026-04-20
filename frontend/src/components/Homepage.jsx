import { useState, useEffect } from 'react';
import { Leaf, Zap, BarChart3, Shield, ArrowRight, Scan, Brain, FileText, ChevronRight } from 'lucide-react';
import './Homepage.css';

export default function Homepage({ onGetStarted }) {
  const [statsVisible, setStatsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setStatsVisible(true), 300);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="homepage" id="homepage">
      {/* ── Navigation Bar ── */}
      <nav className="home-nav" id="home-nav">
        <div className="home-nav-inner">
          <div className="home-nav-brand">
            <span className="home-nav-icon">🌿</span>
            <span className="home-nav-name">CarbonLens</span>
          </div>
          <div className="home-nav-links">
            <a href="#features" className="home-nav-link">Features</a>
            <a href="#how-it-works" className="home-nav-link">How It Works</a>
            <a href="#impact" className="home-nav-link">Impact</a>
          </div>
          <div className="home-nav-actions">
            <span className="home-nav-badge">
              <span className="badge-dot"></span>
              AI Nexus 2026
            </span>
            <button className="home-nav-cta" onClick={onGetStarted}>
              Get Started <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </nav>

      {/* ── Hero Section ── */}
      <section className="hero" id="hero">
        <div className="hero-bg-pattern"></div>
        <div className="hero-content">
          <div className="hero-badge">
            <Leaf size={14} />
            <span>India's First SME Carbon Intelligence Platform</span>
          </div>
          <h1 className="hero-title">
            Track Your Carbon
            <br />
            <span className="hero-title-accent">Footprint with AI</span>
          </h1>
          <p className="hero-subtitle">
            Scan your electricity bills and fuel invoices. Get instant CO₂ emission insights,
            AI-powered recommendations, and ESG-ready reports — built for Indian SMEs.
          </p>
          <div className="hero-actions">
            <button className="hero-btn-primary" onClick={onGetStarted} id="hero-cta">
              <Scan size={18} />
              Start Scanning Bills
            </button>
            <a href="#how-it-works" className="hero-btn-secondary">
              See How It Works
              <ChevronRight size={16} />
            </a>
          </div>
          <div className="hero-trust">
            <span className="trust-item">✅ No sign-up required</span>
            <span className="trust-divider">·</span>
            <span className="trust-item">🔒 Privacy-first</span>
            <span className="trust-divider">·</span>
            <span className="trust-item">🇮🇳 Made for India</span>
          </div>
        </div>

        {/* Floating Stats */}
        <div className={`hero-stats ${statsVisible ? 'visible' : ''}`}>
          <div className="stat-card">
            <div className="stat-number">0.716</div>
            <div className="stat-label">kg CO₂/kWh</div>
            <div className="stat-desc">India Grid Factor (CEA 2024)</div>
          </div>
          <div className="stat-card accent">
            <div className="stat-number">85%</div>
            <div className="stat-label">OCR Accuracy</div>
            <div className="stat-desc">On Indian utility bills</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">&lt;30s</div>
            <div className="stat-label">Processing Time</div>
            <div className="stat-desc">Bill to insights</div>
          </div>
        </div>
      </section>

      {/* ── Features Section ── */}
      <section className="features-section" id="features">
        <div className="section-inner">
          <div className="section-header">
            <span className="section-tag">Features</span>
            <h2 className="section-title">Everything You Need for Carbon Intelligence</h2>
            <p className="section-desc">
              From bill scanning to ESG reporting — a complete platform for your sustainability journey.
            </p>
          </div>
          <div className="features-grid">
            <FeatureCard
              icon={<Scan size={24} />}
              title="Smart Bill Scanner"
              description="Upload images or PDFs of electricity bills, fuel invoices, and gas bills. Our AI extracts all data automatically."
              tag="OCR + AI"
            />
            <FeatureCard
              icon={<BarChart3 size={24} />}
              title="Emission Forecasting"
              description="Predict your CO₂ emissions for 30, 90, or 180 days ahead using historical consumption data."
              tag="Predictive"
            />
            <FeatureCard
              icon={<Zap size={24} />}
              title="What-If Simulator"
              description="Explore scenarios: What if you switch 20% to solar? 30% fleet to EVs? See the CO₂ and cost impact instantly."
              tag="Interactive"
            />
            <FeatureCard
              icon={<Brain size={24} />}
              title="AI Recommendations"
              description="Get personalized, actionable suggestions in English and Hindi to reduce emissions and save costs."
              tag="Bilingual"
            />
            <FeatureCard
              icon={<Shield size={24} />}
              title="Carbon Scoring"
              description="Receive a carbon score (A to D) based on your energy usage, benchmarked against industry standards."
              tag="Grading"
            />
            <FeatureCard
              icon={<FileText size={24} />}
              title="ESG PDF Reports"
              description="Auto-generate comprehensive ESG compliance reports with charts, metrics, and recommendations. Download as PDF."
              tag="Compliance"
            />
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className="how-section" id="how-it-works">
        <div className="section-inner">
          <div className="section-header">
            <span className="section-tag">Process</span>
            <h2 className="section-title">How CarbonLens Works</h2>
            <p className="section-desc">Three simple steps from bill to carbon insights.</p>
          </div>
          <div className="steps-grid">
            <StepCard
              number="01"
              title="Upload Your Bill"
              description="Take a photo or upload a PDF of your electricity bill or fuel invoice. We support all Indian DISCOMs."
              icon="📷"
            />
            <div className="step-connector">
              <ArrowRight size={20} />
            </div>
            <StepCard
              number="02"
              title="AI Extracts Data"
              description="Our OCR + Grok AI pipeline reads the bill, extracts kWh consumed, billing amount, dates, and more."
              icon="🤖"
            />
            <div className="step-connector">
              <ArrowRight size={20} />
            </div>
            <StepCard
              number="03"
              title="Get Insights"
              description="View your CO₂ emissions, carbon score, AI recommendations, and download ESG-ready PDF reports."
              icon="📊"
            />
          </div>
        </div>
      </section>

      {/* ── Impact Section ── */}
      <section className="impact-section" id="impact">
        <div className="section-inner">
          <div className="section-header">
            <span className="section-tag">Impact</span>
            <h2 className="section-title">Why Carbon Intelligence Matters for SMEs</h2>
          </div>
          <div className="impact-grid">
            <div className="impact-card">
              <div className="impact-stat">63M+</div>
              <div className="impact-label">SMEs in India</div>
              <p className="impact-desc">Contributing ~45% of industrial emissions. Even small improvements create massive collective impact.</p>
            </div>
            <div className="impact-card accent">
              <div className="impact-stat">₹12K+</div>
              <div className="impact-label">Annual Savings</div>
              <p className="impact-desc">Average potential cost savings per SME through energy optimization and peak-hour load shifting.</p>
            </div>
            <div className="impact-card">
              <div className="impact-stat">BRSR</div>
              <div className="impact-label">ESG Compliance</div>
              <p className="impact-desc">Business Responsibility and Sustainability Reporting is becoming mandatory. Start tracking today.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA Section ── */}
      <section className="cta-section">
        <div className="cta-inner">
          <div className="cta-icon">🌿</div>
          <h2 className="cta-title">Ready to Track Your Carbon Footprint?</h2>
          <p className="cta-desc">
            Start scanning your utility bills and get instant carbon insights. No sign-up needed.
          </p>
          <button className="cta-button" onClick={onGetStarted} id="bottom-cta">
            <Scan size={18} />
            Get Started Now
            <ArrowRight size={16} />
          </button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="home-footer">
        <div className="home-footer-inner">
          <div className="home-footer-brand">
            <span>🌿 CarbonLens</span>
            <p>India's first SME carbon intelligence platform</p>
          </div>
          <div className="home-footer-meta">
            <span>Team Kompasz · AI Nexus 2026</span>
            <span className="home-footer-divider">·</span>
            <span>Powered by Grok AI + Tesseract OCR</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

/* Sub-components */
function FeatureCard({ icon, title, description, tag }) {
  return (
    <div className="feature-card">
      <div className="feature-card-icon">{icon}</div>
      <h3 className="feature-card-title">{title}</h3>
      <p className="feature-card-desc">{description}</p>
      {tag && <span className="feature-card-tag">{tag}</span>}
    </div>
  );
}

function StepCard({ number, title, description, icon }) {
  return (
    <div className="step-card">
      <div className="step-number">{number}</div>
      <div className="step-icon">{icon}</div>
      <h3 className="step-title">{title}</h3>
      <p className="step-desc">{description}</p>
    </div>
  );
}
