import React from 'react';
import { Link } from 'react-router-dom';
import {
  TrendingUp,
  Trophy,
  Award,
  Zap,
  CircleDot,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
  Info,
} from 'lucide-react';

/**
 * CareerHighsLows component.
 * Displays the historical peak and trough seasons across:
 * 1. Total runs
 * 2. Strike rate
 * 3. Dot-ball percentage
 * 4. Average contribution score
 *
 * Implements strict sample-size transparency, DNB exclusions,
 * tied-season reporting, and direct links to season reports.
 */
export default function CareerHighsLows({
  player,
  competitionView,
  highsLows,
  timeline = [],
  onSelectSeason,
}) {
  // Fallback calculation from timeline if highsLows prop is not directly provided
  const computedHighsLows = React.useMemo(() => {
    if (highsLows && Object.keys(highsLows).length > 0) {
      return highsLows;
    }

    if (!timeline || timeline.length === 0) {
      return null;
    }

    const buildEntry = (s, val, tied) => {
      const bInns = Number(s.batting_innings || 0);
      const balls = Number(s.balls_faced || 0);
      const isLimited = bInns < 5 || balls < 30;
      const matches = Number(s.matches || 0);
      const dnb = Number(s.dnb_matches || (matches - bInns));

      const parts = [`${bInns} innings`, `${balls} balls`];
      if (dnb > 0) parts.push(`${dnb} DNB`);

      return {
        season: String(s.season),
        value: val,
        matches,
        batting_innings: bInns,
        dnb_matches: dnb,
        balls_faced: balls,
        runs: Number(s.runs || 0),
        competition: s.competition || 'IPL',
        is_limited_sample: isLimited,
        sample_note: parts.join(' • '),
        tied_seasons: tied,
      };
    };

    // 1. Runs
    const runsSeasons = timeline.filter((s) => Number(s.batting_innings || 0) > 0 && s.runs !== null && s.runs !== undefined);
    let runsBlock = { metric_id: 'runs', label: 'Total Runs', unit: 'runs', highest: null, lowest: null, insufficient_data: true };
    if (runsSeasons.length > 0) {
      const maxR = Math.max(...runsSeasons.map((s) => Number(s.runs)));
      const minR = Math.min(...runsSeasons.map((s) => Number(s.runs)));
      const maxS = runsSeasons.filter((s) => Number(s.runs) === maxR);
      const minS = runsSeasons.filter((s) => Number(s.runs) === minR);
      runsBlock = {
        metric_id: 'runs',
        label: 'Total Runs',
        unit: 'runs',
        highest: buildEntry(maxS[0], maxR, maxS.slice(1).map((s) => String(s.season))),
        lowest: buildEntry(minS[0], minR, minS.slice(1).map((s) => String(s.season))),
        insufficient_data: false,
        interpretation: 'Total volume of runs scored in a campaign. Low values often reflect small opportunity rather than poor form.',
      };
    }

    // 2. Strike Rate
    const srSeasons = timeline.filter((s) => Number(s.balls_faced || 0) > 0 && s.strike_rate !== null && s.strike_rate !== undefined);
    let srBlock = { metric_id: 'strike_rate', label: 'Strike Rate', unit: 'runs / 100 balls', highest: null, lowest: null, insufficient_data: true };
    if (srSeasons.length > 0) {
      const maxSR = Math.max(...srSeasons.map((s) => Number(s.strike_rate)));
      const minSR = Math.min(...srSeasons.map((s) => Number(s.strike_rate)));
      const maxS = srSeasons.filter((s) => Number(s.strike_rate) === maxSR);
      const minS = srSeasons.filter((s) => Number(s.strike_rate) === minSR);
      srBlock = {
        metric_id: 'strike_rate',
        label: 'Strike Rate',
        unit: 'runs / 100 balls',
        highest: buildEntry(maxS[0], maxSR, maxS.slice(1).map((s) => String(s.season))),
        lowest: buildEntry(minS[0], minSR, minS.slice(1).map((s) => String(s.season))),
        insufficient_data: false,
        interpretation: 'Scoring velocity calibrated against balls faced. Short campaigns (<30 balls) can produce volatile extremes.',
      };
    }

    // 3. Dot-ball %
    const dotSeasons = timeline.filter((s) => Number(s.eligible_balls || s.balls_faced || 0) > 0 && s.dot_ball_percentage !== null && s.dot_ball_percentage !== undefined);
    let dotBlock = { metric_id: 'dot_ball_percentage', label: 'Dot-Ball Percentage', unit: '%', highest: null, lowest: null, insufficient_data: true };
    if (dotSeasons.length > 0) {
      const maxD = Math.max(...dotSeasons.map((s) => Number(s.dot_ball_percentage)));
      const minD = Math.min(...dotSeasons.map((s) => Number(s.dot_ball_percentage)));
      const maxS = dotSeasons.filter((s) => Number(s.dot_ball_percentage) === maxD);
      const minS = dotSeasons.filter((s) => Number(s.dot_ball_percentage) === minD);
      dotBlock = {
        metric_id: 'dot_ball_percentage',
        label: 'Dot-Ball Percentage',
        unit: '%',
        highest: buildEntry(maxS[0], maxD, maxS.slice(1).map((s) => String(s.season))),
        lowest: buildEntry(minS[0], minD, minS.slice(1).map((s) => String(s.season))),
        insufficient_data: false,
        interpretation: 'Percentage of legal balls faced yielding no runs. Lower dot-ball percentage indicates efficient strike rotation and lower pressure buildup.',
      };
    }

    // 4. Average Contribution
    const contribSeasons = timeline.filter((s) => Number(s.eligible_appearances || s.batting_innings || 0) > 0 && s.average_contribution !== null && s.average_contribution !== undefined);
    let contribBlock = { metric_id: 'average_contribution', label: 'Average Contribution Score', unit: '/ 100', highest: null, lowest: null, insufficient_data: true };
    if (contribSeasons.length > 0) {
      const maxC = Math.max(...contribSeasons.map((s) => Number(s.average_contribution)));
      const minC = Math.min(...contribSeasons.map((s) => Number(s.average_contribution)));
      const maxS = contribSeasons.filter((s) => Number(s.average_contribution) === maxC);
      const minS = contribSeasons.filter((s) => Number(s.average_contribution) === minC);
      contribBlock = {
        metric_id: 'average_contribution',
        label: 'Average Contribution Score',
        unit: '/ 100',
        highest: buildEntry(maxS[0], maxC, maxS.slice(1).map((s) => String(s.season))),
        lowest: buildEntry(minS[0], minC, minS.slice(1).map((s) => String(s.season))),
        insufficient_data: false,
        interpretation: 'Synthesized batting execution and team match state impact. Scores above 50.0 add positive situational value.',
      };
    }

    return {
      runs: runsBlock,
      strike_rate: srBlock,
      dot_ball_percentage: dotBlock,
      average_contribution: contribBlock,
    };
  }, [highsLows, timeline]);

  if (!computedHighsLows) {
    return null;
  }

  const metricsConfig = [
    {
      id: 'runs',
      title: 'Total Runs Output',
      icon: Trophy,
      data: computedHighsLows.runs,
      highLabel: 'Highest Runs Season',
      lowLabel: 'Lowest Runs Season',
      formatVal: (v) => `${Number(v).toLocaleString()} runs`,
      highColor: 'text-[#D4AF57]',
      lowColor: 'text-[#B8B8B8]',
      contextTip: 'Represents cumulative seasonal volume. Lowest tallies often reflect minimal batting opportunities rather than poor execution.',
    },
    {
      id: 'strike_rate',
      title: 'Scoring Tempo (Strike Rate)',
      icon: Zap,
      data: computedHighsLows.strike_rate,
      highLabel: 'Peak Strike Rate Season',
      lowLabel: 'Lowest Strike Rate Season',
      formatVal: (v) => `${Number(v).toFixed(1)} SR`,
      highColor: 'text-[#D4AF57]',
      lowColor: 'text-[#C25454]',
      contextTip: 'Calculated strictly as total runs / balls faced × 100. Small-sample seasons (<30 balls) are flagged to prevent misleading extremes.',
    },
    {
      id: 'dot_ball_percentage',
      title: 'Dot-Ball Percentage (Strike Rotation)',
      icon: CircleDot,
      data: computedHighsLows.dot_ball_percentage,
      highLabel: 'Highest Dot % Season',
      lowLabel: 'Lowest Dot % Season (Best Strike Rotation)',
      formatVal: (v) => `${Number(v).toFixed(1)}% dots`,
      highColor: 'text-[#C25454]', // High dot % is generally challenging
      lowColor: 'text-[#5A9E60]', // Low dot % represents great rotation
      contextTip: 'Lower dot-ball percentage indicates superior rotational control and pressure relief. Both extremes are presented neutrally without distortion.',
    },
    {
      id: 'average_contribution',
      title: 'Strategy 4 Average Contribution Score',
      icon: Award,
      data: computedHighsLows.average_contribution,
      highLabel: 'Peak Contribution Season',
      lowLabel: 'Lowest Contribution Season',
      formatVal: (v) => {
        const num = Number(v);
        const diff = (num - 50.0).toFixed(1);
        const sign = num >= 50.0 ? '+' : '';
        return `${num.toFixed(1)} (${sign}${diff} vs Par)`;
      },
      highColor: 'text-[#D4AF57]',
      lowColor: 'text-[#C25454]',
      contextTip: 'Calibrated against baseline Par = 50.0. DNB matches are strictly excluded and never count as zero.',
    },
  ];

  return (
    <section aria-labelledby="career-highs-lows-heading" className="bg-[#161616] rounded-xl p-5 sm:p-7 border border-[#2D2D2D] space-y-6 shadow-xs font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#222222] pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-[#D4AF57] tracking-wider uppercase">
            <TrendingUp className="w-4 h-4" />
            <span>Multi-Season Benchmark Analysis</span>
          </div>
          <h2 id="career-highs-lows-heading" className="font-heading text-xl sm:text-2xl font-bold text-[#F2F2F2] mt-0.5">
            Career Highs &amp; Lows
          </h2>
          <p className="text-xs text-[#858585] mt-1 max-w-2xl leading-relaxed">
            Historical peaks and troughs across key batting indicators. Sample sizes and DNB exclusions are transparently accounted for to prevent small-sample distortion.
          </p>
        </div>

        <div className="flex items-center gap-2 text-[11px] text-[#858585] bg-[#101010] px-3 py-1.5 rounded-lg border border-[#2D2D2D] self-start sm:self-auto shrink-0">
          <Info className="w-3.5 h-3.5 text-[#D4AF57]" />
          <span>Scope: {competitionView === 'combined' ? 'Combined Career' : competitionView.toUpperCase()}</span>
        </div>
      </div>

      {/* Grid of 4 Metric Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {metricsConfig.map((metric) => {
          const { id, title, icon: Icon, data, highLabel, lowLabel, formatVal, highColor, lowColor, contextTip } = metric;

          if (!data || data.insufficient_data) {
            return (
              <div key={id} className="bg-[#101010] p-4 sm:p-5 rounded-xl border border-[#2D2D2D] flex flex-col justify-between space-y-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-lg bg-[#1A1A1A] text-[#858585]">
                    <Icon className="w-4 h-4" />
                  </div>
                  <h3 className="font-semibold text-sm text-[#F2F2F2]">{title}</h3>
                </div>
                <div className="py-6 text-center text-xs text-[#858585]">
                  Insufficient data across evaluated career timeline.
                </div>
              </div>
            );
          }

          const { highest, lowest } = data;

          return (
            <div
              key={id}
              className="bg-[#101010] p-4 sm:p-5 rounded-xl border border-[#2D2D2D] hover:border-[#383838] transition-colors flex flex-col justify-between space-y-4"
            >
              {/* Card Header */}
              <div className="flex items-center justify-between gap-2 border-b border-[#1E1E1E] pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-lg bg-[#1A1A1A] text-[#D4AF57] border border-[#2D2D2D]">
                    <Icon className="w-4 h-4" />
                  </div>
                  <h3 className="font-semibold text-sm sm:text-[15px] text-[#F2F2F2] tracking-wide">
                    {title}
                  </h3>
                </div>
                <span className="text-[11px] text-[#666666] font-mono uppercase">
                  {data.unit}
                </span>
              </div>

              {/* Side-by-Side: Best vs Lowest */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {/* 1. HIGHEST EXTREME */}
                {highest ? (
                  <ExtremeBox
                    type="highest"
                    title={highLabel}
                    extreme={highest}
                    valueText={formatVal(highest.value)}
                    valueColor={highColor}
                    playerName={player}
                    onSelectSeason={onSelectSeason}
                  />
                ) : (
                  <div className="p-3 bg-[#141414] rounded-lg border border-[#222222] text-xs text-[#666666] text-center">
                    No high record
                  </div>
                )}

                {/* 2. LOWEST EXTREME */}
                {lowest ? (
                  <ExtremeBox
                    type="lowest"
                    title={lowLabel}
                    extreme={lowest}
                    valueText={formatVal(lowest.value)}
                    valueColor={lowColor}
                    playerName={player}
                    onSelectSeason={onSelectSeason}
                  />
                ) : (
                  <div className="p-3 bg-[#141414] rounded-lg border border-[#222222] text-xs text-[#666666] text-center">
                    No low record
                  </div>
                )}
              </div>

              {/* Interpretive Footer Note */}
              <div className="text-[11px] text-[#7A7A7A] leading-relaxed pt-1 border-t border-[#1C1C1C]">
                {contextTip}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

/**
 * Subcomponent to render an individual extreme box (highest or lowest).
 */
function ExtremeBox({
  type,
  title,
  extreme,
  valueText,
  valueColor,
  playerName,
  onSelectSeason,
}) {
  const isHighest = type === 'highest';
  const hasTied = extreme.tied_seasons && extreme.tied_seasons.length > 0;
  const isIplSeason = !extreme.competition || extreme.competition.toUpperCase().includes('IPL');

  return (
    <div
      className={`p-3.5 rounded-lg border flex flex-col justify-between space-y-2.5 transition-all ${
        isHighest
          ? 'bg-[#151410] border-[#38301B]/60 hover:border-[#D4AF57]/40'
          : 'bg-[#141414] border-[#262626] hover:border-[#383838]'
      }`}
    >
      <div>
        <div className="flex items-center justify-between gap-1.5 text-[11px]">
          <span className="font-semibold text-[#858585] truncate">
            {title}
          </span>
          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-[#1F1F1F] text-[#B8B8B8] shrink-0 border border-[#2D2D2D]">
            {extreme.competition}
          </span>
        </div>

        {/* Season & Metric Value */}
        <div className="mt-1.5 flex items-baseline justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <span className="font-heading text-lg font-bold text-[#F2F2F2]">
              {extreme.season}
            </span>
            {hasTied && (
              <span
                className="text-[10px] px-1.5 py-0.5 rounded bg-[#222222] text-[#D4AF57] border border-[#333333]"
                title={`Tied with: ${extreme.tied_seasons.join(', ')}`}
              >
                +{extreme.tied_seasons.length} tied
              </span>
            )}
          </div>
          <span className={`text-base font-bold tabular-nums font-sans ${valueColor}`}>
            {valueText}
          </span>
        </div>
      </div>

      {/* Sample Context */}
      <div className="space-y-1.5 pt-1 text-xs">
        <div className="flex items-center justify-between text-[11px] text-[#858585]">
          <span>Opportunity:</span>
          <span className="text-[#B8B8B8] font-medium tabular-nums">
            {extreme.sample_note}
          </span>
        </div>

        {/* Small Sample Warning Pill */}
        {extreme.is_limited_sample && (
          <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-[#271E10] border border-[#523B15] text-[10.5px] text-[#D97706]">
            <AlertTriangle className="w-3 h-3 shrink-0" />
            <span className="truncate">Limited sample size (&lt; 5 inns / 30 balls)</span>
          </div>
        )}
      </div>

      {/* Action Links */}
      <div className="pt-2 border-t border-[#222222] flex items-center justify-between gap-2 text-xs">
        {onSelectSeason && (
          <button
            type="button"
            onClick={() => onSelectSeason(extreme.season)}
            className="text-[11px] text-[#858585] hover:text-[#D4AF57] font-medium transition-colors flex items-center gap-1 cursor-pointer"
            title={`Highlight season ${extreme.season} in charts and table`}
          >
            <span>Highlight</span>
            <ChevronRight className="w-3 h-3" />
          </button>
        )}

        {isIplSeason && playerName ? (
          <Link
            to={`/player/${encodeURIComponent(playerName)}/${encodeURIComponent(extreme.season)}`}
            className="text-[11px] text-[#D4AF57] hover:underline font-semibold flex items-center gap-1 ml-auto"
            title={`Open detailed ${extreme.season} season report`}
          >
            <span>Season Report</span>
            <ExternalLink className="w-3 h-3" />
          </Link>
        ) : (
          <span className="text-[11px] text-[#666666] ml-auto">
            {extreme.season} Record
          </span>
        )}
      </div>
    </div>
  );
}
