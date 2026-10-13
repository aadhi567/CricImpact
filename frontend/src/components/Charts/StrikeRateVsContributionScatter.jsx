import React from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

function CustomTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-[#161616] border border-[#2D2D2D] rounded-lg p-3 text-xs shadow-xl text-[#F2F2F2]">
        <div className="font-bold text-[#F2F2F2]">{data.player}</div>
        <div className="text-[11px] text-[#858585]">vs {data.opponent} ({data.season})</div>
        <div className="mt-1.5 pt-1.5 border-t border-[#2D2D2D] space-y-0.5">
          <div className="text-[#858585]">
            SR: <span className="font-mono font-bold text-[#F2F2F2] tabular-nums">{data.strike_rate}</span>
          </div>
          <div className="text-[#B8B8B8]">
            Score: <span className="font-bold text-[#F2F2F2] tabular-nums">{data.runs}</span> off {data.balls}b
          </div>
          <div className="text-[#D4AF57] font-bold mt-1 tabular-nums font-mono">
            Contribution Score: {data.contribution_score}
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function StrikeRateVsContributionScatter({ data = [] }) {
  return (
    <div className="bg-[#161616] rounded-xl p-5 border border-[#2D2D2D]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2] tracking-tight">
            Strike rate vs. contribution score
          </h3>
          <p className="text-[12px] font-normal text-[#858585] mt-0.5">
            Demonstrates that strike rate alone does not dictate contextual match contribution.
          </p>
        </div>
        <div className="text-[11px] text-[#D4AF57] bg-[#101010] px-2.5 py-1 rounded border border-[#D4AF57]/40 font-mono font-semibold">
          Par = 50.0
        </div>
      </div>

      <div className="w-full h-72">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222222" />
            <XAxis
              type="number"
              dataKey="strike_rate"
              name="Strike Rate"
              domain={[0, 'auto']}
              stroke="#858585"
              tick={{ fontSize: 11, fill: '#858585' }}
              label={{ value: 'Actual Strike Rate', position: 'insideBottom', offset: -10, fill: '#858585', fontSize: 11 }}
            />
            <YAxis
              type="number"
              dataKey="contribution_score"
              name="Contribution Score"
              domain={[0, 100]}
              stroke="#858585"
              tick={{ fontSize: 11, fill: '#858585' }}
              label={{ value: 'Contribution Score (0–100)', angle: -90, position: 'insideLeft', fill: '#858585', fontSize: 11 }}
            />
            <ReferenceLine y={50} stroke="#D4AF57" strokeDasharray="4 4" label={{ value: 'Par (50.0)', fill: '#D4AF57', fontSize: 10, position: 'right' }} />
            <Tooltip content={<CustomTooltip />} />
            <Scatter name="Innings" data={data} fill="#5A9E60" opacity={0.75} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
