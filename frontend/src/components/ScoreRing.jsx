export default function ScoreRing({ score, grade }) {
  // Score 0-100
  const radius = 60;
  const stroke = 6;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="score-ring-container" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <svg height={radius * 2} width={radius * 2}>
        <circle
          stroke="var(--border-color)"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          stroke="#111111"
          fill="transparent"
          strokeWidth={stroke}
          strokeDasharray={circumference + ' ' + circumference}
          style={{ strokeDashoffset, transition: 'stroke-dashoffset 0.5s ease-in-out' }}
          strokeLinecap="round"
          r={normalizedRadius}
          cx={radius}
          cy={radius}
          transform={`rotate(-90 ${radius} ${radius})`}
        />
        <text 
          x="50%" 
          y="45%" 
          dominantBaseline="middle" 
          textAnchor="middle" 
          fontSize="32px" 
          fontWeight="700" 
          fill="var(--text-primary)"
        >
          {grade}
        </text>
        <text 
          x="50%" 
          y="65%" 
          dominantBaseline="middle" 
          textAnchor="middle" 
          fontSize="12px" 
          fontWeight="500" 
          fill="var(--text-secondary)"
        >
          {score}/100
        </text>
      </svg>
    </div>
  );
}
