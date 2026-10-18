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
import { useWindowWidth } from '../../hooks/useWindowWidth';

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const rate = data.positive_contribution_rate;

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
            <span className="text-[#858585]">Positive Rate:</span>
            <span className="font-bold text-xs sm:text-[16px] tabular-nums text-[#5A9E60]">
              {rate !== null ? `${rate}%` : '—'}
            </span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8] pt-1 border-t border-[#222222]">
            <span>Above Par (&gt; 50):</span>
            <span className="tabular-nums font-semibold text-[#5A9E60]">
              {data.positive_appearances} inn
            </span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8]">
            <span>Eligible Innings:</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">
              {data.eligible_appearances} inn
            </span>
          </div>

          <div className="flex items-center justify-between text-[#858585]">
            <span>DNB (Excluded):</span>
            <span className="tabular-nums font-semibold text-[#858585]">
              {data.dnb_matches} matches
            </span>
          </div>

          <div className="text-[10px] text-[#858585] pt-1 border-t border-[#222222]">
            * Formula: (Positive Innings &divide; Eligible Innings) &times; 100.
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function CareerPositiveRateChart({ timeline = [] }) {
  const width = useWindowWidth();
  const isMobile = width < 640;
  const isNarrowMobile = width < 400;

  if (!timeline || timeline.length === 0) {
    return (
      <div className="h-[220px] sm:h-[280px] flex items-center justify-center text-[#858585] text-xs sm:text-sm">
        No positive contribution rate data available.
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
            <span className="w-2.5 h-0.5 bg-[#555555] inline-block" />
            <span>50% Neutral Benchmark</span>
          </span>
          <span className="text-[10px] text-[#5A9E60] font-semibold">Par Line</span>
        </div>
      )}

      <div className="w-full h-[220px] sm:h-[350px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={timeline}
            margin={
              isMobile
                ? { top: 12, right: 8, left: -16, bottom: 20 }
                : { top: 15, right: 15, left: -10, bottom: 25 }
            }
          >
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
              domain={[0, 100]}
              unit="%"
              width={isMobile ? 32 : 40}
            />
            <Tooltip
              content={<CustomTooltip />}
              wrapperStyle={{ outline: 'none', zIndex: 50, pointerEvents: 'none' }}
            />
            <ReferenceLine
              y={50.0}
              stroke="#444444"
              strokeDasharray="4 4"
              label={
                !isMobile
                  ? {
                      value: '50% Neutral Benchmark',
                      fill: '#858585',
                      fontSize: 10,
                      position: 'insideTopRight',
                    }
                  : undefined
              }
            />
            <Bar
              dataKey="positive_contribution_rate"
              name="Positive Contribution Rate (%)"
              fill="#5A9E60"
              radius={[3, 3, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
