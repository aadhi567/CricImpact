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
import { useWindowWidth } from '../../hooks/useWindowWidth';

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const dotPct = data.dot_ball_percentage;

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
            <span className="text-[#858585]">Dot-Ball %:</span>
            <span className="font-bold text-xs sm:text-[16px] tabular-nums text-[#D4AF57]">
              {dotPct !== null ? `${dotPct}%` : '—'}
            </span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8] pt-1 border-t border-[#222222]">
            <span>Dot Balls (0 runs):</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">
              {data.dot_balls} b
            </span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8]">
            <span>Eligible Balls:</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">
              {data.eligible_balls} b
            </span>
          </div>

          <div className="text-[10px] text-[#858585] pt-1 border-t border-[#222222]">
            * Delivery-level records. Lower dot % reflects superior strike rotation.
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function CareerDotBallChart({ timeline = [] }) {
  const width = useWindowWidth();
  const isMobile = width < 640;
  const isNarrowMobile = width < 400;

  if (!timeline || timeline.length === 0) {
    return (
      <div className="h-[220px] sm:h-[280px] flex items-center justify-center text-[#858585] text-xs sm:text-sm">
        No dot-ball percentage data available.
      </div>
    );
  }

  // Calculate overall career dot-ball percentage benchmark from totals
  const totalDots = timeline.reduce((acc, t) => acc + (t.dot_balls || 0), 0);
  const totalBalls = timeline.reduce((acc, t) => acc + (t.eligible_balls || 0), 0);
  const careerDotPct = totalBalls > 0 ? Number((totalDots / totalBalls * 100).toFixed(1)) : 33.0;

  // Intelligently skip tick labels on narrow screens so they never overlap
  const tickInterval = isMobile
    ? (timeline.length > 12 ? 2 : (timeline.length > 6 ? 1 : 0))
    : 0;

  const isBenchmarkNear = Math.abs(careerDotPct - 35) < 6;
  const careerDotLabelPos = isBenchmarkNear ? 'insideTopLeft' : 'insideTopRight';

  return (
    <div className="w-full space-y-1.5">
      {/* Mobile Benchmark Indicator */}
      {isMobile && (
        <div className="flex items-center justify-between px-1 text-[11px] text-[#858585]">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-0.5 bg-[#D4AF57] inline-block" />
            <span>Career Avg: <strong className="text-[#D4AF57] font-semibold">{careerDotPct}%</strong></span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-0.5 bg-[#666666] inline-block" />
            <span>35% T20 Par</span>
          </span>
        </div>
      )}

      <div className="w-full h-[220px] sm:h-[350px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
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
              domain={[10, 60]}
              unit="%"
              width={isMobile ? 32 : 40}
            />
            <Tooltip
              content={<CustomTooltip />}
              wrapperStyle={{ outline: 'none', zIndex: 50, pointerEvents: 'none' }}
            />
            <ReferenceLine
              y={careerDotPct}
              stroke="#D4AF57"
              strokeDasharray="4 4"
              label={
                !isMobile
                  ? {
                      value: `Career Avg: ${careerDotPct}%`,
                      fill: '#D4AF57',
                      fontSize: 11,
                      position: careerDotLabelPos,
                    }
                  : undefined
              }
            />
            <ReferenceLine
              y={35.0}
              stroke="#444444"
              strokeDasharray="2 2"
              label={
                !isMobile
                  ? {
                      value: '35% T20 Par',
                      fill: '#858585',
                      fontSize: 10,
                      position: 'insideBottomRight',
                    }
                  : undefined
              }
            />
            <Line
              type="monotone"
              dataKey="dot_ball_percentage"
              name="Dot-Ball Percentage"
              stroke="#E1C878"
              strokeWidth={2.5}
              dot={{ r: isMobile ? 3 : 4, fill: '#121212', stroke: '#D4AF57', strokeWidth: 2 }}
              activeDot={{ r: isMobile ? 5 : 6, fill: '#D4AF57', stroke: '#F2F2F2', strokeWidth: 2 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
