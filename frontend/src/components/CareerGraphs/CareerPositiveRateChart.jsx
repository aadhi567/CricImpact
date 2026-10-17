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
} from 'recharts';

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const rate = data.positive_contribution_rate;

    return (
      <div className="bg-[#121212] border border-[#2D2D2D] rounded-xl p-3.5 text-xs shadow-2xl text-[#F2F2F2] min-w-[220px]">
        <div className="flex items-center justify-between border-b border-[#222222] pb-2 mb-2">
          <span className="font-bold text-[14px] text-[#F2F2F2]">{label}</span>
          <span className="text-[11px] px-2 py-0.5 rounded bg-[#1A1A1A] border border-[#2D2D2D] text-[#D4AF57] font-semibold">
            {data.competition}
          </span>
        </div>

        <div className="space-y-1.5 font-sans">
          <div className="flex items-center justify-between">
            <span className="text-[#858585]">Positive Rate:</span>
            <span className="font-bold text-[16px] tabular-nums text-[#5A9E60]">
              {rate !== null ? `${rate}%` : '—'}
            </span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8] pt-1 border-t border-[#222222]">
            <span>Numerator (Above Par &gt; 50):</span>
            <span className="tabular-nums font-semibold text-[#5A9E60]">
              {data.positive_appearances} innings
            </span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8]">
            <span>Denominator (Eligible Innings):</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">
              {data.eligible_appearances} innings
            </span>
          </div>

          <div className="flex items-center justify-between text-[#858585]">
            <span>DNB (Excluded):</span>
            <span className="tabular-nums font-semibold text-[#858585]">
              {data.dnb_matches} matches
            </span>
          </div>

          <div className="text-[10.5px] text-[#858585] pt-1 border-t border-[#222222]">
            * Formula: (Positive Innings &divide; Eligible Innings) &times; 100. DNB never enters denominator.
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function CareerPositiveRateChart({ timeline = [] }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="h-[280px] flex items-center justify-center text-[#858585] text-sm">
        No positive contribution rate data available.
      </div>
    );
  }

  return (
    <div className="w-full h-[320px] sm:h-[350px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={timeline}
          margin={{ top: 15, right: 15, left: -10, bottom: 25 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
          <XAxis
            dataKey="season"
            stroke="#858585"
            tick={{ fill: '#858585', fontSize: 12, fontFamily: 'Inter, sans-serif' }}
            tickLine={{ stroke: '#2D2D2D' }}
            interval={0}
            angle={timeline.length > 10 ? -45 : 0}
            textAnchor={timeline.length > 10 ? 'end' : 'middle'}
            height={45}
          />
          <YAxis
            stroke="#858585"
            tick={{ fill: '#858585', fontSize: 12, fontFamily: 'Inter, sans-serif' }}
            tickLine={{ stroke: '#2D2D2D' }}
            domain={[0, 100]}
            unit="%"
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={50.0}
            stroke="#444444"
            strokeDasharray="4 4"
            label={{
              value: '50% Neutral Benchmark',
              fill: '#858585',
              fontSize: 10,
              position: 'insideTopRight',
            }}
          />
          <Bar
            dataKey="positive_contribution_rate"
            name="Positive Contribution Rate (%)"
            fill="#5A9E60"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
