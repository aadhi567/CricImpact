import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const score = data.average_contribution;
    const isAbovePar = score !== null && score >= 50.0;
    const diff = score !== null ? (score - 50.0).toFixed(1) : null;

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
            <span className="text-[#858585]">Avg Contribution:</span>
            <span
              className={`font-bold text-[16px] tabular-nums ${
                score === null
                  ? 'text-[#858585]'
                  : isAbovePar
                  ? 'text-[#5A9E60]'
                  : 'text-[#C25454]'
              }`}
            >
              {score !== null ? score.toFixed(1) : '—'}
            </span>
          </div>

          {score !== null && (
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[#858585]">Relative to Par (50.0):</span>
              <span
                className={`tabular-nums font-semibold ${
                  isAbovePar ? 'text-[#5A9E60]' : 'text-[#C25454]'
                }`}
              >
                {diff >= 0 ? `+${diff}` : diff} pts
              </span>
            </div>
          )}

          {data.ipl_avg_contribution !== null && data.t20i_avg_contribution !== null && (
            <div className="pl-2 border-l border-[#2D2D2D] space-y-1 text-[11px] pt-1">
              <div className="flex items-center justify-between text-[#D4AF57]">
                <span>• IPL Contribution:</span>
                <span className="tabular-nums font-semibold">{data.ipl_avg_contribution.toFixed(1)}</span>
              </div>
              <div className="flex items-center justify-between text-[#5A9E60]">
                <span>• International Contribution:</span>
                <span className="tabular-nums font-semibold">{data.t20i_avg_contribution.toFixed(1)}</span>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between text-[#B8B8B8] pt-1 border-t border-[#222222]">
            <span>Batting Innings:</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">
              {data.batting_innings} <span className="text-[#858585]">({data.matches} appearances)</span>
            </span>
          </div>

          <div className="text-[10.5px] text-[#858585] pt-1 border-t border-[#222222]">
            * Strategy 4 Hybrid scoring • Par = 50.0 • DNB excluded
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function CareerContributionChart({ timeline = [] }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="h-[280px] flex items-center justify-center text-[#858585] text-sm">
        No contribution score data available.
      </div>
    );
  }

  return (
    <div className="w-full h-[320px] sm:h-[350px]">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={timeline}
          margin={{ top: 15, right: 15, left: -10, bottom: 25 }}
        >
          <defs>
            <linearGradient id="contribGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#D4AF57" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#D4AF57" stopOpacity={0.0} />
            </linearGradient>
          </defs>
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
            domain={[30, 85]}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={50.0}
            stroke="#A8893D"
            strokeDasharray="4 4"
            label={{
              value: 'Par = 50.0',
              fill: '#D4AF57',
              fontSize: 11,
              position: 'insideTopLeft',
            }}
          />
          <ReferenceLine
            y={65.0}
            stroke="#2A4D30"
            strokeDasharray="2 2"
            label={{
              value: 'Elite Tier (65+)',
              fill: '#5A9E60',
              fontSize: 10,
              position: 'insideTopRight',
            }}
          />
          <Area
            type="monotone"
            dataKey="average_contribution"
            fill="url(#contribGradient)"
            stroke="none"
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="average_contribution"
            name="Average Contribution"
            stroke="#D4AF57"
            strokeWidth={2.5}
            dot={{ r: 4, fill: '#121212', stroke: '#D4AF57', strokeWidth: 2 }}
            activeDot={{ r: 6, fill: '#D4AF57', stroke: '#F2F2F2', strokeWidth: 2 }}
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
