import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, ComposedChart } from 'recharts';

export default function CarbonChart({ data, showConfidence = false }) {
  // Use ComposedChart if we have confidence bands
  const hasConfidence = data.some(d => d.confidenceLower != null || d.confidenceUpper != null);

  if (hasConfidence || showConfidence) {
    return (
      <div className="chart-wrapper">
        <ResponsiveContainer width="99%" height={280}>
          <ComposedChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <XAxis 
              dataKey="month" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#888888', fontSize: 12 }} 
              dy={10}
            />
            <YAxis 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#888888', fontSize: 12 }}
              dx={-10}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#FFFFFF', 
                border: '1px solid #E8E8E4',
                borderRadius: '7px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                fontSize: '12px'
              }}
              formatter={(value, name) => {
                if (name === 'confidenceUpper' || name === 'confidenceLower') return [null, null];
                return [value ? `${value.toLocaleString('en-IN')} kg` : '—', name];
              }}
            />
            {/* Confidence band (shaded area between lower and upper) */}
            <Area
              type="monotone"
              dataKey="confidenceUpper"
              stroke="none"
              fill="#16653420"
              fillOpacity={0.3}
              name="confidenceUpper"
              connectNulls={false}
            />
            <Area
              type="monotone"
              dataKey="confidenceLower"
              stroke="none"
              fill="#FFFFFF"
              fillOpacity={1}
              name="confidenceLower"
              connectNulls={false}
            />
            <Line 
              type="monotone" 
              dataKey="actual" 
              stroke="#111111" 
              strokeWidth={2} 
              dot={{ r: 3, fill: '#111' }} 
              activeDot={{ r: 5 }}
              connectNulls={false}
              name="Actual"
            />
            <Line 
              type="monotone" 
              dataKey="forecast" 
              stroke="#166534" 
              strokeWidth={2} 
              strokeDasharray="4 4" 
              dot={{ r: 3, fill: '#166534' }}
              connectNulls={false}
              name="Forecast"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return (
    <div className="chart-wrapper">
      <ResponsiveContainer width="99%" height={280}>
        <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <XAxis 
            dataKey="month" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#888888', fontSize: 12 }} 
            dy={10}
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#888888', fontSize: 12 }}
            dx={-10}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#FFFFFF', 
              border: '1px solid #E8E8E4',
              borderRadius: '7px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
              fontSize: '12px'
            }} 
          />
          <Line 
            type="monotone" 
            dataKey="actual" 
            stroke="#111111" 
            strokeWidth={1.5} 
            dot={{ r: 3, fill: '#111' }} 
            activeDot={{ r: 5 }}
            connectNulls={false}
            name="Actual"
          />
          <Line 
            type="monotone" 
            dataKey="forecast" 
            stroke="#166534" 
            strokeWidth={1.5} 
            strokeDasharray="4 4" 
            dot={{ r: 3, fill: '#166534' }}
            connectNulls={false}
            name="Forecast"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
