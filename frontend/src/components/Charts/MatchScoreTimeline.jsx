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
import { useWindowWidth } from '../../hooks/useWindowWidth';

function CustomTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    if (data.is_dnb) {
      return (
        <div className="bg-[#161616]/95 border border-[#2D2D2D] rounded-lg p-2 sm:p-3 text-[11px] sm:text-xs shadow-xl text-[#F2F2F2] max-w-[calc(100vw-32px)] sm:max-w-xs pointer-events-none select-none backdrop-blur-xs">
          <div className="font-bold text-xs sm:text-[13px] text-[#F2F2F2]">{data.match_name}</div>
          <div className="text-[#858585] text-[10.5px]">vs {data.opponent}</div>
          <div className="text-[#C25454] font-semibold mt-1">Did Not Bat (DNB) - N/A</div>
        </div>
      );
    }

    return (
      <div className="bg-[#161616]/95 border border-[#2D2D2D] rounded-lg p-2 sm:p-3 text-[11px] sm:text-xs shadow-xl text-[#F2F2F2] max-w-[calc(100vw-32px)] sm:max-w-xs pointer-events-none select-none backdrop-blur-xs">
        <div className="font-bold text-xs sm:text-[13px] text-[#F2F2F2] truncate">{data.match_name}</div>
        <div className="text-[#858585] text-[10.5px]">vs {data.opponent}</div>
        <div className="mt-1 pt-1 border-t border-[#2D2D2D] space-y-0.5">
          <div className="text-[#B8B8B8]">
            Score: <span className="font-bold text-[#F2F2F2] tabular-nums">{data.runs}</span> off {data.balls}b (SR {data.strike_rate})
          </div>
          <div className="text-[#D4AF57] font-bold mt-0.5 tabular-nums font-mono">
            Contribution Score: {data.contribution_score}
          </div>
          <div className="text-[#858585] tabular-nums font-mono text-[10px]">
            Raw: {data.raw_contribution > 0 ? `+${data.raw_contribution}` : data.raw_contribution}
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function MatchScoreTimeline({ matches = [] }) {
  const width = useWindowWidth();
  const isMobile = width < 640;
  const isNarrowMobile = width < 400;

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
      <div className="bg-[#161616] rounded-xl p-4 sm:p-5 border border-[#2D2D2D] text-center text-[#858585] text-xs">
        No batting innings with contribution scores to chart.
      </div>
    );
  }

  // Intelligently skip tick labels on mobile to prevent crowding
  const tickInterval = isMobile
    ? (chartData.length > 12 ? 2 : (chartData.length > 7 ? 1 : 0))
    : 0;

  return (
    <div className="bg-[#161616] rounded-xl p-2.5 sm:p-4 border border-[#2D2D2D]">
      <div className="flex items-center justify-between mb-2.5 sm:mb-3">
        <div>
          <h3 className="font-heading text-[14px] sm:text-[16px] font-bold text-[#F2F2F2] tracking-tight">
            Match-by-match contribution score
          </h3>
          <p className="text-[10.5px] sm:text-xs font-normal text-[#858585] mt-0.5">
            Chronological progression of innings performance relative to Par (50.0).
          </p>
        </div>
        <div className="text-[10px] sm:text-[11px] text-[#D4AF57] bg-[#101010] px-2 py-0.5 rounded border border-[#D4AF57]/40 font-mono font-semibold shrink-0">
          Par = 50.0
        </div>
      </div>

      <div className="w-full h-44 sm:h-56">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={
              isMobile
                ? { top: 8, right: 8, bottom: 15, left: -16 }
                : { top: 10, right: 15, bottom: 20, left: -10 }
            }
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
            <XAxis
              dataKey="match_name"
              stroke="#858585"
              tick={{ fontSize: isNarrowMobile ? 8.5 : (isMobile ? 9.5 : 10), fill: '#858585' }}
              interval={tickInterval}
              angle={-25}
              textAnchor="end"
              height={isMobile ? 32 : 38}
            />
            <YAxis
              domain={[0, 100]}
              stroke="#858585"
              tick={{ fontSize: isMobile ? 10 : 11, fill: '#858585' }}
              label={
                !isMobile
                  ? { value: 'Score (0–100)', angle: -90, position: 'insideLeft', fill: '#858585', fontSize: 11, offset: 15 }
                  : undefined
              }
              width={isMobile ? 32 : 40}
            />
            <ReferenceLine y={50} stroke="#D4AF57" strokeDasharray="4 4" label={!isMobile ? { value: 'Par 50', fill: '#D4AF57', fontSize: 10, position: 'right' } : undefined} />
            <Tooltip
              content={<CustomTooltip />}
              wrapperStyle={{ outline: 'none', zIndex: 50, pointerEvents: 'none' }}
            />
            <Bar dataKey="contribution_score" fill="#2D2D2D" radius={[3, 3, 0, 0]} maxBarSize={isMobile ? 24 : 32} />
            <Line type="monotone" dataKey="contribution_score" stroke="#D4AF57" strokeWidth={2} dot={{ r: isMobile ? 2.5 : 3.5, fill: '#D4AF57' }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
