import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import { TrendingUp, BarChart3, AlertCircle } from 'lucide-react';
import { useWindowWidth } from '../../hooks/useWindowWidth';
import {
  calculateTickInterval,
  computeTimelineSummary,
  prepareTimelineChartData,
} from '../../utils/timelineUtils';

/**
 * Premium custom tooltip for the Match Contribution Timeline.
 * Displays full chronological context, opponent, batting figures,
 * exact contribution score, and deviation from par (50.0).
 */
function CustomTimelineTooltip({ active, payload, viewMode }) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  if (!data) return null;

  const isDnb = Boolean(data.is_dnb);
  if (isDnb) {
    return (
      <div className="bg-[#141414]/95 border border-[#2D2D2D] rounded-xl p-3 text-xs shadow-2xl text-[#F2F2F2] max-w-xs pointer-events-none select-none backdrop-blur-md">
        <div className="font-bold text-sm text-[#F2F2F2]">{data.full_date || data.display_date}</div>
        <div className="text-[#858585] text-xs">vs {data.opponent}</div>
        <div className="text-[#C25454] font-semibold mt-1.5 flex items-center gap-1">
          <AlertCircle className="w-3.5 h-3.5" />
          Did Not Bat (DNB) — Unrated
        </div>
      </div>
    );
  }

  const score = data.contribution_score;
  const deviation = data.deviation;
  const isPositive = deviation >= 0;

  return (
    <div className="bg-[#141414]/95 border border-[#2D2D2D] rounded-xl p-3.5 text-xs shadow-2xl text-[#F2F2F2] min-w-[220px] max-w-xs pointer-events-none select-none backdrop-blur-md z-50">
      {/* Header: Date and Match Context */}
      <div className="border-b border-[#262626] pb-2">
        <div className="flex items-center justify-between text-[11px] text-[#858585] mb-0.5">
          <span>Match #{data.match_number}</span>
          <span className="font-mono text-[#D4AF57]">{data.display_date}</span>
        </div>
        <div className="font-bold text-[13px] text-[#F2F2F2] truncate">
          vs {data.opponent}
        </div>
        {data.venue && (
          <div className="text-[10.5px] text-[#858585] truncate mt-0.5">
            {data.venue}
          </div>
        )}
      </div>

      {/* Batting Inning Figures */}
      <div className="py-2 border-b border-[#262626] space-y-1">
        <div className="flex items-center justify-between text-[#B8B8B8]">
          <span>Innings Score:</span>
          <span className="font-bold text-[#F2F2F2] tabular-nums font-mono">
            {data.runs} <span className="text-[#858585] font-normal">runs ({data.balls}b)</span>
            {data.is_not_out ? ' *' : ''}
          </span>
        </div>
        <div className="flex items-center justify-between text-[#858585] text-[11px]">
          <span>Strike Rate:</span>
          <span className="font-mono text-[#F2F2F2] tabular-nums">
            {data.strike_rate !== null ? data.strike_rate : '—'}
          </span>
        </div>
      </div>

      {/* Model Rating Metrics */}
      <div className="pt-2 space-y-1.5">
        <div
          className={`flex items-center justify-between transition-colors ${
            viewMode === 'score' ? 'bg-[#1F1F1F] px-1.5 py-0.5 rounded' : ''
          }`}
        >
          <span className="text-[#858585]">Contribution Score:</span>
          <span className="font-bold font-mono text-[13px] text-[#D4AF57] tabular-nums">
            {score !== null ? score.toFixed(1) : '—'}
            <span className="text-[10px] text-[#858585] font-normal"> / 100</span>
          </span>
        </div>

        <div
          className={`flex items-center justify-between transition-colors ${
            viewMode === 'deviation' ? 'bg-[#1F1F1F] px-1.5 py-0.5 rounded' : ''
          }`}
        >
          <span className="text-[#858585]">Deviation from Par:</span>
          <span
            className={`font-semibold font-mono text-[11.5px] tabular-nums px-1.5 py-0.5 rounded ${
              isPositive
                ? 'text-[#5A9E60] bg-[#152718] border border-[#2A4D30]'
                : 'text-[#C25454] bg-[#271414] border border-[#4D2626]'
            }`}
          >
            {isPositive ? `+${deviation.toFixed(1)}` : deviation.toFixed(1)} vs Par (50)
          </span>
        </div>

        {data.raw_contribution !== null && (
          <div className="flex items-center justify-between text-[10.5px] text-[#858585] pt-0.5">
            <span>Raw Context (C_raw):</span>
            <span className="font-mono tabular-nums">
              {data.raw_contribution > 0 ? `+${data.raw_contribution.toFixed(3)}` : data.raw_contribution.toFixed(3)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Custom point marker (Dot) that dynamically color-codes
 * scores above par (green), at par (gold), and below par (coral).
 */
function renderCustomTimelineDot(props, isMobile) {
  const { cx, cy, payload } = props;
  if (cx === undefined || cy === undefined || !payload) return null;

  const score = payload.contribution_score;
  if (score === null || score === undefined) return null;

  let fill = '#D4AF57';
  let stroke = '#8C7030';

  if (score > 50.0) {
    fill = '#5A9E60'; // Above Par
    stroke = '#2A4D30';
  } else if (score < 50.0) {
    fill = '#C25454'; // Below Par
    stroke = '#4D2626';
  }

  const radius = isMobile ? 3 : 4;

  return (
    <circle
      key={`dot-${payload.index}`}
      cx={cx}
      cy={cy}
      r={radius}
      fill={fill}
      stroke={stroke}
      strokeWidth={1.5}
      className="transition-transform duration-150"
    />
  );
}

export default function MatchScoreTimeline({ matches = [] }) {
  const width = useWindowWidth();
  const isMobile = width < 640;
  const isNarrowMobile = width < 400;

  // View Mode: 'score' (0–100 with Par=50) | 'deviation' (±50 with Baseline=0)
  const [viewMode, setViewMode] = useState('score');

  // Compute summary metrics (matches played, rated, above/below par, best score, recent form)
  const summary = useMemo(() => computeTimelineSummary(matches), [matches]);

  // Transform and sort match records chronologically
  const chartData = useMemo(
    () => prepareTimelineChartData(matches, viewMode),
    [matches, viewMode]
  );

  // Calculate non-overlapping tick intervals dynamically
  const tickInterval = useMemo(
    () => calculateTickInterval(chartData.length, width),
    [chartData.length, width]
  );

  if (chartData.length === 0) {
    return (
      <div className="bg-[#161616] rounded-xl p-6 border border-[#2D2D2D] text-center text-[#858585]">
        <AlertCircle className="w-6 h-6 text-[#858585] mx-auto mb-2 opacity-60" />
        <h4 className="text-sm font-semibold text-[#F2F2F2]">No Rated Batting Innings</h4>
        <p className="text-xs text-[#858585] mt-1 max-w-sm mx-auto">
          No rated batting performances found for this selection. Matches where the player did not bat (DNB) are excluded from the performance timeline.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-[#161616] rounded-xl p-3.5 sm:p-5 border border-[#2D2D2D] shadow-xs flex flex-col justify-between">
      {/* 1. Header & View Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-heading text-[15px] sm:text-[16px] font-bold text-[#F2F2F2] tracking-tight">
              Match-by-match contribution score
            </h3>
          </div>
          <p className="text-[11px] sm:text-xs text-[#858585] mt-0.5">
            {viewMode === 'score'
              ? 'Chronological progression of innings performance relative to Par (50.0).'
              : 'Situational deviation from baseline par rating (Score − 50.0).'}
          </p>
        </div>

        {/* View Toggle Buttons */}
        <div className="inline-flex rounded-lg bg-[#101010] p-1 border border-[#2D2D2D] self-start sm:self-auto shrink-0">
          <button
            type="button"
            onClick={() => setViewMode('score')}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11.5px] font-semibold transition-all cursor-pointer ${
              viewMode === 'score'
                ? 'bg-[#D4AF57] text-[#080808] shadow-xs'
                : 'text-[#858585] hover:text-[#F2F2F2]'
            }`}
            aria-pressed={viewMode === 'score'}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Score (0–100)</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode('deviation')}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11.5px] font-semibold transition-all cursor-pointer ${
              viewMode === 'deviation'
                ? 'bg-[#D4AF57] text-[#080808] shadow-xs'
                : 'text-[#858585] hover:text-[#F2F2F2]'
            }`}
            aria-pressed={viewMode === 'deviation'}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Deviation (±50)</span>
          </button>
        </div>
      </div>

      {/* 2. Summary Statistics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-2.5 mb-4">
        {/* Card 1: Matches & Rated */}
        <div className="bg-[#101010] rounded-lg p-2.5 border border-[#242424] flex flex-col justify-between">
          <div className="text-[10px] sm:text-[10.5px] font-semibold uppercase tracking-wider text-[#858585]">
            Appearances
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-base sm:text-lg font-bold font-mono text-[#F2F2F2] tabular-nums">
              {summary.ratedCount}
            </span>
            <span className="text-xs text-[#858585] font-normal">
              / {summary.totalMatches} matches
            </span>
          </div>
          <div className="text-[10px] text-[#858585] mt-1 truncate">
            {summary.dnbCount > 0 ? `${summary.dnbCount} DNB excluded` : '100% Batting rate'}
          </div>
        </div>

        {/* Card 2: Performance vs Par */}
        <div className="bg-[#101010] rounded-lg p-2.5 border border-[#242424] flex flex-col justify-between">
          <div className="text-[10px] sm:text-[10.5px] font-semibold uppercase tracking-wider text-[#858585]">
            Above / Below Par
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-base sm:text-lg font-bold font-mono text-[#5A9E60] tabular-nums">
              {summary.aboveParCount}▲
            </span>
            <span className="text-xs text-[#858585]">/</span>
            <span className="text-base sm:text-lg font-bold font-mono text-[#C25454] tabular-nums">
              {summary.belowParCount}▼
            </span>
          </div>
          <div className="text-[10px] text-[#858585] mt-1 truncate">
            {summary.aboveParPct !== null ? `${summary.aboveParPct}% above par` : 'N/A'}
          </div>
        </div>

        {/* Card 3: Best Score */}
        <div className="bg-[#101010] rounded-lg p-2.5 border border-[#242424] flex flex-col justify-between">
          <div className="text-[10px] sm:text-[10.5px] font-semibold uppercase tracking-wider text-[#858585]">
            Best Match Score
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-base sm:text-lg font-bold font-mono text-[#D4AF57] tabular-nums">
              {summary.bestScore !== null ? summary.bestScore.toFixed(1) : '—'}
            </span>
            <span className="text-[10px] text-[#858585]">/ 100</span>
          </div>
          <div className="text-[10px] text-[#858585] mt-1 truncate" title={summary.bestMatch ? `vs ${summary.bestMatch.opponent}` : ''}>
            {summary.bestMatch
              ? `vs ${summary.bestMatch.opponent}`
              : 'No rated innings'}
          </div>
        </div>

        {/* Card 4: Recent Form (Latest 5 Rated) */}
        <div className="bg-[#101010] rounded-lg p-2.5 border border-[#242424] flex flex-col justify-between">
          <div className="text-[10px] sm:text-[10.5px] font-semibold uppercase tracking-wider text-[#858585]">
            Recent Form ({summary.recentFormCount > 0 ? `L${summary.recentFormCount}` : 'L5'})
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span
              className={`text-base sm:text-lg font-bold font-mono tabular-nums ${
                summary.recentFormAvg === null
                  ? 'text-[#858585]'
                  : summary.recentFormAvg >= 50.0
                  ? 'text-[#5A9E60]'
                  : 'text-[#C25454]'
              }`}
            >
              {summary.recentFormAvg !== null ? summary.recentFormAvg.toFixed(1) : '—'}
            </span>
            {summary.recentFormAvg !== null && (
              <span className="text-[10.5px] font-mono text-[#858585]">
                ({summary.recentFormAvg >= 50.0 ? '+' : ''}{(summary.recentFormAvg - 50.0).toFixed(1)})
              </span>
            )}
          </div>
          <div className="text-[10px] text-[#858585] mt-1 truncate">
            {summary.recentFormAvg !== null
              ? summary.recentFormAvg >= 50.0
                ? 'Positive form trend'
                : 'Sub-par recent trend'
              : 'Insufficient data'}
          </div>
        </div>
      </div>

      {/* 3. Visual Legend */}
      <div className="flex flex-wrap items-center justify-between text-[11px] text-[#858585] mb-2 px-1 gap-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#5A9E60] border border-[#2A4D30] inline-block" />
            <span>Above Par (&gt;50)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#D4AF57] border border-[#8C7030] inline-block" />
            <span>At Par (=50)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#C25454] border border-[#4D2626] inline-block" />
            <span>Below Par (&lt;50)</span>
          </div>
        </div>
        <div className="text-[10.5px] font-mono text-[#D4AF57]">
          {viewMode === 'score' ? 'Benchmark Par = 50.0' : 'Baseline = 0.0 (Par 50)'}
        </div>
      </div>

      {/* 4. Chart Visualization */}
      <div className="w-full h-56 sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{
              top: 12,
              right: isMobile ? 35 : 45,
              bottom: isMobile ? 24 : 28,
              left: isMobile ? -14 : -6,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />

            <XAxis
              dataKey="display_date"
              stroke="#858585"
              tick={{
                fontSize: isNarrowMobile ? 8.5 : isMobile ? 9.5 : 10.5,
                fill: '#858585',
              }}
              interval={tickInterval}
              angle={-25}
              textAnchor="end"
              height={isMobile ? 36 : 42}
            />

            {viewMode === 'score' ? (
              <YAxis
                domain={[0, 100]}
                ticks={[0, 25, 50, 75, 100]}
                stroke="#858585"
                tick={{ fontSize: isMobile ? 10 : 11, fill: '#858585' }}
                label={
                  !isMobile
                    ? {
                        value: 'Contribution Score (0–100)',
                        angle: -90,
                        position: 'insideLeft',
                        fill: '#858585',
                        fontSize: 10.5,
                        offset: 14,
                      }
                    : undefined
                }
                width={isMobile ? 32 : 40}
              />
            ) : (
              <YAxis
                domain={[-50, 50]}
                ticks={[-50, -25, 0, 25, 50]}
                stroke="#858585"
                tick={{ fontSize: isMobile ? 10 : 11, fill: '#858585' }}
                label={
                  !isMobile
                    ? {
                        value: 'Deviation vs Par (Score − 50)',
                        angle: -90,
                        position: 'insideLeft',
                        fill: '#858585',
                        fontSize: 10.5,
                        offset: 14,
                      }
                    : undefined
                }
                width={isMobile ? 34 : 42}
              />
            )}

            {/* Benchmark Reference Line: Par 50 for score view, Par 0 for deviation view */}
            <ReferenceLine
              y={viewMode === 'deviation' ? 0 : 50}
              stroke="#D4AF57"
              strokeDasharray="4 4"
              strokeWidth={1.5}
              label={{
                value: viewMode === 'deviation' ? 'Par (0.0)' : 'Par (50.0)',
                fill: '#D4AF57',
                fontSize: 10,
                position: 'insideTopRight',
                offset: 8,
              }}
            />

            <Tooltip
              content={<CustomTimelineTooltip viewMode={viewMode} />}
              wrapperStyle={{ outline: 'none', zIndex: 50, pointerEvents: 'none' }}
            />

            {viewMode === 'score' ? (
              <>
                {/* Subtle neutral background bar */}
                <Bar
                  dataKey="plot_value"
                  fill="#222222"
                  radius={[3, 3, 0, 0]}
                  maxBarSize={isMobile ? 18 : 26}
                />
                {/* Connected, data-faithful score line */}
                <Line
                  type="monotone"
                  dataKey="plot_value"
                  stroke="#D4AF57"
                  strokeWidth={2}
                  dot={(props) => renderCustomTimelineDot(props, isMobile)}
                  activeDot={{ r: 6, stroke: '#FFFFFF', strokeWidth: 2 }}
                />
              </>
            ) : (
              <>
                {/* Diverging positive/negative deviation bars */}
                <Bar
                  dataKey="plot_value"
                  maxBarSize={isMobile ? 18 : 26}
                >
                  {chartData.map((entry) => (
                    <Cell
                      key={`dev-cell-${entry.match_id}`}
                      fill={entry.deviation >= 0 ? '#5A9E60' : '#C25454'}
                      stroke={entry.deviation >= 0 ? '#2A4D30' : '#4D2626'}
                      strokeWidth={1}
                      radius={entry.deviation >= 0 ? [3, 3, 0, 0] : [0, 0, 3, 3]}
                    />
                  ))}
                </Bar>
                {/* Connecting trend line for deviation */}
                <Line
                  type="monotone"
                  dataKey="plot_value"
                  stroke="#B8B8B8"
                  strokeWidth={1.5}
                  dot={(props) => renderCustomTimelineDot(props, isMobile)}
                  activeDot={{ r: 6, stroke: '#FFFFFF', strokeWidth: 2 }}
                />
              </>
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
