import { useState } from 'react';
import './RecoList.css';

export default function RecoList() {
  const [lang, setLang] = useState('en');

  const recos = [
    {
      en: "Consider shifting 20% of energy to solar panels to save ~160 kg CO2/month.",
      hi: "20% ऊर्जा सोलर पैनल से लेने पर ~160 kg CO2/माह बचत होगी।"
    },
    {
      en: "Moving heavy machinery to off-peak hours (10 PM–6 AM) can reduce cost by Rs.12,000/year.",
      hi: "भारी मशीनरी को ऑफ-पीक (रात 10–सुबह 6) में चलाने से Rs.12,000/वर्ष बचत होगी।"
    },
    {
      en: "Upgrade to energy-efficient LED lighting in the factory floor.",
      hi: "फैक्ट्री फ्लोर में ऊर्जा-कुशल एलईडी लाइटें लगाएं।"
    }
  ];

  return (
    <div className="card reco-list-panel">
      <div className="reco-header">
        <h3>AI Recommendations</h3>
        <button 
          className="lang-toggle" 
          onClick={() => setLang(lang === 'en' ? 'hi' : 'en')}
        >
          {lang === 'en' ? 'अ/A' : 'A/अ'}
        </button>
      </div>
      <ul className="reco-list">
        {recos.map((r, i) => (
          <li key={i} className="reco-item">
            <span className="reco-bullet">•</span>
            <span className="reco-text">{r[lang]}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
