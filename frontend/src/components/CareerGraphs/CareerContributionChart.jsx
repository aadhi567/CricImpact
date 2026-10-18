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
import { useWindowWidth } from '../../hooks/useWindowWidth';

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const score = data.average_contribution;
    const isAbovePar = score !== null && score >= 50.0;
    const diff = score !== null ? (score - 50.0).toFixed(1) : null;

    return (
      <div className="bg-[#121212]/95 border border-[#2D2D2D] rounded-lg p-2.5 sm:p-3.5 text-[11px] sm:text-xs shadow-2xl text-[#F2F2F2] max-w-[calc(100vw-32px)] sm:max-w-xs min-w-[170px] sm:min-w-[220px] pointer-events-none select-none backdrop-blur-xs">
        <div className="flex items-center justify-between border-b border-[#222222] pb-1.5 mb-1.5 gap-2">
          <span className="font-bold text-xs sm:text-[14px] text-[#F2F2F2] truncate">{label}</span>
          <span className="text-[10px] sm:text-[11px] px-1.5 py-0.5 rounded bg-[#1A1A1A] border border-[#2D2D2D] text-[#D4AF57] font-semibold shrink-0">
            {data.competition}
          </span>
        </div>

        <div className="space-y-1 font-sans">
          <div className="flex items-center justify-between">
            <span className="text-[#858585]">Avg Contribution:</span>
            <span
              className={`font-bold text-xs sm:text-[16px] tabular-nums ${
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
            <div className="flex items-center justify-between text-[10px] sm:text-[11px]">
              <span className="text-[#858585]">Rel to Par (50.0):</span>
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
            <div className="pl-1.5 border-l border-[#2D2D2D] space-y-0.5 text-[10px] sm:text-[11px] pt-0.5">
              <div className="flex items-center justify-between text-[#D4AF57]">
                <span>• IPL:</span>
                <span className="tabular-nums font-semibold">{data.ipl_avg_contribution.toFixed(1)}</span>
              </div>
              <div className="flex items-center justify-between text-[#5A9E60]">
                <span>• Intl:</span>
                <span className="tabular-nums font-semibold">{data.t20i_avg_contribution.toFixed(1)}</span>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between text-[#B8B8B8] pt-1 border-t border-[#222222]">
            <span>Batting Innings:</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">
              {data.batting_innings} <span className="text-[#858585]">({data.matches} m)</span>
            </span>
          </div>

          <div className="text-[10px] text-[#858585] pt-1 border-t border-[#222222]">
            * Strategy 4 Hybrid • Par = 50.0 • DNB excluded
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function CareerContributionChart({ timeline = [] }) {
  const width = useWindowWidth();
  const isMobile = width < 640;
  const isNarrowMobile = width < 400;

  if (!timeline || timeline.length === 0) {
    return (
      <div className="h-[220px] sm:h-[280px] flex items-center justify-center text-[#858585] text-xs sm:text-sm">
        No contribution score data available.
      </div>
    );
  }

  // Intelligently skip tick labels on narrow screens so they never overlap
  const tickInterval = isMobile
    ? (timeline.length > 12 ? 2 : (timeline.length > 6 ? 1 : 0))
    : 0;

  return (
    <div className="w-full space-y-1.5">
      {/* Mobile Benchmark Indicator */}
      {isMobile && (
        <div className="flex items-center justify-between px-1 text-[11px] text-[#858585]">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-0.5 bg-[#D4AF57] inline-block" />
            <span>Par = 50.0 (Neutral)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-0.5 bg-[#5A9E60] inline-block" />
            <span>Elite Tier (65+)</span>
          </span>
        </div>
      )}

      <div className="w-full h-[220px] sm:h-[350px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={timeline}
            margin={
              isMobile
                ? { top: 12, right: 8, left: -16, bottom: 20 }
                : { top: 15, right: 15, left: -10, bottom: 25 }
            }
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
              tick={{
                fill: '#858585',
                fontSize: isNarrowMobile ? 9.5 : (isMobile ? 10.5 : 12),
                fontFamily: 'Inter, sans-serif',
              }}
              tickLine={{ stroke: '#2D2D2D' }}
              interval={tickInterval}
              angle={timeline.length > (isMobile ? 6 : 10) ? -35 : 0}
              textAnchor={timeline.length > (isMobile ? 6 : 10) ? 'end' : 'middle'}
              height={isMobile ? 36 : 45}
            />
            <YAxis
              stroke="#858585"
              tick={{
                fill: '#858585',
                fontSize: isMobile ? 10 : 12,
                fontFamily: 'Inter, sans-serif',
              }}
              tickLine={{ stroke: '#2D2D2D' }}
              domain={[30, 85]}
              width={isMobile ? 32 : 40}
            />
            <Tooltip
              content={<CustomTooltip />}
              wrapperStyle={{ outline: 'none', zIndex: 50, pointerEvents: 'none' }}
            />
            <ReferenceLine
              y={50.0}
              stroke="#A8893D"
              strokeDasharray="4 4"
              label={
                !isMobile
                  ? {
                      value: 'Par = 50.0',
                      fill: '#D4AF57',
                      fontSize: 11,
                      position: 'insideTopLeft',
                    }
                  : undefined
              }
            />
            <ReferenceLine
              y={65.0}
              stroke="#2A4D30"
              strokeDasharray="2 2"
              label={
                !isMobile
                  ? {
                      value: 'Elite Tier (65+)',
                      fill: '#5A9E60',
                      fontSize: 10,
                      position: 'insideTopRight',
                    }
                  : undefined
              }
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
              dot={{ r: isMobile ? 3 : 4, fill: '#121212', stroke: '#D4AF57', strokeWidth: 2 }}
              activeDot={{ r: isMobile ? 5 : 6, fill: '#D4AF57', stroke: '#F2F2F2', strokeWidth: 2 }}
              connectNulls={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
