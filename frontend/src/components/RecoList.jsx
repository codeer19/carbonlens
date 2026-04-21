import { useState, useEffect } from 'react';
import { getRecommendations } from '../services/api';
import './RecoList.css';

export default function RecoList({ monthlyKwh = 0, co2Kg = 0 }) {
  const [lang, setLang] = useState('en');
  const [mlData, setMlData] = useState(null);
  const [loading, setLoading] = useState(false);

  const hasData = monthlyKwh > 0 || co2Kg > 0;

  // Fetch real ML recommendations from backend
  useEffect(() => {
    async function fetchRecos() {
      setLoading(true);
      try {
        const kwh = monthlyKwh || 8500;
        const result = await getRecommendations(kwh, 'textile', 'maharashtra');
        setMlData(result);
      } catch (err) {
        console.error('Recommendations API error:', err);
        setMlData(null);
      } finally {
        setLoading(false);
      }
    }
    fetchRecos();
  }, [monthlyKwh]);

  // Parse recommendations into bullet points
  const parseRecos = (text) => {
    if (!text) return [];
    // Split by sentence-ending patterns or numbered items
    const parts = text.split(/(?:\.\s+|\n|(?=\(\d\)))/g).filter(s => s.trim().length > 10);
    return parts.map(s => s.trim().replace(/^[\d).\-]+\s*/, '').replace(/\.$/, ''));
  };

  const recoItems = mlData
    ? (lang === 'en' ? parseRecos(mlData.recommendations_en) : parseRecos(mlData.recommendations_hi))
    : [];

  const modelUsed = mlData?.model || '';
  const confidence = mlData?.confidence || 0;
  const gradeProbs = mlData?.grade_probabilities;

  return (
    <div className="card reco-list-panel">
      <div className="reco-header">
        <div className="reco-header-left">
          <h3>AI Recommendations</h3>
          {modelUsed && (
            <span className={`reco-model-badge ${modelUsed.includes('xgboost') ? 'ml' : 'fallback'}`}>
              {modelUsed.includes('xgboost') ? 'XGBoost ML' : 'Heuristic'}
            </span>
          )}
        </div>
        <button 
          className="lang-toggle" 
          onClick={() => setLang(lang === 'en' ? 'hi' : 'en')}
        >
          {lang === 'en' ? 'अ/A' : 'A/अ'}
        </button>
      </div>

      {loading ? (
        <div className="reco-loading">Loading ML recommendations...</div>
      ) : (
        <ul className="reco-list">
          {recoItems.length > 0 ? (
            recoItems.map((text, i) => (
              <li key={i} className="reco-item">
                <span className="reco-bullet">•</span>
                <span className="reco-text">{text}</span>
              </li>
            ))
          ) : (
            <li className="reco-item">
              <span className="reco-bullet">•</span>
              <span className="reco-text">
                {lang === 'en'
                  ? 'Upload a bill to get personalized energy-saving recommendations.'
                  : 'व्यक्तिगत ऊर्जा-बचत सिफारिशें पाने के लिए बिल अपलोड करें।'}
              </span>
            </li>
          )}
        </ul>
      )}

      {/* Confidence & Grade breakdown */}
      {confidence > 0 && !loading && (
        <div className="reco-confidence-section">
          <div className="reco-confidence-bar-wrap">
            <div className="reco-confidence-header">
              <span>Scoring Confidence</span>
              <span className="reco-confidence-value">{Math.round(confidence)}%</span>
            </div>
            <div className="reco-confidence-bar">
              <div
                className="reco-confidence-fill"
                style={{
                  width: `${Math.min(100, confidence)}%`,
                  backgroundColor: confidence >= 75 ? '#166534' : confidence >= 50 ? '#ca8a04' : '#dc2626',
                }}
              />
            </div>
          </div>

          {gradeProbs && (
            <div className="grade-probabilities">
              <span className="grade-prob-label">Grade Probabilities:</span>
              <div className="grade-prob-chips">
                {Object.entries(gradeProbs).map(([grade, prob]) => (
                  <span
                    key={grade}
                    className={`grade-chip ${prob > 50 ? 'active' : ''}`}
                    title={`${prob}% probability`}
                  >
                    {grade}: {Math.round(prob)}%
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
