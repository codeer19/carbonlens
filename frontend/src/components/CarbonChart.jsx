import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function CarbonChart({ data }) {
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
