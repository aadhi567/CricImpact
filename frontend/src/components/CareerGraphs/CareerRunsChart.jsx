import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { useWindowWidth } from '../../hooks/useWindowWidth';

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-[#121212]/95 border border-[#2D2D2D] rounded-lg p-2.5 sm:p-3.5 text-[11px] sm:text-xs shadow-2xl text-[#F2F2F2] max-w-[calc(100vw-32px)] sm:max-w-xs min-w-[170px] sm:min-w-[210px] pointer-events-none select-none backdrop-blur-xs">
        <div className="flex items-center justify-between border-b border-[#222222] pb-1.5 mb-1.5 gap-2">
          <span className="font-bold text-xs sm:text-[14px] text-[#F2F2F2] truncate">{label}</span>
          <span className="text-[10px] sm:text-[11px] px-1.5 py-0.5 rounded bg-[#1A1A1A] border border-[#2D2D2D] text-[#D4AF57] font-semibold shrink-0">
            {data.competition}
          </span>
        </div>

        <div className="space-y-1 font-sans">
          <div className="flex items-center justify-between">
            <span className="text-[#858585]">Total Runs:</span>
            <span className="font-bold text-[#F2F2F2] text-xs sm:text-[14px] tabular-nums font-sans">
              {data.runs}
            </span>
          </div>

          {data.ipl_runs !== null && data.t20i_runs !== null && (
            <div className="pl-1.5 border-l border-[#2D2D2D] space-y-0.5 text-[10px] sm:text-[11.5px]">
              <div className="flex items-center justify-between text-[#D4AF57]">
                <span>• IPL Runs:</span>
                <span className="tabular-nums font-semibold">{data.ipl_runs}</span>
              </div>
              <div className="flex items-center justify-between text-[#5A9E60]">
                <span>• Intl Runs:</span>
                <span className="tabular-nums font-semibold">{data.t20i_runs}</span>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between text-[#B8B8B8] pt-1 border-t border-[#222222]">
            <span>Batting Innings:</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">
              {data.batting_innings} <span className="text-[#858585] font-normal">({data.matches} m)</span>
            </span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8]">
            <span>Balls Faced:</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">{data.balls_faced}</span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8]">
            <span>Season SR:</span>
            <span className="tabular-nums font-bold text-[#D4AF57]">{data.strike_rate ?? '—'}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function CareerRunsChart({ timeline = [], isCombined = false }) {
  const width = useWindowWidth();
  const isMobile = width < 640;
  const isNarrowMobile = width < 400;

  if (!timeline || timeline.length === 0) {
    return (
      <div className="h-[220px] sm:h-[280px] flex items-center justify-center text-[#858585] text-xs sm:text-sm">
        No seasonal runs data available.
      </div>
    );
  }

  // Intelligently skip tick labels on narrow screens so they never overlap, while keeping all bars intact
  const tickInterval = isMobile
    ? (timeline.length > 12 ? 2 : (timeline.length > 6 ? 1 : 0))
    : 0;

  return (
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
            allowDecimals={false}
            width={isMobile ? 32 : 40}
          />
          <Tooltip
            content={<CustomTooltip />}
            wrapperStyle={{ outline: 'none', zIndex: 50, pointerEvents: 'none' }}
          />
          {isCombined ? (
            <>
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{
                  paddingBottom: isMobile ? '4px' : '10px',
                  fontSize: isMobile ? '11px' : '12px',
                }}
              />
              <Bar
                dataKey="ipl_runs"
                name="IPL Runs"
                stackId="a"
                fill="#D4AF57"
                radius={[0, 0, 0, 0]}
              />
              <Bar
                dataKey="t20i_runs"
                name="International Runs"
                stackId="a"
                fill="#5A9E60"
                radius={[3, 3, 0, 0]}
              />
            </>
          ) : (
            <Bar
              dataKey="runs"
              name="Total Runs"
              fill="#D4AF57"
              radius={[3, 3, 0, 0]}
            />
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
