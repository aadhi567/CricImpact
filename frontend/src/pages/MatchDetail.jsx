import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  MapPin,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Zap,
  Users,
  Award,
  Scale,
} from 'lucide-react';
import { getMatchDetail } from '../services/api';
import { useCompetition } from '../context/CompetitionContext';
import Breadcrumbs from '../components/Breadcrumbs';

export default function MatchDetail() {
  const { matchId, playerId } = useParams();
  const { competition } = useCompetition();

  const [matchData, setMatchData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getMatchDetail(matchId, playerId, competition);
        if (isMounted) {
          setMatchData(data);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, [matchId, playerId, competition]);

  if (loading) {
    return (
      <div className="w-full py-16 text-center text-[#858585]">
        <div className="inline-block animate-pulse text-sm font-semibold">
          Loading CricImpact player report...
        </div>
      </div>
    );
  }

  if (error || !matchData) {
    return (
      <div className="w-full py-12">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs text-[#D4AF57] hover:text-[#E1C878] font-semibold mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>
        <div className="bg-[#271414] border border-[#4D2626] rounded-xl p-6 text-[#C25454] flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <h2 className="text-base font-bold text-[#F2F2F2]">Match Record Not Found</h2>
            <p className="text-sm mt-1 text-[#858585]">
              {error || `No contribution record found for match #${matchId} and batter ${playerId}.`}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // DNB Handling: Preserve strict null-scoring and explanation
  if (matchData.is_dnb) {
    return (
      <div className="w-full space-y-8">
        <div>
          <Link
            to={`/player/${encodeURIComponent(matchData.player)}/${matchData.season}`}
            className="inline-flex items-center gap-1.5 text-xs text-[#858585] hover:text-[#D4AF57] font-semibold transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to {matchData.player} Season Analysis
          </Link>
        </div>

        <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] shadow-xs">
          <h1 className="font-heading text-2xl font-bold text-[#F2F2F2] mb-2">
            {matchData.player} — Match #{matchData.match_id}
          </h1>
          <div className="text-xs text-[#858585] mb-4">
            {matchData.team} vs {matchData.opponent} • {matchData.date} • {matchData.venue}
          </div>
          <div className="p-4 rounded-lg bg-[#101010] border border-[#2D2D2D] text-xs text-[#858585]">
            <strong className="text-[#F2F2F2]">Did Not Bat (DNB):</strong>{' '}
            {matchData.commentary || 'Did not participate with the bat during this match. DNB is strictly excluded from scoring and denominators.'}
          </div>
        </div>
      </div>
    );
  }

  const perf = matchData.basic_performance || {};
  const ctx = matchData.match_context || {};
  const isFirstInn = ctx.innings === 1;

  // Extract pillar scores & leverage
  const p1Val = matchData.pillars?.pillar1_context?.score;
  const p2Val = matchData.pillars?.pillar2_performance?.raw_score ?? matchData.pillars?.pillar2_performance?.score;
  const p3Val = matchData.pillars?.pillar3_state?.raw_score ?? matchData.pillars?.pillar3_state?.score;

  const levVal =
    matchData.leverage?.value ??
    matchData.p1_leverage ??
    (p1Val !== null && p1Val !== undefined
      ? Math.max(0.65, Math.min(1.35, 1.0 + 0.35 * ((Number(p1Val) - 50.0) / 50.0))).toFixed(2)
      : '1.00');

  const adjP2 = matchData.adjusted_p2 ?? (
    p2Val !== null && p2Val !== undefined
      ? Math.max(0.1, Math.min(99.9, 50.0 + (Number(p2Val) - 50.0) * Number(levVal))).toFixed(1)
      : null
  );

  const adjP3 = matchData.adjusted_p3 ?? (
    p3Val !== null && p3Val !== undefined
      ? Math.max(0.1, Math.min(99.9, 50.0 + (Number(p3Val) - 50.0) * Number(levVal))).toFixed(1)
      : null
  );

  const contributionScore = matchData.contribution_score;

  // Opener check
  const isOpener =
    ctx.entry_over === 0 ||
    ctx.entry_over === 0.0 ||
    perf.batting_position === 1 ||
    perf.batting_position === 2;

  // Dynamic Tier Labels
  const getP2Tier = (val) => {
    if (val === null || val === undefined) return 'Unrated';
    const num = Number(val);
    if (num >= 80) return 'Elite Execution';
    if (num >= 65) return 'High Execution';
    if (num >= 50) return 'Above Par';
    if (num >= 35) return 'Moderate Execution';
    return 'Low Execution';
  };

  const getP3Tier = (val) => {
    if (val === null || val === undefined) return 'Unrated';
    const num = Number(val);
    if (num >= 80) return 'Exceptional Impact';
    if (num >= 65) return 'Strong Impact';
    if (num >= 50) return 'Above Par';
    if (num >= 35) return 'Moderate Impact';
    return 'Limited Impact';
  };

  // Safe formatting helpers
  const runs = perf.runs ?? 0;
  const balls = perf.balls ?? 0;
  const strikeRate = perf.strike_rate !== null && perf.strike_rate !== undefined ? Number(perf.strike_rate).toFixed(1) : '0.0';
  const fours = perf.fours ?? 0;
  const sixes = perf.sixes ?? 0;
  const boundaryRuns = perf.boundary_runs ?? (fours * 4 + sixes * 6);
  const boundaryPct = perf.boundary_percentage !== null && perf.boundary_percentage !== undefined ? Number(perf.boundary_percentage).toFixed(1) : (runs > 0 ? ((boundaryRuns / runs) * 100).toFixed(1) : '0.0');
  const dotBalls = perf.dot_balls ?? 0;
  const dotPct = perf.dot_ball_percentage !== null && perf.dot_ball_percentage !== undefined ? Number(perf.dot_ball_percentage).toFixed(1) : (balls > 0 ? ((dotBalls / balls) * 100).toFixed(1) : '0.0');
  const runsPerBall = perf.runs_per_ball !== null && perf.runs_per_ball !== undefined ? Number(perf.runs_per_ball).toFixed(2) : (balls > 0 ? (runs / balls).toFixed(2) : '0.00');
  const nonBoundaryRuns = Math.max(0, runs - boundaryRuns);

  // Context & Team details
  const entryOver = ctx.entry_over !== null && ctx.entry_over !== undefined ? ctx.entry_over : '0.0';
  const exitOver = ctx.exit_over !== null && ctx.exit_over !== undefined ? ctx.exit_over : '20.0';
  const oversSpent = ctx.overs_spent !== null && ctx.overs_spent !== undefined ? ctx.overs_spent : (balls / 6).toFixed(1);
  const scoreEntry = ctx.team_score_entry !== null && ctx.team_score_entry !== undefined ? ctx.team_score_entry : 0;
  const scoreExit = ctx.team_score_exit !== null && ctx.team_score_exit !== undefined ? ctx.team_score_exit : runs;
  const wktsDownEntry = ctx.wickets_remaining_entry !== null && ctx.wickets_remaining_entry !== undefined ? (10 - ctx.wickets_remaining_entry) : 0;
  const wktsRemEntry = ctx.wickets_remaining_entry !== null && ctx.wickets_remaining_entry !== undefined ? ctx.wickets_remaining_entry : 10;
  const wktsLost = ctx.wickets_lost_during_stay ?? 0;
  const teamRunsAdded = ctx.team_runs_added !== null && ctx.team_runs_added !== undefined ? ctx.team_runs_added : Math.max(runs, scoreExit - scoreEntry);
  const partRuns = ctx.partnership_runs !== null && ctx.partnership_runs !== undefined ? ctx.partnership_runs : Math.max(runs, teamRunsAdded);
  const partShare = ctx.batter_partnership_share !== null && ctx.batter_partnership_share !== undefined
    ? (ctx.batter_partnership_share <= 1.0 && ctx.batter_partnership_share > 0 ? Math.round(ctx.batter_partnership_share * 100) : Math.round(ctx.batter_partnership_share))
    : (partRuns > 0 ? Math.round((runs / partRuns) * 100) : 100);
  const phaseLabel = ctx.phase || (entryOver < 6 ? 'Powerplay' : entryOver >= 16 ? 'Death Overs' : 'Middle Overs');

  return (
    <div className="w-full space-y-6 sm:space-y-7">
      {/* Top Breadcrumb Navigation */}
      <Breadcrumbs
        items={[
          { to: '/matches', label: 'Matches' },
          { to: `/matches/${matchData.match_id}`, label: `Match #${matchData.match_id}` },
          { label: `${matchData.player} Contribution Report` },
        ]}
        backTo={`/matches/${matchData.match_id}`}
        backLabel="Back to Match Overview"
      />

      {/* Match Context Banner */}
      <div className="bg-[#161616] rounded-xl p-4 sm:p-5 border border-[#2D2D2D] shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3.5">
        <div>
          <div className="text-[11.5px] font-semibold text-[#D4AF57] tracking-wider uppercase mb-1 font-sans">
            CricImpact Match Analysis
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="font-heading text-[22px] sm:text-[26px] lg:text-[28px] font-bold text-[#F2F2F2] tracking-tight">
              {matchData.player}
            </h1>
            <span className="text-[#858585] font-semibold text-[14px]">
              ({matchData.team})
            </span>
            <span className="text-[#2D2D2D]">•</span>
            <span className="text-[14.5px] font-semibold text-[#F2F2F2]">
              vs {matchData.opponent}
            </span>
            <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#1F1C14] text-[#D4AF57] border border-[#A8893D]/40">
              Innings {ctx.innings || 1}
            </span>
            {isOpener && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#101010] text-[#858585] border border-[#2D2D2D]">
                Opener
              </span>
            )}
            {matchData.event_name && matchData.event_name !== 'Indian Premier League' && (
              <span className="px-2 py-0.5 rounded-full text-[10.5px] font-semibold bg-[#1F1C14] text-[#D4AF57] border border-[#D4AF57]/40 uppercase tracking-wide">
                {matchData.event_name}{matchData.stage ? ` • ${matchData.stage}` : ''}
              </span>
            )}
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-2.5 text-[12px] text-[#858585]">
            <span className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" />
              {matchData.date}
            </span>
            <span className="text-[#2D2D2D]">•</span>
            <span className="flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5" />
              {matchData.venue || matchData.city || 'T20 Match Venue'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2.5 self-start md:self-auto">
          <span
            className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full ${
              matchData.team_result === 'Won'
                ? 'bg-[#152718] text-[#5A9E60] border border-[#2A4D30]'
                : 'bg-[#271414] text-[#C25454] border border-[#4D2626]'
            }`}
          >
            {matchData.team_result === 'Won' ? (
              <CheckCircle2 className="w-3.5 h-3.5" />
            ) : (
              <XCircle className="w-3.5 h-3.5" />
            )}
            Team {matchData.team_result}
          </span>
        </div>
      </div>

      {/* SECTION 1: BATTING PERFORMANCE */}
      <div className="bg-[#161616] rounded-xl p-4 sm:p-5 border border-[#2D2D2D] shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-[#2D2D2D] pb-3">
          <div className="flex items-start gap-2.5">
            <div className="p-2 rounded-lg bg-[#1F1C14] border border-[#A8893D]/30 text-[#D4AF57] mt-0.5">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-heading text-[17px] sm:text-[19px] font-bold text-[#F2F2F2] tracking-tight">
                1. Batting Performance
              </h2>
              <p className="text-[12px] text-[#858585] mt-0.5">
                Individual execution, scoring output, pace, and boundary profile.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-[#1F1C14] text-[#D4AF57] border border-[#A8893D]/30">
              {getP2Tier(p2Val)}
            </span>
          </div>
        </div>

        {/* Prominent P2 Display & Core Metrics */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
          {/* Prominent Score Tile */}
          <div className="lg:col-span-4 bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] flex flex-col justify-between">
            <div>
              <span className="text-[10.5px] font-semibold text-[#858585] tracking-wider uppercase block">
                P2 — Batting Execution Score
              </span>
              <div className="mt-1.5 flex items-baseline gap-1.5">
                <span className="font-mono text-2xl sm:text-3xl font-bold text-[#F2F2F2] tabular-nums">
                  {p2Val !== null && p2Val !== undefined ? Number(p2Val).toFixed(1) : '—'}
                </span>
                <span className="text-sm font-normal text-[#858585]">/ 100</span>
              </div>
            </div>

            <div className="mt-3 pt-2.5 border-t border-[#2D2D2D] flex flex-wrap items-center justify-between gap-2 text-[11.5px]">
              <span className="text-[#858585]">Adjusted P2 (with leverage):</span>
              <span className="font-mono font-bold text-[#D4AF57]">
                {adjP2 !== null && adjP2 !== undefined ? `${Number(adjP2).toFixed(1)} / 100` : '—'}
              </span>
            </div>
          </div>

          {/* Basic Match Stats Grid */}
          <div className="lg:col-span-8 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#858585] block">Runs & Balls</span>
              <span className="text-xl font-bold text-[#F2F2F2] mt-1 block font-mono tabular-nums">
                {runs} <span className="text-xs font-normal text-[#858585]">({balls}b)</span>
              </span>
              <span className="text-[11px] text-[#858585] mt-1 block font-mono">
                {runsPerBall} runs/ball
              </span>
            </div>

            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#858585] block">Strike Rate</span>
              <span className="text-xl font-bold text-[#F2F2F2] mt-1 block font-mono tabular-nums">
                {strikeRate}
              </span>
              <span className="text-[11px] text-[#858585] mt-1 block">
                Scoring tempo
              </span>
            </div>

            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#858585] block">Boundaries</span>
              <span className="text-xl font-bold text-[#F2F2F2] mt-1 block font-mono tabular-nums">
                {boundaryRuns} <span className="text-xs font-normal text-[#858585]">({fours}x4, {sixes}x6)</span>
              </span>
              <span className="text-[11px] text-[#858585] mt-1 block font-mono">
                {boundaryPct}% boundary share
              </span>
            </div>

            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#858585] block">Dots & Rotation</span>
              <span className="text-xl font-bold text-[#F2F2F2] mt-1 block font-mono tabular-nums">
                {dotBalls} <span className="text-xs font-normal text-[#858585]">({dotPct}%)</span>
              </span>
              <span className="text-[11px] text-[#858585] mt-1 block font-mono">
                {nonBoundaryRuns} running runs
              </span>
            </div>
          </div>
        </div>

        {/* Concise Batting Execution Explanation (Concise Bullet Points) */}
        <div className="bg-[#101010] p-4 sm:p-5 rounded-lg border border-[#2D2D2D] space-y-2.5">
          <h3 className="text-xs font-semibold text-[#D4AF57] tracking-wider uppercase">
            Batting Execution Analysis
          </h3>
          <ul className="space-y-2 text-xs sm:text-[13px] text-[#F2F2F2] list-disc list-inside leading-relaxed">
            <li>
              Scored <strong className="text-[#F2F2F2] font-mono">{runs} runs</strong> off <strong className="text-[#F2F2F2] font-mono">{balls} deliveries</strong> at a strike rate of <strong className="text-[#F2F2F2] font-mono">{strikeRate}</strong> ({runsPerBall} runs per ball).
            </li>
            <li>
              Generated <strong className="text-[#F2F2F2] font-mono">{boundaryRuns} runs</strong> through boundary hitting (<span className="font-mono">{fours}</span> fours and <span className="font-mono">{sixes}</span> sixes), accounting for <strong className="text-[#F2F2F2] font-mono">{boundaryPct}%</strong> of total scoring.
            </li>
            <li>
              Faced <strong className="text-[#F2F2F2] font-mono">{dotBalls} dot balls</strong> (<span className="font-mono">{dotPct}%</span> dot-ball rate) while rotating strike for <strong className="text-[#F2F2F2] font-mono">{nonBoundaryRuns} runs</strong> in running between wickets.
            </li>
            <li>
              Batted at position #{perf.batting_position || '—'} in the {phaseLabel}, finishing {perf.dismissal_status ? `${perf.dismissal_status}${perf.dismissal_kind ? ` (${perf.dismissal_kind})` : ''}` : 'unbeaten'}.
            </li>
          </ul>
        </div>
      </div>

      {/* SECTION 2: TEAM CONTRIBUTION */}
      <div className="bg-[#161616] rounded-xl p-4 sm:p-5 border border-[#2D2D2D] shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-[#2D2D2D] pb-3">
          <div className="flex items-start gap-2.5">
            <div className="p-2 rounded-lg bg-[#1F1C14] border border-[#A8893D]/30 text-[#D4AF57] mt-0.5">
              <Users className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-heading text-[17px] sm:text-[19px] font-bold text-[#F2F2F2] tracking-tight">
                2. Team Contribution
              </h2>
              <p className="text-[12px] text-[#858585] mt-0.5">
                Player's assessed contribution to team progress, crease occupation, and match situation.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-[#1F1C14] text-[#D4AF57] border border-[#A8893D]/30">
              {getP3Tier(p3Val)}
            </span>
          </div>
        </div>

        {/* Prominent P3 Display & Team Situation Metrics */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
          {/* Prominent Score Tile */}
          <div className="lg:col-span-4 bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] flex flex-col justify-between">
            <div>
              <span className="text-[10.5px] font-semibold text-[#858585] tracking-wider uppercase block">
                P3 — Team Contribution Score
              </span>
              <div className="mt-1.5 flex items-baseline gap-1.5">
                <span className="font-mono text-2xl sm:text-3xl font-bold text-[#F2F2F2] tabular-nums">
                  {p3Val !== null && p3Val !== undefined ? Number(p3Val).toFixed(1) : '—'}
                </span>
                <span className="text-sm font-normal text-[#858585]">/ 100</span>
              </div>
            </div>

            <div className="mt-3 pt-2.5 border-t border-[#2D2D2D] flex flex-wrap items-center justify-between gap-2 text-[11.5px]">
              <span className="text-[#858585]">Adjusted P3 (with leverage):</span>
              <span className="font-mono font-bold text-[#D4AF57]">
                {adjP3 !== null && adjP3 !== undefined ? `${Number(adjP3).toFixed(1)} / 100` : '—'}
              </span>
            </div>
          </div>

          {/* Match Situation & Progression Tiles */}
          <div className="lg:col-span-8 grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
            <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D]">
              <span className="text-[10.5px] font-semibold text-[#858585] block">State at Entry</span>
              <span className="text-lg font-bold text-[#F2F2F2] mt-0.5 block font-mono tabular-nums">
                {scoreEntry}/{wktsDownEntry}
              </span>
              <span className="text-[10.5px] text-[#858585] mt-0.5 block">
                Over {entryOver} ({wktsRemEntry} left)
              </span>
            </div>

            <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D]">
              <span className="text-[10.5px] font-semibold text-[#858585] block">Crease Occupation</span>
              <span className="text-lg font-bold text-[#F2F2F2] mt-0.5 block font-mono tabular-nums">
                {oversSpent} <span className="text-[11px] font-normal text-[#858585]">ov</span>
              </span>
              <span className="text-[10.5px] text-[#858585] mt-0.5 block font-mono">
                Ov {entryOver} to {exitOver}
              </span>
            </div>

            <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D]">
              <span className="text-[10.5px] font-semibold text-[#858585] block">Team Progression</span>
              <span className="text-lg font-bold text-[#F2F2F2] mt-0.5 block font-mono tabular-nums">
                {scoreEntry} → {scoreExit}
              </span>
              <span className="text-[10.5px] text-[#858585] mt-0.5 block font-mono">
                +{teamRunsAdded} team runs
              </span>
            </div>

            <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D]">
              <span className="text-[10.5px] font-semibold text-[#858585] block">Partnership Share</span>
              <span className="text-lg font-bold text-[#D4AF57] mt-0.5 block font-mono tabular-nums">
                {partShare}%
              </span>
              <span className="text-[10.5px] text-[#858585] mt-0.5 block font-mono">
                {runs} of {partRuns} runs
              </span>
            </div>
          </div>
        </div>

        {/* Concise Team Contribution Explanation (Concise Bullet Points) */}
        <div className="bg-[#101010] p-3.5 sm:p-4 rounded-lg border border-[#2D2D2D] space-y-2">
          <h3 className="text-[11.5px] font-semibold text-[#D4AF57] tracking-wider uppercase">
            Team Contribution & Match Situation Analysis
          </h3>
          <ul className="space-y-1.5 text-xs sm:text-[12.5px] text-[#F2F2F2] list-disc list-inside leading-relaxed">
            <li>
              {isFirstInn
                ? `Entered at over ${entryOver} during the ${phaseLabel} with the team at ${scoreEntry}/${wktsDownEntry} (${wktsRemEntry} wickets in hand), tasked with constructing the first-innings total.`
                : `Entered at over ${entryOver} during the ${phaseLabel} with the team at ${scoreEntry}/${wktsDownEntry} chasing a target of ${ctx.target || 'N/A'}${ctx.required_rr_entry ? ` at an initial Required Run Rate of ${ctx.required_rr_entry} RPO` : ''}.`}
            </li>
            <li>
              Occupied the crease across <strong className="text-[#F2F2F2] font-mono">{oversSpent} overs</strong> (from over {entryOver} to {exitOver}), stabilizing the batting order while team score advanced from <strong className="text-[#F2F2F2] font-mono">{scoreEntry}</strong> to <strong className="text-[#F2F2F2] font-mono">{scoreExit}</strong> (<span className="font-mono">+{teamRunsAdded} runs</span> added during stay).
            </li>
            <li>
              Contributed <strong className="text-[#F2F2F2] font-mono">{partShare}%</strong> of partnership runs during this period (<strong className="text-[#F2F2F2] font-mono">{runs}</strong> of <span className="font-mono">{partRuns} runs</span>), carrying primary scoring responsibility in tandem.
            </li>
            <li>
              {wktsLost === 0
                ? 'Preserved wickets at both ends with zero partner dismissals occurring during the batter’s crease occupation.'
                : `${wktsLost} partner wicket${wktsLost > 1 ? 's' : ''} fell at the opposite end during the stay; the evaluation assesses the player’s direct scoring and advancement without attributing partner dismissals.`}
            </li>
            {!isFirstInn && ctx.required_rr_entry && ctx.required_rr_exit && (
              <li>
                Required run rate shifted from <strong className="text-[#F2F2F2] font-mono">{ctx.required_rr_entry}</strong> to <strong className="text-[#F2F2F2] font-mono">{ctx.required_rr_exit} RPO</strong> over the course of the innings.
              </li>
            )}
          </ul>
        </div>
      </div>

      {/* SECTION 3: OVERALL PERFORMANCE */}
      <div className="bg-[#161616] rounded-xl p-4 sm:p-5 border border-[#2D2D2D] shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-[#2D2D2D] pb-3">
          <div className="flex items-start gap-2.5">
            <div className="p-2 rounded-lg bg-[#1F1C14] border border-[#A8893D]/30 text-[#D4AF57] mt-0.5">
              <Award className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-heading text-[17px] sm:text-[19px] font-bold text-[#F2F2F2] tracking-tight">
                3. Overall Performance
              </h2>
              <p className="text-[12px] text-[#858585] mt-0.5">
                Approved CricImpact score synthesizing Adjusted P2 and Adjusted P3 under context leverage.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-[#101010] text-[#858585] border border-[#2D2D2D]">
              Par Benchmark = 50.0 / 100
            </span>
          </div>
        </div>

        {/* Prominent Approved CricImpact Score */}
        <div className="bg-[#101010] p-4 sm:p-5 rounded-xl border border-[#2D2D2D] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-[10.5px] font-semibold text-[#858585] tracking-wider uppercase block">
              Final Approved CricImpact Score
            </span>
            <div className="mt-1.5 flex items-baseline gap-1.5">
              <span className="font-mono text-[26px] sm:text-[32px] font-bold text-[#D4AF57] tabular-nums leading-none">
                {contributionScore !== null && contributionScore !== undefined
                  ? Number(contributionScore).toFixed(1)
                  : '—'}
              </span>
              <span className="text-sm font-normal text-[#858585]">/ 100</span>
            </div>
            <div className="mt-1.5 text-[11.5px] text-[#858585] flex items-center gap-2">
              <span>Par = 50.0</span>
              <span className="text-[#2D2D2D]">•</span>
              <span className={`font-mono font-semibold ${
                contributionScore >= 50.0 ? 'text-[#5A9E60]' : 'text-[#C25454]'
              }`}>
                {contributionScore !== null && contributionScore !== undefined
                  ? `${contributionScore >= 50.0 ? '+' : ''}${(contributionScore - 50.0).toFixed(1)} vs Par`
                  : ''}
              </span>
            </div>
          </div>

          {matchData.verdict && (
            <div className="sm:max-w-md p-3 rounded-lg bg-[#152718] border border-[#2A4D30] text-xs text-[#F2F2F2]">
              <strong className="text-[#5A9E60] block mb-0.5">Model Analytical Verdict:</strong>
              {matchData.verdict}
            </div>
          )}
        </div>

        {/* 50/50 Architecture Synthesis */}
        <div className="bg-[#101010] p-4 rounded-xl border border-[#2D2D2D] space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 border-b border-[#2D2D2D] pb-2.5">
            <div className="flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-[#D4AF57]" />
              <h3 className="text-[11.5px] font-semibold text-[#F2F2F2] uppercase tracking-wider">
                50/50 Synthesis Architecture
              </h3>
            </div>
            <span className="font-mono text-[11px] text-[#D4AF57] bg-[#161616] px-2 py-0.5 rounded border border-[#2D2D2D]">
              Formula: 0.50 × Adjusted P2 + 0.50 × Adjusted P3
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            {/* Adjusted P2 Component */}
            <div className="bg-[#161616] p-3 rounded-lg border border-[#2D2D2D] space-y-1">
              <span className="text-[10.5px] font-semibold text-[#858585] block">
                Adjusted P2 (Execution)
              </span>
              <div className="flex items-baseline gap-1">
                <span className="font-mono text-xl font-bold text-[#F2F2F2] tabular-nums">
                  {adjP2 !== null && adjP2 !== undefined ? Number(adjP2).toFixed(1) : '—'}
                </span>
                <span className="text-xs text-[#858585]">/ 100</span>
              </div>
              <p className="text-[10.5px] text-[#858585]">
                Raw P2: <span className="font-mono text-[#F2F2F2]">{p2Val !== null ? Number(p2Val).toFixed(1) : '—'}</span> (50% weight)
              </p>
              <div className="pt-1.5 border-t border-[#2D2D2D] text-[10.5px] font-mono text-[#D4AF57]">
                0.50 × {adjP2 !== null ? Number(adjP2).toFixed(1) : '0.0'} = {adjP2 !== null ? (0.5 * Number(adjP2)).toFixed(1) : '0.0'}
              </div>
            </div>

            {/* Adjusted P3 Component */}
            <div className="bg-[#161616] p-3 rounded-lg border border-[#2D2D2D] space-y-1">
              <span className="text-[10.5px] font-semibold text-[#858585] block">
                Adjusted P3 (Team Contribution)
              </span>
              <div className="flex items-baseline gap-1">
                <span className="font-mono text-xl font-bold text-[#F2F2F2] tabular-nums">
                  {adjP3 !== null && adjP3 !== undefined ? Number(adjP3).toFixed(1) : '—'}
                </span>
                <span className="text-xs text-[#858585]">/ 100</span>
              </div>
              <p className="text-[10.5px] text-[#858585]">
                Raw P3: <span className="font-mono text-[#F2F2F2]">{p3Val !== null ? Number(p3Val).toFixed(1) : '—'}</span> (50% weight)
              </p>
              <div className="pt-1.5 border-t border-[#2D2D2D] text-[10.5px] font-mono text-[#D4AF57]">
                0.50 × {adjP3 !== null ? Number(adjP3).toFixed(1) : '0.0'} = {adjP3 !== null ? (0.5 * Number(adjP3)).toFixed(1) : '0.0'}
              </div>
            </div>

            {/* Context Leverage Scaling */}
            <div className="bg-[#161616] p-3 rounded-lg border border-[#2D2D2D] space-y-1">
              <span className="text-[10.5px] font-semibold text-[#858585] block">
                Context Leverage λ(P1)
              </span>
              <div className="flex items-baseline gap-1">
                <span className="font-mono text-xl font-bold text-[#D4AF57] tabular-nums">
                  {Number(levVal).toFixed(2)}×
                </span>
              </div>
              <p className="text-[10.5px] text-[#858585]">
                Context P1: <span className="font-mono text-[#F2F2F2]">{p1Val !== null ? Number(p1Val).toFixed(1) : '—'}</span> / 100
              </p>
              <div className="pt-1.5 border-t border-[#2D2D2D] text-[10.5px] text-[#858585]">
                Scales deviations from par (50.0) based on situation pressure
              </div>
            </div>
          </div>

          {/* Concise Overall Explanation Bullets */}
          <div className="pt-2.5 border-t border-[#2D2D2D]">
            <ul className="space-y-1.5 text-xs sm:text-[12.5px] text-[#F2F2F2] list-disc list-inside leading-relaxed">
              <li>
                The final rating combines individual execution (<strong className="text-[#F2F2F2] font-mono">Adjusted P2: {adjP2 !== null ? Number(adjP2).toFixed(1) : '—'} / 100</strong>) and assessed team-state impact (<strong className="text-[#F2F2F2] font-mono">Adjusted P3: {adjP3 !== null ? Number(adjP3).toFixed(1) : '—'} / 100</strong>) using the existing 50/50 weighting.
              </li>
              <li>
                Match context P1 (<strong className="text-[#F2F2F2] font-mono">{p1Val !== null ? Number(p1Val).toFixed(1) : '—'} / 100</strong>) establishes a leverage multiplier of <strong className="text-[#D4AF57] font-mono">{Number(levVal).toFixed(2)}×</strong>, calibrating raw pillar deviations to reflect match difficulty and high-pressure game situations.
              </li>
              <li>
                Synthesis calculation: <span className="font-mono text-[#D4AF57]">0.50 × {adjP2 !== null ? Number(adjP2).toFixed(1) : '0.0'} + 0.50 × {adjP3 !== null ? Number(adjP3).toFixed(1) : '0.0'} = {contributionScore !== null ? Number(contributionScore).toFixed(1) : '—'} / 100</span>, providing a balanced and contextually certified evaluation of the player's performance.
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
