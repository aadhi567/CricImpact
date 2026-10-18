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
  ReferenceLine,
} from 'recharts';
import { useWindowWidth } from '../../hooks/useWindowWidth';

const PLAYER_COLORS = ['#D4AF57', '#E1C878', '#A8893D', '#5A9E60', '#B8B8B8'];

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#161616]/95 border border-[#2D2D2D] rounded-lg p-2.5 sm:p-3 text-[11px] sm:text-xs shadow-xl text-[#F2F2F2] max-w-[calc(100vw-32px)] sm:max-w-xs pointer-events-none select-none backdrop-blur-xs">
        <div className="font-bold text-[#F2F2F2] mb-1 font-mono text-xs sm:text-[13px] truncate">{label}</div>
        <div className="space-y-1">
          {payload.map((entry, idx) => (
            <div key={idx} className="flex items-center justify-between gap-3 text-[11px] sm:text-xs">
              <span className="flex items-center gap-1.5 font-medium truncate" style={{ color: entry.color }}>
                <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: entry.color }} />
                <span className="truncate">{entry.name}:</span>
              </span>
              <span className="font-mono font-bold text-[#F2F2F2] tabular-nums shrink-0">
                {entry.value !== null && entry.value !== undefined ? Number(entry.value).toFixed(1) : '—'}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
}

export default function PrimaryMetricsComparisonChart({ players = [] }) {
  const width = useWindowWidth();
  const isMobile = width < 640;
  const isNarrowMobile = width < 400;

  if (!players || players.length === 0) return null;

  const metricDefs = [
    { key: 'contribution_score', name: 'Contribution Score (0–100)' },
    { key: 'season_team_contribution_share', name: 'Team Share (%)' },
  ];

  const chartData = metricDefs.map(({ key, name }) => {
    const item = { metric: name };
    players.forEach((p) => {
      const val = p[key];
      item[p.player] = val !== null && val !== undefined ? Number(val) : null;
    });
    return item;
  });

  return (
    <div className="bg-[#161616] rounded-xl p-3 sm:p-4 border border-[#2D2D2D]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 sm:gap-2 mb-2.5 sm:mb-3">
        <div>
          <h3 className="font-heading text-[14px] sm:text-[16px] font-bold text-[#F2F2F2] tracking-tight">
            Contribution score vs. team share
          </h3>
          <p className="text-[10.5px] sm:text-xs font-normal text-[#858585] mt-0.5">
            Compares average situational efficiency against relative team attribution.
          </p>
        </div>
        <div className="text-[10px] sm:text-[11px] text-[#B8B8B8] bg-[#101010] px-2 py-0.5 rounded border border-[#2D2D2D] font-mono font-semibold self-start sm:self-auto shrink-0">
          Dual perspectives
        </div>
      </div>

      <div className="w-full h-56 sm:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={
              isMobile
                ? { top: 10, right: 8, bottom: 15, left: -16 }
                : { top: 15, right: 15, bottom: 20, left: -10 }
            }
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
            <XAxis
              dataKey="metric"
              stroke="#858585"
              tick={{ fontSize: isNarrowMobile ? 9 : (isMobile ? 10 : 11), fill: '#858585' }}
              tickFormatter={(val) =>
                isMobile
                  ? val.startsWith('Contribution')
                    ? 'Score (0–100)'
                    : 'Team Share (%)'
                  : val
              }
              height={isMobile ? 32 : 36}
            />
            <YAxis
              domain={[0, 100]}
              stroke="#858585"
              tick={{ fontSize: isMobile ? 10 : 11, fill: '#858585' }}
              label={
                !isMobile
                  ? { value: 'Value (0–100 / %)', angle: -90, position: 'insideLeft', fill: '#858585', fontSize: 11, offset: 15 }
                  : undefined
              }
              width={isMobile ? 32 : 40}
            />
            <ReferenceLine y={50} stroke="#D4AF57" strokeDasharray="4 4" label={!isMobile ? { value: 'Par 50', fill: '#D4AF57', fontSize: 10, position: 'right' } : undefined} />
            <Tooltip
              content={<CustomTooltip />}
              wrapperStyle={{ outline: 'none', zIndex: 50, pointerEvents: 'none' }}
            />
            <Legend
              wrapperStyle={{ paddingTop: isMobile ? 4 : 10, fontSize: isMobile ? 11 : 12 }}
              formatter={(value) => <span className="text-[#F2F2F2] font-semibold">{value}</span>}
            />
            {players.map((p, idx) => (
              <Bar
                key={p.player}
                dataKey={p.player}
                name={p.player}
                fill={PLAYER_COLORS[idx % PLAYER_COLORS.length]}
                radius={[3, 3, 0, 0]}
                maxBarSize={isMobile ? 22 : 28}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 text-center text-[10px] sm:text-[11px] text-[#858585]">
        * Contribution Score: Contextual performance against situational expectations. Team Contribution Share: Batter's share of team positive contribution.
      </div>
    </div>
  );
}
