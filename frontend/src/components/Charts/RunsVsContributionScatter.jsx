import React from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { useWindowWidth } from '../../hooks/useWindowWidth';

function CustomTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-[#161616] border border-[#2D2D2D] rounded-lg p-2.5 sm:p-3 text-xs shadow-xl text-[#F2F2F2] max-w-[calc(100vw-32px)] sm:max-w-xs pointer-events-none select-none backdrop-blur-xs">
        <div className="font-bold text-[#F2F2F2] truncate">{data.player}</div>
        <div className="text-[11px] text-[#858585]">vs {data.opponent} ({data.season})</div>
        <div className="mt-1.5 pt-1.5 border-t border-[#2D2D2D] space-y-0.5">
          <div className="text-[#B8B8B8]">
            Runs: <span className="font-bold text-[#F2F2F2] tabular-nums">{data.runs}</span> ({data.balls}b)
          </div>
          <div className="text-[#858585]">
            SR: <span className="font-mono text-[#F2F2F2] tabular-nums">{data.strike_rate}</span>
          </div>
          <div className="text-[#D4AF57] font-bold mt-1 tabular-nums font-mono">
            Contribution Score: {data.contribution_score}
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function RunsVsContributionScatter({ data = [] }) {
  const { isMobile, isNarrowMobile } = useWindowWidth();

  return (
    <div className="bg-[#161616] rounded-xl p-3 sm:p-5 border border-[#2D2D2D]">
      <div className="flex items-center justify-between mb-3 sm:mb-4">
        <div>
          <h3 className="font-heading text-[15px] sm:text-[17px] font-bold text-[#F2F2F2] tracking-tight">
            Runs vs. contribution score
          </h3>
          <p className="text-[11px] sm:text-[12px] font-normal text-[#858585] mt-0.5">
            Illustrates that raw volume (runs scored) is distinct from contextual contribution.
          </p>
        </div>
        <div className="text-[10px] sm:text-[11px] text-[#D4AF57] bg-[#101010] px-2 sm:px-2.5 py-0.5 sm:py-1 rounded border border-[#D4AF57]/40 font-mono font-semibold shrink-0">
          Par = 50.0
        </div>
      </div>

      <div className="w-full h-56 sm:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart
            margin={
              isMobile
                ? { top: 10, right: 15, bottom: 15, left: -15 }
                : { top: 10, right: 20, bottom: 20, left: 0 }
            }
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#222222" />
            <XAxis
              type="number"
              dataKey="runs"
              name="Runs"
              stroke="#858585"
              tick={{ fontSize: isMobile ? 10 : 11, fill: '#858585' }}
              label={{
                value: isNarrowMobile ? 'Runs' : 'Actual Runs Scored',
                position: 'insideBottom',
                offset: -10,
                fill: '#858585',
                fontSize: isMobile ? 10 : 11,
              }}
            />
            <YAxis
              type="number"
              dataKey="contribution_score"
              name="Contribution Score"
              domain={[0, 100]}
              stroke="#858585"
              tick={{ fontSize: isMobile ? 10 : 11, fill: '#858585' }}
              label={{
                value: isMobile ? 'Score' : 'Contribution Score (0–100)',
                angle: -90,
                position: 'insideLeft',
                fill: '#858585',
                fontSize: isMobile ? 10 : 11,
                offset: isMobile ? 15 : 10,
              }}
            />
            <ReferenceLine
              y={50}
              stroke="#D4AF57"
              strokeDasharray="4 4"
              label={{
                value: isNarrowMobile ? '50' : 'Par (50.0)',
                fill: '#D4AF57',
                fontSize: 10,
                position: 'right',
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Scatter name="Innings" data={data} fill="#D4AF57" opacity={0.75} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
