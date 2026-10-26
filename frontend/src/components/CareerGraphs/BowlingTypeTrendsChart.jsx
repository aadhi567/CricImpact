import React, { useState, useMemo } from 'react';
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
import {
  Zap,
  Activity,
  Shield,
  AlertTriangle,
  CheckCircle2,
  ArrowUpDown,
} from 'lucide-react';
import { useWindowWidth } from '../../hooks/useWindowWidth';

function CustomBowlingTooltip({ active, payload, label, selectedBowlingType = 'both', chartMetricView = 'strike_rate' }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const pace = data.pace || {};
    const spin = data.spin || {};

    const showPace = selectedBowlingType === 'both' || selectedBowlingType === 'pace';
    const showSpin = selectedBowlingType === 'both' || selectedBowlingType === 'spin';
    const isDismissalsView = chartMetricView === 'dismissals';

    return (
      <div className="bg-[#121212]/95 border border-[#2D2D2D] rounded-lg p-2.5 sm:p-4 text-[11px] sm:text-xs shadow-2xl text-[#F2F2F2] max-w-[calc(100vw-32px)] sm:max-w-sm min-w-[190px] sm:min-w-[280px] font-sans pointer-events-none select-none backdrop-blur-xs">
        <div className="flex items-center justify-between border-b border-[#222222] pb-1.5 mb-1.5 gap-2">
          <span className="font-bold text-xs sm:text-[14px] text-[#F2F2F2] truncate">{label}</span>
          <span className="text-[10px] sm:text-[11px] px-1.5 py-0.5 rounded bg-[#1A1A1A] border border-[#2D2D2D] text-[#D4AF57] font-semibold shrink-0">
            {data.competition || 'Season'}
          </span>
        </div>

        <div className="space-y-2 sm:space-y-3 font-sans">
          {/* Pace Stats */}
          {showPace && (
            <div className="bg-[#181611] p-2 sm:p-2.5 rounded-lg border border-[#D4AF57]/30 space-y-0.5 sm:space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-[#D4AF57] flex items-center gap-1.5 text-[11px] sm:text-xs">
                  <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-[#D4AF57] inline-block" />
                  {isDismissalsView ? 'Pace Outs' : 'Pace Bowling'}
                </span>
                <span className="font-bold text-xs sm:text-[14px] tabular-nums text-[#D4AF57]">
                  {isDismissalsView ? (
                    <>
                      {data.pace_dismissals ?? pace.dismissals ?? 0}
                      <span className="text-[10px] text-[#858585] font-normal ml-0.5">outs</span>
                    </>
                  ) : (
                    <>
                      {pace.strike_rate !== null && pace.strike_rate !== undefined ? `${pace.strike_rate}` : '—'}
                      <span className="text-[10px] text-[#858585] font-normal ml-0.5">SR</span>
                    </>
                  )}
                </span>
              </div>
              {isDismissalsView && (
                <div className="text-[11px] text-[#B8B8B8] flex items-center justify-between pt-1 border-t border-[#D4AF57]/15">
                  <span>Strike Rate:</span>
                  <span className="text-[#F2F2F2] tabular-nums font-medium">
                    {pace.strike_rate !== null && pace.strike_rate !== undefined ? `${pace.strike_rate}` : '—'}
                  </span>
                </div>
              )}
              <div className={`text-[11px] text-[#B8B8B8] flex items-center justify-between ${!isDismissalsView ? 'pt-1 border-t border-[#D4AF57]/15' : ''}`}>
                <span>Runs &amp; Balls:</span>
                <span className="text-[#F2F2F2] tabular-nums font-medium">
                  {pace.runs} runs / {pace.balls_faced} balls
                </span>
              </div>
              <div className="text-[11px] text-[#B8B8B8] flex items-center justify-between">
                <span>Avg per Dismissal:</span>
                <span className="text-[#F2F2F2] tabular-nums font-medium">
                  {pace.average !== null ? pace.average : pace.is_not_out ? 'Not Out' : '—'}
                  {!isDismissalsView && pace.dismissals !== undefined ? ` (${pace.dismissals} outs)` : ''}
                </span>
              </div>
              <div className="text-[11px] text-[#B8B8B8] flex items-center justify-between">
                <span>Dot % &bull; Boundary %:</span>
                <span className="text-[#F2F2F2] tabular-nums font-medium">
                  {pace.dot_ball_percentage !== null ? `${pace.dot_ball_percentage}%` : '—'} &bull;{' '}
                  {pace.boundary_percentage !== null ? `${pace.boundary_percentage}%` : '—'}
                </span>
              </div>
              {pace.insufficient_sample && (
                <div className="text-[10px] text-[#E5A84B] flex items-center gap-1 pt-1">
                  <AlertTriangle className="w-3 h-3 shrink-0" />
                  <span>Small sample (&lt;20 balls faced)</span>
                </div>
              )}
            </div>
          )}

          {/* Spin Stats */}
          {showSpin && (
            <div className="bg-[#10171F] p-2 sm:p-2.5 rounded-lg border border-[#6BA8E5]/30 space-y-0.5 sm:space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-[#6BA8E5] flex items-center gap-1.5 text-[11px] sm:text-xs">
                  <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-[#6BA8E5] inline-block" />
                  {isDismissalsView ? 'Spin Outs' : 'Spin Bowling'}
                </span>
                <span className="font-bold text-xs sm:text-[14px] tabular-nums text-[#6BA8E5]">
                  {isDismissalsView ? (
                    <>
                      {data.spin_dismissals ?? spin.dismissals ?? 0}
                      <span className="text-[10px] text-[#858585] font-normal ml-0.5">outs</span>
                    </>
                  ) : (
                    <>
                      {spin.strike_rate !== null && spin.strike_rate !== undefined ? `${spin.strike_rate}` : '—'}
                      <span className="text-[10px] text-[#858585] font-normal ml-0.5">SR</span>
                    </>
                  )}
                </span>
              </div>
              {isDismissalsView && (
                <div className="text-[11px] text-[#B8B8B8] flex items-center justify-between pt-1 border-t border-[#6BA8E5]/15">
                  <span>Strike Rate:</span>
                  <span className="text-[#F2F2F2] tabular-nums font-medium">
                    {spin.strike_rate !== null && spin.strike_rate !== undefined ? `${spin.strike_rate}` : '—'}
                  </span>
                </div>
              )}
              <div className={`text-[11px] text-[#B8B8B8] flex items-center justify-between ${!isDismissalsView ? 'pt-1 border-t border-[#6BA8E5]/15' : ''}`}>
                <span>Runs &amp; Balls:</span>
                <span className="text-[#F2F2F2] tabular-nums font-medium">
                  {spin.runs} runs / {spin.balls_faced} balls
                </span>
              </div>
              <div className="text-[11px] text-[#B8B8B8] flex items-center justify-between">
                <span>Avg per Dismissal:</span>
                <span className="text-[#F2F2F2] tabular-nums font-medium">
                  {spin.average !== null ? spin.average : spin.is_not_out ? 'Not Out' : '—'}
                  {!isDismissalsView && spin.dismissals !== undefined ? ` (${spin.dismissals} outs)` : ''}
                </span>
              </div>
              <div className="text-[11px] text-[#B8B8B8] flex items-center justify-between">
                <span>Dot % &bull; Boundary %:</span>
                <span className="text-[#F2F2F2] tabular-nums font-medium">
                  {spin.dot_ball_percentage !== null ? `${spin.dot_ball_percentage}%` : '—'} &bull;{' '}
                  {spin.boundary_percentage !== null ? `${spin.boundary_percentage}%` : '—'}
                </span>
              </div>
              {spin.insufficient_sample && (
                <div className="text-[10px] text-[#E5A84B] flex items-center gap-1 pt-1">
                  <AlertTriangle className="w-3 h-3 shrink-0" />
                  <span>Small sample (&lt;20 balls faced)</span>
                </div>
              )}
            </div>
          )}

          {/* Coverage note */}
          <div className="text-[10px] text-[#858585] pt-1 border-t border-[#222222] flex items-center justify-between">
            <span>Verified Data Coverage:</span>
            <span className="font-semibold text-[#D4AF57]">
              {data.coverage_percentage !== null && data.coverage_percentage !== undefined ? `${data.coverage_percentage}%` : '—'}
            </span>
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export default function BowlingTypeTrendsChart({ bowlingTrends }) {
  const width = useWindowWidth();
  const isMobile = width < 640;
  const isNarrowMobile = width < 400;

  // Selector state: 'both' | 'pace' | 'spin' (default to 'both')
  const [selectedBowlingType, setSelectedBowlingType] = useState('both');
  // Chart view: 'strike_rate' | 'dismissals'
  const [chartMetricView, setChartMetricView] = useState('strike_rate');
  const [tableSortField, setTableSortField] = useState('season');
  const [tableSortDir, setTableSortDir] = useState('asc');

  const seasons = useMemo(() => bowlingTrends?.seasons || [], [bowlingTrends?.seasons]);
  const summary = bowlingTrends?.summary || {};

  const showPace = selectedBowlingType === 'both' || selectedBowlingType === 'pace';
  const showSpin = selectedBowlingType === 'both' || selectedBowlingType === 'spin';

  // Prepare chart dataset
  const chartData = useMemo(() => {
    return seasons.map((s) => ({
      ...s,
      pace_sr: s.pace?.strike_rate,
      spin_sr: s.spin?.strike_rate,
      pace_dismissals: s.pace_dismissals ?? s.pace?.dismissals ?? 0,
      spin_dismissals: s.spin_dismissals ?? s.spin?.dismissals ?? 0,
    }));
  }, [seasons]);

  // Overall career benchmarks
  const paceSummary = summary?.pace || {};
  const spinSummary = summary?.spin || {};
  const totalBalls = summary?.total_balls_faced ?? 0;
  const isCompleteCoverage = summary?.is_coverage_complete !== false && totalBalls > 0;
  const coveragePct = summary?.coverage_percentage ?? (totalBalls === 0 ? null : 100.0);

  // Sortable season table
  const sortedSeasons = useMemo(() => {
    return [...seasons].sort((a, b) => {
      let aVal = a[tableSortField];
      let bVal = b[tableSortField];

      if (tableSortField.startsWith('pace_')) {
        const sub = tableSortField.replace('pace_', '');
        aVal = a[tableSortField] ?? a.pace?.[sub];
        bVal = b[tableSortField] ?? b.pace?.[sub];
      } else if (tableSortField.startsWith('spin_')) {
        const sub = tableSortField.replace('spin_', '');
        aVal = a[tableSortField] ?? a.spin?.[sub];
        bVal = b[tableSortField] ?? b.spin?.[sub];
      }

      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      if (typeof aVal === 'string') {
        return tableSortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return tableSortDir === 'asc' ? aVal - bVal : bVal - aVal;
    });
  }, [seasons, tableSortField, tableSortDir]);

  if (!bowlingTrends || !bowlingTrends.seasons || bowlingTrends.seasons.length === 0) {
    return (
      <div className="bg-[#161616] rounded-xl p-8 border border-[#2D2D2D] text-center space-y-2">
        <div className="text-[#858585] text-sm">
          No bowling-type delivery data recorded for this selection.
        </div>
      </div>
    );
  }

  const handleTableSort = (field) => {
    if (tableSortField === field) {
      setTableSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setTableSortField(field);
      setTableSortDir('desc');
    }
  };

  const bowlingOptions = [
    { id: 'pace', label: 'Pace' },
    { id: 'spin', label: 'Spin' },
    { id: 'both', label: 'Both' },
  ];

  const handleKeyDown = (e) => {
    const optionIds = ['pace', 'spin', 'both'];
    const currentIndex = optionIds.indexOf(selectedBowlingType);
    let nextIndex = -1;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      nextIndex = (currentIndex + 1) % optionIds.length;
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      nextIndex = (currentIndex - 1 + optionIds.length) % optionIds.length;
    }
    if (nextIndex !== -1) {
      const nextId = optionIds[nextIndex];
      setSelectedBowlingType(nextId);
      const btn = document.getElementById(`bowling-selector-graph-${nextId}`);
      if (btn) btn.focus();
    }
  };

  return (
    <div className="bg-[#161616] rounded-xl p-3.5 sm:p-6 border border-[#2D2D2D] shadow-xs space-y-4 sm:space-y-6 font-sans">
      {/* Section Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#222222] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="text-xs font-bold text-[#D4AF57] tracking-wider uppercase px-2 py-0.5 bg-[#1F1B12] rounded border border-[#A8893D]/30">
              Matchup Diagnostics
            </span>
            <h3 className="font-heading text-xl sm:text-2xl font-bold text-[#F2F2F2] tracking-tight">
              Bowling-Type Performance Trends
            </h3>
          </div>
          <p className="text-xs text-[#858585] mt-1 max-w-2xl">
            Season-by-season execution breakdown against <strong>Pace</strong> vs{' '}
            <strong>Spin</strong> bowling. Derived directly from verified delivery registries with
            strict sample validation and auditable bowler-style classification.
          </p>
        </div>
      </div>

      {/* 3 Career Baseline KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {/* Card 1: Overall vs Pace */}
        <div className="bg-[#101010] p-4 rounded-xl border border-[#2D2D2D] relative overflow-hidden space-y-3">
          <div className="flex items-center justify-between border-b border-[#222222] pb-2.5">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-[#D4AF57]" />
              <span className="text-xs font-bold text-[#F2F2F2] uppercase tracking-wider">
                Career vs Pace
              </span>
            </div>
            <span className="text-[11px] text-[#A8893D] font-semibold bg-[#1F1B12] px-2 py-0.5 rounded border border-[#A8893D]/30">
              {paceSummary.balls_faced?.toLocaleString()} balls
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-[#858585] block text-[11px]">Strike Rate</span>
              <span className="text-[20px] font-bold text-[#D4AF57] tabular-nums">
                {paceSummary.strike_rate ?? '—'}
              </span>
            </div>
            <div>
              <span className="text-[#858585] block text-[11px]">Batting Average</span>
              <span className="text-[20px] font-bold text-[#F2F2F2] tabular-nums">
                {paceSummary.average !== null ? paceSummary.average : paceSummary.is_not_out ? 'Not Out' : '—'}
              </span>
            </div>
            <div>
              <span className="text-[#858585] block text-[11px]">Runs (Dismissals)</span>
              <span className="text-[#F2F2F2] font-semibold tabular-nums">
                {paceSummary.runs?.toLocaleString()} r ({paceSummary.dismissals} outs)
              </span>
            </div>
            <div>
              <span className="text-[#858585] block text-[11px]">Dot % &bull; Boundary %</span>
              <span className="text-[#F2F2F2] font-semibold tabular-nums">
                {paceSummary.dot_ball_percentage ?? '—'}% &bull; {paceSummary.boundary_percentage ?? '—'}%
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: Overall vs Spin */}
        <div className="bg-[#101010] p-4 rounded-xl border border-[#2D2D2D] relative overflow-hidden space-y-3">
          <div className="flex items-center justify-between border-b border-[#222222] pb-2.5">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#6BA8E5]" />
              <span className="text-xs font-bold text-[#F2F2F2] uppercase tracking-wider">
                Career vs Spin
              </span>
            </div>
            <span className="text-[11px] text-[#6BA8E5] font-semibold bg-[#101A24] px-2 py-0.5 rounded border border-[#6BA8E5]/30">
              {spinSummary.balls_faced?.toLocaleString()} balls
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-[#858585] block text-[11px]">Strike Rate</span>
              <span className="text-[20px] font-bold text-[#6BA8E5] tabular-nums">
                {spinSummary.strike_rate ?? '—'}
              </span>
            </div>
            <div>
              <span className="text-[#858585] block text-[11px]">Batting Average</span>
              <span className="text-[20px] font-bold text-[#F2F2F2] tabular-nums">
                {spinSummary.average !== null ? spinSummary.average : spinSummary.is_not_out ? 'Not Out' : '—'}
              </span>
            </div>
            <div>
              <span className="text-[#858585] block text-[11px]">Runs (Dismissals)</span>
              <span className="text-[#F2F2F2] font-semibold tabular-nums">
                {spinSummary.runs?.toLocaleString()} r ({spinSummary.dismissals} outs)
              </span>
            </div>
            <div>
              <span className="text-[#858585] block text-[11px]">Dot % &bull; Boundary %</span>
              <span className="text-[#F2F2F2] font-semibold tabular-nums">
                {spinSummary.dot_ball_percentage ?? '—'}% &bull; {spinSummary.boundary_percentage ?? '—'}%
              </span>
            </div>
          </div>
        </div>

        {/* Card 3: Classification Coverage Disclosure */}
        <div className="bg-[#101010] p-4 rounded-xl border border-[#2D2D2D] relative overflow-hidden space-y-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-[#222222] pb-2.5">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-[#5A9E60]" />
                <span className="text-xs font-bold text-[#F2F2F2] uppercase tracking-wider">
                  Data Classification Integrity
                </span>
              </div>
              <span
                className={`text-[11px] font-bold px-2 py-0.5 rounded border ${
                  totalBalls === 0
                    ? 'text-[#858585] bg-[#1A1A1A] border-[#2D2D2D]'
                    : isCompleteCoverage
                    ? 'text-[#5A9E60] bg-[#152718] border-[#2A4D30]'
                    : 'text-[#E5A84B] bg-[#271E10] border-[#5E441D]'
                }`}
              >
                {totalBalls === 0
                  ? 'N/A'
                  : coveragePct !== null && coveragePct !== undefined
                  ? `${coveragePct}% Verified`
                  : 'N/A'}
              </span>
            </div>
            <div className="mt-2.5 space-y-1.5 text-xs text-[#858585]">
              <div className="flex items-center justify-between">
                <span>Classified Balls:</span>
                <span className="text-[#F2F2F2] font-semibold tabular-nums">
                  {summary?.classified_balls_faced?.toLocaleString() ?? 0} / {summary?.total_balls_faced?.toLocaleString() ?? 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Classified Outs:</span>
                <span className="text-[#F2F2F2] font-semibold tabular-nums">
                  {((summary?.pace_dismissals ?? 0) + (summary?.spin_dismissals ?? 0)).toLocaleString()} / {(summary?.bowler_credited_dismissals ?? 0).toLocaleString()}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Auditable Registry:</span>
                <span className="text-[#D4AF57] font-semibold">577 Bowlers</span>
              </div>
            </div>
          </div>
          <div className="text-[11px] text-[#858585] pt-2 border-t border-[#222222]">
            {totalBalls === 0 ? (
              <span className="text-[#858585] flex items-center gap-1 font-medium">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                No batting observations recorded for this selection.
              </span>
            ) : isCompleteCoverage ? (
              <span className="text-[#5A9E60] flex items-center gap-1 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" />
                100% verified classification across all deliveries.
              </span>
            ) : (
              <span className="text-[#E5A84B] flex items-center gap-1 font-medium">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                {summary?.unclassified_balls_faced} unclassified balls &amp; {summary?.unclassified_dismissals ?? 0} outs excluded.
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Interactive Line Chart & Toolbar */}
      <div className="space-y-3">
        {/* Above-Graph Toolbar: Title, View Selector, Legend, and Segmented Control */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 bg-[#121212] p-3 rounded-xl border border-[#222222]">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-[#F2F2F2]">
                  {chartMetricView === 'dismissals'
                    ? 'Dismissals by Bowling Type'
                    : 'Strike Rate Trajectory by Season'}
                </span>
                <span className="text-[11px] text-[#858585]">
                  {chartMetricView === 'dismissals'
                    ? '(Bowler-credited wickets)'
                    : '(Runs ÷ Balls × 100)'}
                </span>
              </div>
              <span className="text-[11px] text-[#666666] block mt-0.5">
                Hover nodes to inspect underlying metrics
              </span>
            </div>

            {/* Selectable Chart View Control */}
            <div
              role="tablist"
              aria-label="Bowling trends chart view selector"
              className="inline-flex items-center p-1 bg-[#0A0A0A] rounded-lg border border-[#2D2D2D] text-xs self-start sm:self-auto"
            >
              <button
                type="button"
                role="tab"
                id="chart-view-strike-rate"
                aria-selected={chartMetricView === 'strike_rate'}
                onClick={() => setChartMetricView('strike_rate')}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                  chartMetricView === 'strike_rate'
                    ? 'bg-[#1F1B12] text-[#D4AF57] border border-[#D4AF57]/40 shadow-xs'
                    : 'text-[#858585] hover:text-[#F2F2F2]'
                }`}
              >
                Strike Rate Trends
              </button>
              <button
                type="button"
                role="tab"
                id="chart-view-dismissals"
                aria-selected={chartMetricView === 'dismissals'}
                onClick={() => setChartMetricView('dismissals')}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                  chartMetricView === 'dismissals'
                    ? 'bg-[#1F1B12] text-[#D4AF57] border border-[#D4AF57]/40 shadow-xs'
                    : 'text-[#858585] hover:text-[#F2F2F2]'
                }`}
              >
                Dismissals by Bowling Type
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Dynamic Chart Legend showing only active series */}
            <div className="flex items-center gap-2 text-xs" aria-label="Active series legend">
              {showPace && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#1F1B12] border border-[#D4AF57]/30 text-[#D4AF57] font-semibold text-[11px]">
                  <span className="w-2 h-2 rounded-full bg-[#D4AF57] shrink-0" />
                  <span>{chartMetricView === 'dismissals' ? 'Pace Dismissals' : 'Pace SR'}</span>
                </div>
              )}
              {showSpin && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#101A24] border border-[#6BA8E5]/30 text-[#6BA8E5] font-semibold text-[11px]">
                  <span className="w-2 h-2 rounded-full bg-[#6BA8E5] shrink-0" />
                  <span>{chartMetricView === 'dismissals' ? 'Spin Dismissals' : 'Spin SR'}</span>
                </div>
              )}
            </div>

            {/* Segmented Control above the graph */}
            <div
              role="radiogroup"
              aria-label="Graph series selector"
              onKeyDown={handleKeyDown}
              className="inline-flex items-center p-1 bg-[#0A0A0A] rounded-lg border border-[#2D2D2D] text-xs self-start sm:self-auto"
            >
              {bowlingOptions.map((opt) => {
                const isSelected = selectedBowlingType === opt.id;
                return (
                  <button
                    key={opt.id}
                    id={`bowling-selector-graph-${opt.id}`}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    tabIndex={isSelected ? 0 : -1}
                    onClick={() => setSelectedBowlingType(opt.id)}
                    className={`px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-[#D4AF57] text-[#080808] font-bold shadow-xs'
                        : 'text-[#858585] hover:text-[#F2F2F2]'
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Graph Canvas */}
        <div className="w-full h-[230px] sm:h-[360px] bg-[#101010] p-2 sm:p-3 rounded-xl border border-[#2D2D2D]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={
                isMobile
                  ? { top: 12, right: 8, left: -16, bottom: 20 }
                  : { top: 20, right: 20, left: -10, bottom: 25 }
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
                interval={
                  isMobile
                    ? (chartData.length > 12 ? 2 : (chartData.length > 6 ? 1 : 0))
                    : 0
                }
                angle={chartData.length > (isMobile ? 6 : 10) ? -35 : 0}
                textAnchor={chartData.length > (isMobile ? 6 : 10) ? 'end' : 'middle'}
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
                allowDecimals={chartMetricView !== 'dismissals'}
                domain={
                  chartMetricView === 'dismissals'
                    ? [0, 'dataMax + 1']
                    : ['dataMin - 15', 'dataMax + 15']
                }
                width={isMobile ? 32 : 40}
              />
              <Tooltip
                content={
                  <CustomBowlingTooltip
                    selectedBowlingType={selectedBowlingType}
                    chartMetricView={chartMetricView}
                  />
                }
                wrapperStyle={{ outline: 'none', zIndex: 50, pointerEvents: 'none' }}
              />

              {/* Career Reference Lines (for Strike Rate view) */}
              {chartMetricView === 'strike_rate' && (
                <>
                  {paceSummary.strike_rate && showPace && (
                    <ReferenceLine
                      y={paceSummary.strike_rate}
                      stroke="#D4AF57"
                      strokeDasharray="3 3"
                      strokeOpacity={0.4}
                    />
                  )}
                  {spinSummary.strike_rate && showSpin && (
                    <ReferenceLine
                      y={spinSummary.strike_rate}
                      stroke="#6BA8E5"
                      strokeDasharray="3 3"
                      strokeOpacity={0.4}
                    />
                  )}
                </>
              )}

              {/* Pace Series Line */}
              {showPace && (
                <Line
                  type="monotone"
                  dataKey={chartMetricView === 'dismissals' ? 'pace_dismissals' : 'pace_sr'}
                  name={chartMetricView === 'dismissals' ? 'Pace Dismissals' : 'Pace Bowling SR'}
                  stroke="#D4AF57"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: '#D4AF57', stroke: '#080808', strokeWidth: 1.5 }}
                  activeDot={{ r: 6, fill: '#E1C878', stroke: '#F2F2F2', strokeWidth: 2 }}
                  connectNulls={false}
                />
              )}

              {/* Spin Series Line */}
              {showSpin && (
                <Line
                  type="monotone"
                  dataKey={chartMetricView === 'dismissals' ? 'spin_dismissals' : 'spin_sr'}
                  name={chartMetricView === 'dismissals' ? 'Spin Dismissals' : 'Spin Bowling SR'}
                  stroke="#6BA8E5"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: '#6BA8E5', stroke: '#080808', strokeWidth: 1.5 }}
                  activeDot={{ r: 6, fill: '#94C3F3', stroke: '#F2F2F2', strokeWidth: 2 }}
                  connectNulls={false}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Comprehensive Season-by-Season Analytical Table */}
      <div className="bg-[#101010] rounded-xl border border-[#2D2D2D] overflow-hidden space-y-0">
        <div className="p-3.5 sm:p-4 border-b border-[#2D2D2D] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h4 className="font-heading text-sm font-bold text-[#F2F2F2]">
              Seasonal Pace vs Spin Metrics Archive
            </h4>
            <p className="text-xs text-[#858585] mt-0.5">
              Click headers to sort. Strike rates and batting averages are aggregated directly from
              underlying runs, balls, and dismissals.
            </p>
          </div>
          <div className="text-xs text-[#858585]">
            {sortedSeasons.length} seasons recorded
          </div>
        </div>

        <div className="overflow-x-auto max-w-full">
          <table className="w-full text-left border-collapse font-sans text-xs">
            <thead>
              <tr className="border-b border-[#2D2D2D] bg-[#141414] text-[#858585] font-semibold uppercase tracking-wider">
                <th
                  className="py-3 px-3.5 cursor-pointer hover:text-[#F2F2F2]"
                  onClick={() => handleTableSort('season')}
                >
                  <div className="flex items-center gap-1">
                    <span>Season</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-2.5 text-center">Scope</th>
                <th
                  className="py-3 px-2.5 text-right cursor-pointer hover:text-[#F2F2F2]"
                  onClick={() => handleTableSort('matches')}
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>M</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>

                {/* Pace Columns Header */}
                <th
                  className="py-3 px-3 text-right cursor-pointer hover:text-[#D4AF57] bg-[#1F1B12]/40 border-l border-[#2D2D2D]"
                  onClick={() => handleTableSort('pace_runs')}
                >
                  <div className="flex items-center justify-end gap-1 text-[#D4AF57]">
                    <span>Pace Runs/Balls</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  className="py-3 px-2.5 text-right cursor-pointer hover:text-[#D4AF57] bg-[#1F1B12]/40"
                  onClick={() => handleTableSort('pace_dismissals')}
                >
                  <div className="flex items-center justify-end gap-1 text-[#D4AF57]">
                    <span>Pace Outs</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  className="py-3 px-3 text-right cursor-pointer hover:text-[#D4AF57] bg-[#1F1B12]/40"
                  onClick={() => handleTableSort('pace_strike_rate')}
                >
                  <div className="flex items-center justify-end gap-1 text-[#D4AF57]">
                    <span>Pace SR</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-2.5 text-right bg-[#1F1B12]/40 text-[#D4AF57]">
                  Pace Avg
                </th>
                <th className="py-3 px-2.5 text-right bg-[#1F1B12]/40 text-[#D4AF57]">
                  Dot %
                </th>
                <th className="py-3 px-2.5 text-right bg-[#1F1B12]/40 text-[#D4AF57]">
                  Bnd %
                </th>

                {/* Spin Columns Header */}
                <th
                  className="py-3 px-3 text-right cursor-pointer hover:text-[#6BA8E5] bg-[#101A24]/40 border-l border-[#2D2D2D]"
                  onClick={() => handleTableSort('spin_runs')}
                >
                  <div className="flex items-center justify-end gap-1 text-[#6BA8E5]">
                    <span>Spin Runs/Balls</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  className="py-3 px-2.5 text-right cursor-pointer hover:text-[#6BA8E5] bg-[#101A24]/40"
                  onClick={() => handleTableSort('spin_dismissals')}
                >
                  <div className="flex items-center justify-end gap-1 text-[#6BA8E5]">
                    <span>Spin Outs</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  className="py-3 px-3 text-right cursor-pointer hover:text-[#6BA8E5] bg-[#101A24]/40"
                  onClick={() => handleTableSort('spin_strike_rate')}
                >
                  <div className="flex items-center justify-end gap-1 text-[#6BA8E5]">
                    <span>Spin SR</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-2.5 text-right bg-[#101A24]/40 text-[#6BA8E5]">
                  Spin Avg
                </th>
                <th className="py-3 px-2.5 text-right bg-[#101A24]/40 text-[#6BA8E5]">
                  Dot %
                </th>
                <th className="py-3 px-2.5 text-right bg-[#101A24]/40 text-[#6BA8E5]">
                  Bnd %
                </th>

                <th className="py-3 px-3 text-center border-l border-[#2D2D2D]">
                  Coverage
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-[#222222] text-[#F2F2F2]">
              {sortedSeasons.map((row) => {
                const pace = row.pace || {};
                const spin = row.spin || {};
                const hasPace = pace.balls_faced > 0;
                const hasSpin = spin.balls_faced > 0;

                return (
                  <tr
                    key={row.season}
                    className="hover:bg-[#1A1A1A] transition-colors"
                  >
                    <td className="py-2.5 px-3.5 font-semibold text-[#F2F2F2] whitespace-nowrap">
                      {row.season}
                    </td>
                    <td className="py-2.5 px-2.5 text-center whitespace-nowrap">
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#161616] border border-[#2D2D2D] text-[#858585]">
                        {row.competition}
                      </span>
                    </td>
                    <td className="py-2.5 px-2.5 text-right tabular-nums text-[#858585]">
                      {row.matches}
                    </td>

                    {/* Pace Columns */}
                    <td className="py-2.5 px-3 text-right tabular-nums font-medium bg-[#1F1B12]/20 border-l border-[#2D2D2D] whitespace-nowrap">
                      {hasPace ? (
                        <span>
                          <strong className="text-[#F2F2F2]">{pace.runs}</strong>
                          <span className="text-[#858585]"> / {pace.balls_faced}b</span>
                        </span>
                      ) : (
                        <span className="text-[#858585]">—</span>
                      )}
                    </td>
                    <td className="py-2.5 px-2.5 text-right tabular-nums font-semibold text-[#D4AF57] bg-[#1F1B12]/20">
                      {hasPace ? (pace.dismissals ?? row.pace_dismissals ?? 0) : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-right tabular-nums font-bold text-[#D4AF57] bg-[#1F1B12]/20">
                      {pace.strike_rate !== null ? pace.strike_rate : '—'}
                      {pace.insufficient_sample && (
                        <span className="ml-1 text-[10px] text-[#E5A84B] font-normal" title="Sample < 20 balls">
                          *
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-2.5 text-right tabular-nums text-[#B8B8B8] bg-[#1F1B12]/20 whitespace-nowrap">
                      {pace.average !== null ? (
                        pace.average
                      ) : pace.is_not_out ? (
                        <span className="text-[#5A9E60] font-medium" title="Not Out (0 dismissals)">
                          Not Out
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="py-2.5 px-2.5 text-right tabular-nums text-[#858585] bg-[#1F1B12]/20">
                      {pace.dot_ball_percentage !== null ? `${pace.dot_ball_percentage}%` : '—'}
                    </td>
                    <td className="py-2.5 px-2.5 text-right tabular-nums text-[#858585] bg-[#1F1B12]/20">
                      {pace.boundary_percentage !== null ? `${pace.boundary_percentage}%` : '—'}
                    </td>

                    {/* Spin Columns */}
                    <td className="py-2.5 px-3 text-right tabular-nums font-medium bg-[#101A24]/20 border-l border-[#2D2D2D] whitespace-nowrap">
                      {hasSpin ? (
                        <span>
                          <strong className="text-[#F2F2F2]">{spin.runs}</strong>
                          <span className="text-[#858585]"> / {spin.balls_faced}b</span>
                        </span>
                      ) : (
                        <span className="text-[#858585]">—</span>
                      )}
                    </td>
                    <td className="py-2.5 px-2.5 text-right tabular-nums font-semibold text-[#6BA8E5] bg-[#101A24]/20">
                      {hasSpin ? (spin.dismissals ?? row.spin_dismissals ?? 0) : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-right tabular-nums font-bold text-[#6BA8E5] bg-[#101A24]/20">
                      {spin.strike_rate !== null ? spin.strike_rate : '—'}
                      {spin.insufficient_sample && (
                        <span className="ml-1 text-[10px] text-[#E5A84B] font-normal" title="Sample < 20 balls">
                          *
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-2.5 text-right tabular-nums text-[#B8B8B8] bg-[#101A24]/20 whitespace-nowrap">
                      {spin.average !== null ? (
                        spin.average
                      ) : spin.is_not_out ? (
                        <span className="text-[#5A9E60] font-medium" title="Not Out (0 dismissals)">
                          Not Out
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="py-2.5 px-2.5 text-right tabular-nums text-[#858585] bg-[#101A24]/20">
                      {spin.dot_ball_percentage !== null ? `${spin.dot_ball_percentage}%` : '—'}
                    </td>
                    <td className="py-2.5 px-2.5 text-right tabular-nums text-[#858585] bg-[#101A24]/20">
                      {spin.boundary_percentage !== null ? `${spin.boundary_percentage}%` : '—'}
                    </td>

                    {/* Coverage */}
                    <td className="py-2.5 px-3 text-center border-l border-[#2D2D2D] whitespace-nowrap">
                      <span
                        className={`text-[11px] font-semibold tabular-nums px-1.5 py-0.5 rounded ${
                          row.coverage_percentage === null || row.coverage_percentage === undefined
                            ? 'text-[#858585] bg-[#1A1A1A]'
                            : row.coverage_percentage >= 99.9
                            ? 'text-[#5A9E60] bg-[#152718]'
                            : 'text-[#E5A84B] bg-[#271E10]'
                        }`}
                      >
                        {row.coverage_percentage !== null && row.coverage_percentage !== undefined ? `${row.coverage_percentage}%` : '—'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Footnote / Explanations */}
        <div className="p-3 bg-[#121212] border-t border-[#2D2D2D] text-[11px] text-[#858585] space-y-1">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
            <span>
              * <strong>Balls Faced:</strong> Wides strictly excluded; no-balls faced by the batter included.
            </span>
            <span>
              * <strong>Dismissals:</strong> Credited to bowler style (bowled, caught, lbw, stumped, c&amp;b, hit wicket). Run outs excluded.
            </span>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
            <span>
              * <strong>Average:</strong> Runs &divide; Dismissals. Seasons with 0 dismissals and &gt;0 balls return <em>Not Out</em>.
            </span>
            <span>
              * <strong>* Asterisk:</strong> Flags limited sample size (&lt;20 balls faced against bowling type).
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
