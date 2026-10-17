import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const sr = data.strike_rate;

    return (
      <div className="bg-[#121212] border border-[#2D2D2D] rounded-xl p-3.5 text-xs shadow-2xl text-[#F2F2F2] min-w-[210px]">
        <div className="flex items-center justify-between border-b border-[#222222] pb-2 mb-2">
          <span className="font-bold text-[14px] text-[#F2F2F2]">{label}</span>
          <span className="text-[11px] px-2 py-0.5 rounded bg-[#1A1A1A] border border-[#2D2D2D] text-[#D4AF57] font-semibold">
            {data.competition}
          </span>
        </div>

        <div className="space-y-1.5 font-sans">
          <div className="flex items-center justify-between">
            <span className="text-[#858585]">Strike Rate:</span>
            <span className="font-bold text-[#F2F2F2] text-[15px] tabular-nums text-[#D4AF57]">
              {sr !== null ? `${sr}` : '—'}
            </span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8] pt-1 border-t border-[#222222]">
            <span>Runs Scored:</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">{data.runs}</span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8]">
            <span>Balls Faced:</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">{data.balls_faced}</span>
          </div>

          <div className="text-[11px] text-[#858585] pt-1 border-t border-[#222222]">
            * Calculated as (Total Runs &divide; Balls Faced) &times; 100
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function CareerStrikeRateChart({ timeline = [] }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="h-[280px] flex items-center justify-center text-[#858585] text-sm">
        No strike rate data available.
      </div>
    );
  }

  // Calculate overall career strike rate benchmark from underlying totals
  const totalRuns = timeline.reduce((acc, t) => acc + (t.runs || 0), 0);
  const totalBalls = timeline.reduce((acc, t) => acc + (t.balls_faced || 0), 0);
  const careerSR = totalBalls > 0 ? Number((totalRuns / totalBalls * 100).toFixed(1)) : 130;

  return (
    <div className="w-full h-[320px] sm:h-[350px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
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
            domain={['dataMin - 15', 'dataMax + 15']}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={careerSR}
            stroke="#D4AF57"
            strokeDasharray="4 4"
            label={{
              value: `Career SR: ${careerSR}`,
              fill: '#D4AF57',
              fontSize: 11,
              position: 'insideTopRight',
            }}
          />
          <ReferenceLine
            y={130}
            stroke="#444444"
            strokeDasharray="2 2"
            label={{
              value: '130 SR Baseline',
              fill: '#858585',
              fontSize: 10,
              position: 'insideBottomRight',
            }}
          />
          <Line
            type="monotone"
            dataKey="strike_rate"
            name="Strike Rate"
            stroke="#D4AF57"
            strokeWidth={2.5}
            dot={{ r: 4, fill: '#121212', stroke: '#D4AF57', strokeWidth: 2 }}
            activeDot={{ r: 6, fill: '#D4AF57', stroke: '#F2F2F2', strokeWidth: 2 }}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
