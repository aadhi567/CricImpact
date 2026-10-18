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

const SEGMENTS = [
  { key: 'first_innings_contribution', name: '1st Inn', color: '#B8B8B8' },
  { key: 'chase_contribution', name: 'Chase', color: '#D4AF57' },
  { key: 'powerplay_contribution', name: 'Powerplay', color: '#E1C878' },
  { key: 'middle_over_contribution', name: 'Middle', color: '#858585' },
  { key: 'death_over_contribution', name: 'Death', color: '#A8893D' },
  { key: 'high_pressure_contribution', name: 'High Pressure', color: '#5A9E60' },
];

function CustomTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-[#161616] border border-[#2D2D2D] rounded-lg p-2.5 sm:p-3 text-xs shadow-xl text-[#F2F2F2] max-w-[calc(100vw-32px)] sm:max-w-xs pointer-events-none select-none backdrop-blur-xs">
        <div className="font-bold text-[#F2F2F2]">{data.name}</div>
        <div className="mt-1 pt-1 border-t border-[#2D2D2D]">
          {data.score !== null ? (
            <div className="text-[#D4AF57] font-bold tabular-nums font-mono">
              Contribution Score: {data.score.toFixed(1)} / 100
            </div>
          ) : (
            <div className="text-[#858585]">Not Observed (N/A)</div>
          )}
        </div>
      </div>
    );
  }
  return null;
}

export default function ContextContributionBarChart({ breakdown = {} }) {
  const { isMobile, isNarrowMobile } = useWindowWidth();

  const chartData = SEGMENTS.map((seg) => {
    const val = breakdown[seg.key];
    const isNull = val === null || val === undefined;
    return {
      name: isNarrowMobile && seg.name === 'High Pressure' ? 'High Press' : seg.name,
      score: isNull ? null : Number(val),
      color: seg.color,
    };
  });

  return (
    <div className="bg-[#161616] rounded-xl p-3 sm:p-5 border border-[#2D2D2D]">
      <div className="flex items-center justify-between mb-3 sm:mb-4">
        <div>
          <h3 className="font-heading text-[15px] sm:text-[17px] font-bold text-[#F2F2F2] tracking-tight">
            Phase and context comparison chart
          </h3>
          <p className="text-[11px] sm:text-[12px] font-normal text-[#858585] mt-0.5">
            Contribution Score across innings type, match phases, and high-pressure situations.
          </p>
        </div>
        <div className="text-[10px] sm:text-[11px] text-[#D4AF57] bg-[#101010] px-2 sm:px-2.5 py-0.5 sm:py-1 rounded border border-[#D4AF57]/40 font-mono font-semibold shrink-0">
          Par = 50.0
        </div>
      </div>

      <div className="w-full h-48 sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={
              isMobile
                ? { top: 10, right: 10, bottom: 20, left: -20 }
                : { top: 10, right: 15, bottom: 20, left: -10 }
            }
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
            <XAxis
              dataKey="name"
              stroke="#858585"
              tick={{ fontSize: isMobile ? 10 : 11, fill: '#858585' }}
            />
            <YAxis
              domain={[0, 100]}
              stroke="#858585"
              tick={{ fontSize: isMobile ? 10 : 11, fill: '#858585' }}
              label={{
                value: isMobile ? 'Score' : 'Score (0–100)',
                angle: -90,
                position: 'insideLeft',
                fill: '#858585',
                fontSize: isMobile ? 10 : 11,
                offset: isMobile ? 15 : 15,
              }}
            />
            <ReferenceLine
              y={50}
              stroke="#D4AF57"
              strokeDasharray="4 4"
              label={{
                value: isNarrowMobile ? '50' : 'Par 50',
                fill: '#D4AF57',
                fontSize: 10,
                position: 'right',
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="score" radius={[3, 3, 0, 0]} maxBarSize={isMobile ? 32 : 44}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 text-[10px] sm:text-[11px] text-[#858585] text-center">
        * Missing bars represent phases where no innings were observed (strictly NULL / N/A).
      </div>
    </div>
  );
}
