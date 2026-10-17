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
    const dotPct = data.dot_ball_percentage;

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
            <span className="text-[#858585]">Dot-Ball %:</span>
            <span className="font-bold text-[16px] tabular-nums text-[#D4AF57]">
              {dotPct !== null ? `${dotPct}%` : '—'}
            </span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8] pt-1 border-t border-[#222222]">
            <span>Dot Balls (0 runs):</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">
              {data.dot_balls} balls
            </span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8]">
            <span>Eligible Balls Faced:</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">
              {data.eligible_balls} balls
            </span>
          </div>

          <div className="text-[10.5px] text-[#858585] pt-1 border-t border-[#222222]">
            * Calculated from delivery-level records. Lower dot % indicates superior strike rotation.
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function CareerDotBallChart({ timeline = [] }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="h-[280px] flex items-center justify-center text-[#858585] text-sm">
        No dot-ball percentage data available.
      </div>
    );
  }

  // Calculate overall career dot-ball percentage benchmark from totals
  const totalDots = timeline.reduce((acc, t) => acc + (t.dot_balls || 0), 0);
  const totalBalls = timeline.reduce((acc, t) => acc + (t.eligible_balls || 0), 0);
  const careerDotPct = totalBalls > 0 ? Number((totalDots / totalBalls * 100).toFixed(1)) : 33.0;

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
            domain={[10, 60]}
            unit="%"
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={careerDotPct}
            stroke="#D4AF57"
            strokeDasharray="4 4"
            label={{
              value: `Career Avg: ${careerDotPct}%`,
              fill: '#D4AF57',
              fontSize: 11,
              position: 'insideTopRight',
            }}
          />
          <ReferenceLine
            y={35.0}
            stroke="#444444"
            strokeDasharray="2 2"
            label={{
              value: '35% T20 Par',
              fill: '#858585',
              fontSize: 10,
              position: 'insideBottomRight',
            }}
          />
          <Line
            type="monotone"
            dataKey="dot_ball_percentage"
            name="Dot-Ball Percentage"
            stroke="#E1C878"
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
