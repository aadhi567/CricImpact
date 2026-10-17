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

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-[#121212] border border-[#2D2D2D] rounded-xl p-3.5 text-xs shadow-2xl text-[#F2F2F2] min-w-[210px]">
        <div className="flex items-center justify-between border-b border-[#222222] pb-2 mb-2">
          <span className="font-bold text-[14px] text-[#F2F2F2]">{label}</span>
          <span className="text-[11px] px-2 py-0.5 rounded bg-[#1A1A1A] border border-[#2D2D2D] text-[#D4AF57] font-semibold">
            {data.competition}
          </span>
        </div>

        <div className="space-y-1.5 font-sans">
          <div className="flex items-center justify-between">
            <span className="text-[#858585]">Total Runs:</span>
            <span className="font-bold text-[#F2F2F2] text-[14px] tabular-nums font-sans">
              {data.runs}
            </span>
          </div>

          {data.ipl_runs !== null && data.t20i_runs !== null && (
            <div className="pl-2 border-l border-[#2D2D2D] space-y-1 text-[11.5px]">
              <div className="flex items-center justify-between text-[#D4AF57]">
                <span>• IPL Runs:</span>
                <span className="tabular-nums font-semibold">{data.ipl_runs}</span>
              </div>
              <div className="flex items-center justify-between text-[#5A9E60]">
                <span>• International Runs:</span>
                <span className="tabular-nums font-semibold">{data.t20i_runs}</span>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between text-[#B8B8B8] pt-1 border-t border-[#222222]">
            <span>Batting Innings:</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">
              {data.batting_innings} <span className="text-[#858585] font-normal">({data.matches} matches)</span>
            </span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8]">
            <span>Balls Faced:</span>
            <span className="tabular-nums font-semibold text-[#F2F2F2]">{data.balls_faced}</span>
          </div>

          <div className="flex items-center justify-between text-[#B8B8B8]">
            <span>Season Strike Rate:</span>
            <span className="tabular-nums font-bold text-[#D4AF57]">{data.strike_rate ?? '—'}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function CareerRunsChart({ timeline = [], isCombined = false }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="h-[280px] flex items-center justify-center text-[#858585] text-sm">
        No seasonal runs data available.
      </div>
    );
  }

  return (
    <div className="w-full h-[320px] sm:h-[350px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
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
            allowDecimals={false}
          />
          <Tooltip content={<CustomTooltip />} />
          {isCombined ? (
            <>
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ paddingBottom: '10px', fontSize: '12px' }}
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
                radius={[4, 4, 0, 0]}
              />
            </>
          ) : (
            <Bar
              dataKey="runs"
              name="Total Runs"
              fill="#D4AF57"
              radius={[4, 4, 0, 0]}
            />
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
