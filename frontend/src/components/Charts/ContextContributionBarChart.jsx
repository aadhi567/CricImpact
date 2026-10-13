import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Cell,
} from 'recharts';

const SEGMENTS = [
  { key: 'first_innings_contribution', name: '1st Inn', color: '#B8B8B8' },
  { key: 'chase_contribution', name: 'Chase', color: '#D4AF57' },
  { key: 'powerplay_contribution', name: 'Powerplay', color: '#E1C878' },
  { key: 'middle_over_contribution', name: 'Middle', color: '#858585' },
  { key: 'death_over_contribution', name: 'Death', color: '#A8893D' },
  { key: 'high_pressure_contribution', name: 'High Pressure', color: '#5A9E60' },
];

function CustomTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-[#161616] border border-[#2D2D2D] rounded-lg p-3 text-xs shadow-xl text-[#F2F2F2]">
        <div className="font-bold text-[#F2F2F2]">{data.name}</div>
        <div className="mt-1 pt-1 border-t border-[#2D2D2D]">
          {data.score !== null ? (
            <div className="text-[#D4AF57] font-bold tabular-nums font-mono">
              Contribution Score: {data.score.toFixed(1)} / 100
            </div>
          ) : (
            <div className="text-[#858585]">Not Observed (N/A)</div>
          )}
        </div>
      </div>
    );
  }
  return null;
}

export default function ContextContributionBarChart({ breakdown = {} }) {
  const chartData = SEGMENTS.map((seg) => {
    const val = breakdown[seg.key];
    const isNull = val === null || val === undefined;
    return {
      name: seg.name,
      score: isNull ? null : Number(val),
      color: seg.color,
    };
  });

  return (
    <div className="bg-[#161616] rounded-xl p-5 border border-[#2D2D2D]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2] tracking-tight">
            Phase and context comparison chart
          </h3>
          <p className="text-[12px] font-normal text-[#858585] mt-0.5">
            Contribution Score across innings type, match phases, and high-pressure situations.
          </p>
        </div>
        <div className="text-[11px] text-[#D4AF57] bg-[#101010] px-2.5 py-1 rounded border border-[#D4AF57]/40 font-mono font-semibold">
          Par = 50.0
        </div>
      </div>

      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 15, bottom: 20, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
            <XAxis dataKey="name" stroke="#858585" tick={{ fontSize: 11, fill: '#858585' }} />
            <YAxis
              domain={[0, 100]}
              stroke="#858585"
              tick={{ fontSize: 11, fill: '#858585' }}
              label={{ value: 'Score (0–100)', angle: -90, position: 'insideLeft', fill: '#858585', fontSize: 11, offset: 15 }}
            />
            <ReferenceLine y={50} stroke="#D4AF57" strokeDasharray="4 4" label={{ value: 'Par 50', fill: '#D4AF57', fontSize: 10, position: 'right' }} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="score" radius={[3, 3, 0, 0]} maxBarSize={44}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 text-[11px] text-[#858585] text-center">
        * Missing bars represent phases where no innings were observed (strictly NULL / N/A).
      </div>
    </div>
  );
}
