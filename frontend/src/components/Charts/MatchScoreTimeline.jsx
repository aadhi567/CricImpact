import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';

function CustomTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    if (data.is_dnb) {
      return (
        <div className="bg-[#161616] border border-[#2D2D2D] rounded-lg p-3 text-xs shadow-xl text-[#F2F2F2]">
          <div className="font-bold text-[#F2F2F2]">{data.match_name}</div>
          <div className="text-[#858585]">vs {data.opponent}</div>
          <div className="text-[#C25454] font-semibold mt-1">Did Not Bat (DNB) - N/A</div>
        </div>
      );
    }

    return (
      <div className="bg-[#161616] border border-[#2D2D2D] rounded-lg p-3 text-xs shadow-xl text-[#F2F2F2]">
        <div className="font-bold text-[#F2F2F2]">{data.match_name}</div>
        <div className="text-[#858585]">vs {data.opponent}</div>
        <div className="mt-1 pt-1 border-t border-[#2D2D2D] space-y-0.5">
          <div className="text-[#B8B8B8]">
            Score: <span className="font-bold text-[#F2F2F2] tabular-nums">{data.runs}</span> off {data.balls}b (SR {data.strike_rate})
          </div>
          <div className="text-[#D4AF57] font-bold mt-1 tabular-nums font-mono">
            Contribution Score: {data.contribution_score}
          </div>
          <div className="text-[#858585] tabular-nums font-mono">
            Raw: {data.raw_contribution > 0 ? `+${data.raw_contribution}` : data.raw_contribution}
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function MatchScoreTimeline({ matches = [] }) {
  const chartData = matches
    .filter((m) => !m.is_dnb && m.contribution_score !== null)
    .map((m, idx) => ({
      index: idx + 1,
      match_name: m.date ? `${m.date}` : `M${idx + 1}`,
      opponent: m.opponent,
      runs: m.runs,
      balls: m.balls,
      strike_rate: m.strike_rate,
      contribution_score: m.contribution_score,
      raw_contribution: m.raw_contribution,
    }));

  if (chartData.length === 0) {
    return (
      <div className="bg-[#161616] rounded-xl p-5 border border-[#2D2D2D] text-center text-[#858585] text-xs">
        No batting innings with contribution scores to chart.
      </div>
    );
  }

  return (
    <div className="bg-[#161616] rounded-xl p-5 border border-[#2D2D2D]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2] tracking-tight">
            Match-by-match contribution score
          </h3>
          <p className="text-[12px] font-normal text-[#858585] mt-0.5">
            Chronological progression of innings performance relative to Par (50.0).
          </p>
        </div>
        <div className="text-[11px] text-[#D4AF57] bg-[#101010] px-2.5 py-1 rounded border border-[#D4AF57]/40 font-mono font-semibold">
          Par = 50.0
        </div>
      </div>

      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 15, bottom: 20, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
            <XAxis
              dataKey="match_name"
              stroke="#858585"
              tick={{ fontSize: 10, fill: '#858585' }}
              interval={0}
              angle={-25}
              textAnchor="end"
            />
            <YAxis
              domain={[0, 100]}
              stroke="#858585"
              tick={{ fontSize: 11, fill: '#858585' }}
              label={{ value: 'Score (0–100)', angle: -90, position: 'insideLeft', fill: '#858585', fontSize: 11, offset: 15 }}
            />
            <ReferenceLine y={50} stroke="#D4AF57" strokeDasharray="4 4" label={{ value: 'Par 50', fill: '#D4AF57', fontSize: 10, position: 'right' }} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="contribution_score" fill="#2D2D2D" radius={[3, 3, 0, 0]} maxBarSize={32} />
            <Line type="monotone" dataKey="contribution_score" stroke="#D4AF57" strokeWidth={2} dot={{ r: 3.5, fill: '#D4AF57' }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
