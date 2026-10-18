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
  Cell,
} from 'recharts';
import { useWindowWidth } from '../../hooks/useWindowWidth';

function CustomTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const isPos = data.raw >= 0;
    return (
      <div className="bg-[#161616] border border-[#2D2D2D] rounded-lg p-2.5 sm:p-3 text-xs shadow-xl text-[#F2F2F2] max-w-[calc(100vw-32px)] sm:max-w-xs pointer-events-none select-none backdrop-blur-xs">
        <div className="font-bold text-[#F2F2F2] truncate">{data.match_name}</div>
        <div className="text-[11px] text-[#858585]">vs {data.opponent}</div>
        <div className="mt-1.5 pt-1.5 border-t border-[#2D2D2D] space-y-0.5">
          <div className="text-[#B8B8B8]">
            Performance: <span className="font-bold text-[#F2F2F2] tabular-nums">{data.runs}</span> runs ({data.balls}b)
          </div>
          <div className={`font-mono font-bold mt-1 tabular-nums ${isPos ? 'text-[#5A9E60]' : 'text-[#C25454]'}`}>
            Raw Contribution: {isPos ? `+${data.raw.toFixed(4)}` : data.raw.toFixed(4)}
          </div>
          <div className="text-[#858585] text-[10px] tabular-nums font-mono">
            Score: {data.score} / 100
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function RawContributionChart({ matches = [] }) {
  const { isMobile } = useWindowWidth();

  const chartData = matches
    .filter((m) => !m.is_dnb && m.raw_contribution !== null)
    .map((m, idx) => ({
      index: idx + 1,
      match_name: m.date ? `${m.date}` : `M${idx + 1}`,
      opponent: m.opponent,
      runs: m.runs,
      balls: m.balls,
      raw: m.raw_contribution,
      score: m.contribution_score,
    }));

  if (chartData.length === 0) {
    return null;
  }

  const mobileInterval = chartData.length > 12 ? 2 : (chartData.length > 6 ? 1 : 0);

  return (
    <div className="bg-[#161616] rounded-xl p-3 sm:p-5 border border-[#2D2D2D]">
      <div className="flex items-center justify-between mb-3 sm:mb-4">
        <div>
          <h3 className="font-heading text-[15px] sm:text-[17px] font-bold text-[#F2F2F2] tracking-tight">
            Match-by-match raw contribution
          </h3>
          <p className="text-[11px] sm:text-[12px] font-normal text-[#858585] mt-0.5">
            Raw contextual metric values (positive vs. negative impact relative to situational baseline).
          </p>
        </div>
        <div className="text-[10px] sm:text-[11px] text-[#B8B8B8] bg-[#101010] px-2 sm:px-2.5 py-0.5 sm:py-1 rounded border border-[#2D2D2D] font-mono font-semibold shrink-0">
          Zero Line = Neutral
        </div>
      </div>

      <div className="w-full h-48 sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={
              isMobile
                ? { top: 10, right: 10, bottom: 25, left: -20 }
                : { top: 10, right: 15, bottom: 20, left: -10 }
            }
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
            <XAxis
              dataKey="match_name"
              stroke="#858585"
              tick={{ fontSize: isMobile ? 9 : 10, fill: '#858585' }}
              interval={isMobile ? mobileInterval : 0}
              angle={-25}
              textAnchor="end"
            />
            <YAxis
              stroke="#858585"
              tick={{ fontSize: isMobile ? 10 : 11, fill: '#858585' }}
              label={{
                value: isMobile ? 'Raw' : 'Raw Contribution (C_raw)',
                angle: -90,
                position: 'insideLeft',
                fill: '#858585',
                fontSize: isMobile ? 10 : 11,
                offset: isMobile ? 15 : 15,
              }}
            />
            <ReferenceLine y={0} stroke="#858585" strokeWidth={1.5} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="raw" radius={[2, 2, 2, 2]} maxBarSize={isMobile ? 20 : 28}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.raw >= 0 ? '#5A9E60' : '#C25454'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
