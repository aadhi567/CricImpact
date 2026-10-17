import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Award,
  TrendingUp,
  AlertTriangle,
  Info,
  Zap,
} from 'lucide-react';
import ContributionGauge from '../components/ContributionGauge';
import ContributionBreakdown from '../components/ContributionBreakdown';
import MatchContributionTable from '../components/MatchContributionTable';
import MatchScoreTimeline from '../components/Charts/MatchScoreTimeline';
import Breadcrumbs from '../components/Breadcrumbs';
import { getPlayerSeason, getPlayerMatches, getSeasons } from '../services/api';
import { useCompetition, resolveDefaultSeason } from '../context/CompetitionContext';

export default function PlayerAnalysis() {
  const { playerId, season: routeSeason } = useParams();
  const { competition, activeMeta, selectedSeason: globalSeason, tournamentType } = useCompetition();

  const [playerData, setPlayerData] = useState(null);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [resolvedSeason, setResolvedSeason] = useState(routeSeason || globalSeason || '');

  useEffect(() => {
    let isMounted = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        let targetSeason = routeSeason;
        if (!targetSeason) {
          if (globalSeason) {
            targetSeason = globalSeason;
          } else {
            const seasonsData = await getSeasons(competition, tournamentType);
            targetSeason = resolveDefaultSeason(seasonsData.seasons || [], seasonsData.default_season);
          }
        }
        if (isMounted) {
          setResolvedSeason(targetSeason);
        }

        const [profile, matchRes] = await Promise.all([
          getPlayerSeason(playerId, targetSeason, competition, tournamentType),
          getPlayerMatches(playerId, targetSeason, competition, tournamentType),
        ]);

        if (isMounted) {
          setPlayerData(profile);
          setMatches(matchRes.matches || []);
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
  }, [playerId, routeSeason, competition, tournamentType, globalSeason]);

  if (loading) {
    return (
      <div className="w-full px-4 sm:px-6 lg:px-8 py-16 text-center text-[#858585]">
        <div className="inline-block animate-pulse text-sm font-semibold">
          Loading {playerId} season contribution report...
        </div>
      </div>
    );
  }

  if (error || !playerData) {
    return (
      <div className="w-full px-4 sm:px-6 lg:px-8 py-12">
        <Breadcrumbs
          items={[
            { to: '/players', label: 'Players' },
            { label: playerId },
          ]}
          backTo="/players"
          backLabel="Back to Players"
          className="mb-4"
        />
        <div className="bg-[#271414] border border-[#4D2626] rounded-xl p-6 text-[#C25454] flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <h2 className="text-base font-bold text-[#F2F2F2]">Player Season Record Not Found</h2>
            <p className="text-sm mt-1 text-[#858585]">
              {error || `No record found for ${playerId} in season ${resolvedSeason || routeSeason}.`}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const isDnbSeason = playerData.batting_innings === 0;
  const score = playerData.average_contribution_score;
  const p2Score = score !== null ? score : null;
  const p3Score = score !== null ? score : null;

  return (
    <div className="w-full space-y-8 font-sans text-[#F2F2F2]">
      {/* 0. Breadcrumb Navigation */}
      <Breadcrumbs
        items={[
          { to: '/players', label: 'Players' },
          { label: playerData.player },
          { label: `${playerData.season} Season Report` },
        ]}
        backTo="/players"
        backLabel="Back to Players"
      />

      {/* Header Banner */}
      <div className="bg-[#161616] rounded-xl p-4 sm:p-6 md:p-8 border border-[#2D2D2D] shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6 min-w-0">
        <div>
          <div className="flex flex-wrap items-center gap-2 sm:gap-2.5">
            <h1 className="font-heading text-[24px] sm:text-[32px] lg:text-[36px] font-bold text-[#F2F2F2] tracking-wide leading-tight break-words">
              {playerData.player}
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#1F1C14] text-[#D4AF57] border border-[#A8893D]/40">
              {playerData.season} Season
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#101010] text-[#858585] border border-[#2D2D2D]">
              {activeMeta?.short_name || 'T20'}
            </span>
          </div>

          <div className="mt-2.5 flex flex-wrap items-center gap-3 text-xs sm:text-[13px] text-[#858585] font-sans">
            <span className="text-[#F2F2F2] font-semibold">{playerData.team}</span>
            <span>•</span>
            <span className="text-[#F2F2F2] font-semibold">{playerData.actual_runs} Runs</span>
            <span>•</span>
            <span>{playerData.balls_faced} Balls</span>
            <span>•</span>
            <span>SR {playerData.strike_rate !== null ? playerData.strike_rate : '—'}</span>
            {playerData.not_outs > 0 && (
              <>
                <span>•</span>
                <span className="text-[#D4AF57]">{playerData.not_outs} Not Outs</span>
              </>
            )}
          </div>
        </div>

        {/* Participation Badges & Career Action */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 self-start md:self-auto">
          <Link
            to={`/career?player=${encodeURIComponent(playerData.player)}`}
            className="inline-flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl bg-[#1F1C14] hover:bg-[#2A2415] text-[#D4AF57] border border-[#A8893D]/40 hover:border-[#D4AF57] text-xs font-semibold transition-colors duration-150"
            title="Explore multi-season batting performance and CricImpact career metrics"
          >
            <TrendingUp className="w-4 h-4" />
            <span>Career Graph</span>
          </Link>

          <div className="flex items-center gap-4 bg-[#101010] p-3.5 sm:p-4 rounded-xl border border-[#2D2D2D] font-sans">
            <div className="text-center px-2">
              <div className="text-[11px] text-[#858585] font-semibold tracking-wide">Matches</div>
              <div className="text-xl font-bold text-[#F2F2F2] mt-0.5 tabular-nums">{playerData.matches_played}</div>
            </div>
            <div className="w-px h-8 bg-[#2D2D2D]" />
            <div className="text-center px-2">
              <div className="text-[11px] text-[#858585] font-semibold tracking-wide">Innings</div>
              <div className="text-xl font-bold text-[#5A9E60] mt-0.5 tabular-nums">{playerData.batting_innings}</div>
            </div>
            <div className="w-px h-8 bg-[#2D2D2D]" />
            <div className="text-center px-2">
              <div className="text-[11px] text-[#858585] font-semibold tracking-wide">DNB</div>
              <div className="text-xl font-bold text-[#858585] mt-0.5 tabular-nums">{playerData.did_not_bat_matches}</div>
            </div>
          </div>
        </div>
      </div>

      {isDnbSeason && (
        <div className="p-4 rounded-lg bg-[#101010] border border-[#2D2D2D] text-[#858585] text-xs sm:text-[13px] flex items-center gap-2">
          <Info className="w-4 h-4 shrink-0 text-[#D4AF57]" />
          <span>
            <strong className="text-[#F2F2F2] font-semibold">Specialist appearance (pure DNB):</strong> This player was in the playing XI for {playerData.matches_played} matches but did not bat in any innings. In accordance with the validated DNB rule, contribution score is N/A (never treated as zero).
          </span>
        </div>
      )}

      {/* SECTION 1: BATTING PERFORMANCE (P2) */}
      <section aria-labelledby="section-p2" className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#2D2D2D] pb-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-[#1F1C14] border border-[#A8893D]/30 text-[#D4AF57] mt-0.5">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <h2 id="section-p2" className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
                1. Batting Performance (P2)
              </h2>
              <p className="text-[13px] text-[#858585] mt-0.5 font-normal">
                Individual execution, runs output, scoring tempo, and boundary generation.
              </p>
            </div>
          </div>

          <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-[#1F1C14] text-[#D4AF57] border border-[#A8893D]/30 font-sans">
            {p2Score !== null ? (p2Score >= 65 ? 'High Execution' : p2Score >= 50 ? 'Above Par' : 'Moderate Execution') : 'N/A'}
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
          {/* Prominent P2 Execution Score */}
          <div className="lg:col-span-4 bg-[#101010] p-5 rounded-xl border border-[#2D2D2D] flex flex-col justify-between font-sans">
            <div>
              <span className="text-[11px] font-semibold text-[#858585] tracking-wider uppercase block">
                Batting Execution Score (P2)
              </span>
              <div className="mt-2 flex items-baseline gap-1.5">
                <span className="text-4xl sm:text-5xl font-bold text-[#F2F2F2] tabular-nums font-sans">
                  {p2Score !== null ? Number(p2Score).toFixed(1) : '—'}
                </span>
                <span className="text-lg font-normal text-[#858585]">/ 100</span>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-[#2D2D2D] text-xs text-[#858585]">
              Par benchmark = 50.0 • 50% weight in final rating
            </div>
          </div>

          {/* Core Batting Execution Metrics */}
          <div className="lg:col-span-8 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-sans">
            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#858585] block font-sans">Total Runs</span>
              <span className="text-xl font-bold text-[#F2F2F2] mt-1 block tabular-nums">
                {playerData.actual_runs}
              </span>
              <span className="text-[11px] text-[#858585] mt-1 block">
                across {playerData.batting_innings} innings
              </span>
            </div>

            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#858585] block font-sans">Balls Faced</span>
              <span className="text-xl font-bold text-[#F2F2F2] mt-1 block tabular-nums">
                {playerData.balls_faced}
              </span>
              <span className="text-[11px] text-[#858585] mt-1 block">
                deliveries met
              </span>
            </div>

            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#858585] block font-sans">Strike Rate</span>
              <span className="text-xl font-bold text-[#D4AF57] mt-1 block tabular-nums">
                {playerData.strike_rate !== null ? playerData.strike_rate : '—'}
              </span>
              <span className="text-[11px] text-[#858585] mt-1 block">
                runs per 100 balls
              </span>
            </div>

            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#858585] block font-sans">Innings Average</span>
              <span className="text-xl font-bold text-[#F2F2F2] mt-1 block tabular-nums">
                {playerData.batting_innings > 0
                  ? (playerData.actual_runs / playerData.batting_innings).toFixed(1)
                  : '—'}
              </span>
              <span className="text-[11px] text-[#858585] mt-1 block">
                runs / batting opp.
              </span>
            </div>
          </div>
        </div>

        {/* Concise Plain-Language Batting Performance Explanation */}
        <div className="bg-[#101010] p-4 sm:p-5 rounded-lg border border-[#2D2D2D] space-y-2 text-xs sm:text-[13px] text-[#B8B8B8] leading-relaxed font-sans">
          <h3 className="font-semibold text-[#D4AF57] tracking-wider uppercase text-xs">
            Batting Execution Analysis
          </h3>
          <ul className="space-y-1.5 list-disc list-inside">
            <li>
              Scored <strong className="text-[#F2F2F2] font-sans">{playerData.actual_runs} runs</strong> from <strong className="text-[#F2F2F2] font-sans">{playerData.balls_faced} deliveries</strong> across {playerData.batting_innings} actual batting opportunities.
            </li>
            <li>
              Maintained a seasonal scoring tempo of <strong className="text-[#F2F2F2] font-sans">{playerData.strike_rate || '—'} strike rate</strong>, calibrated against par baseline expectations.
            </li>
            <li>
              P2 reflects direct individual execution and run production relative to entry phase conditions.
            </li>
          </ul>
        </div>
      </section>

      {/* SECTION 2: TEAM CONTRIBUTION (P3) */}
      <section aria-labelledby="section-p3" className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#2D2D2D] pb-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-[#1F1C14] border border-[#A8893D]/30 text-[#D4AF57] mt-0.5">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h2 id="section-p3" className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
                2. Team Contribution (P3)
              </h2>
              <p className="text-[13px] text-[#858585] mt-0.5 font-normal">
                Macro match state transformation, positive impact accumulation, and team contribution share.
              </p>
            </div>
          </div>

          <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-[#1F1C14] text-[#D4AF57] border border-[#A8893D]/30 font-sans">
            {p3Score !== null ? (p3Score >= 65 ? 'High Impact' : p3Score >= 50 ? 'Above Par' : 'Moderate Impact') : 'N/A'}
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
          {/* Prominent P3 Impact Score */}
          <div className="lg:col-span-4 bg-[#101010] p-5 rounded-xl border border-[#2D2D2D] flex flex-col justify-between font-sans">
            <div>
              <span className="text-[11px] font-semibold text-[#858585] tracking-wider uppercase block">
                Team Contribution Score (P3)
              </span>
              <div className="mt-2 flex items-baseline gap-1.5">
                <span className="text-4xl sm:text-5xl font-bold text-[#F2F2F2] tabular-nums font-sans">
                  {p3Score !== null ? Number(p3Score).toFixed(1) : '—'}
                </span>
                <span className="text-lg font-normal text-[#858585]">/ 100</span>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-[#2D2D2D] text-xs text-[#858585]">
              Par benchmark = 50.0 • 50% weight in final rating
            </div>
          </div>

          {/* Team Contribution Metrics */}
          <div className="lg:col-span-8 grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-sans">
            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#858585] block font-sans">Team Contribution Share</span>
              <span className="text-xl font-bold text-[#D4AF57] mt-1 block tabular-nums">
                {playerData.season_team_contribution_share !== null
                  ? `${Number(playerData.season_team_contribution_share).toFixed(1)}%`
                  : '—'}
              </span>
              <span className="text-[11px] text-[#858585] mt-1 block">
                share of team positive value
              </span>
            </div>

            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#858585] block font-sans">Positive Contribution</span>
              <span className="text-xl font-bold text-[#5A9E60] mt-1 block tabular-nums">
                {playerData.total_positive_raw_contribution !== null
                  ? Number(playerData.total_positive_raw_contribution).toFixed(2)
                  : '—'}
              </span>
              <span className="text-[11px] text-[#858585] mt-1 block">
                total accumulated value
              </span>
            </div>

            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#858585] block font-sans">Opportunities Evaluated</span>
              <span className="text-xl font-bold text-[#F2F2F2] mt-1 block tabular-nums">
                {playerData.batting_innings}
              </span>
              <span className="text-[11px] text-[#858585] mt-1 block">
                {playerData.did_not_bat_matches || 0} DNBs excluded
              </span>
            </div>
          </div>
        </div>

        {/* Contextual Breakdown Cards */}
        {playerData.context_breakdown && (
          <ContributionBreakdown breakdown={playerData.context_breakdown} />
        )}
      </section>

      {/* SECTION 3: OVERALL PERFORMANCE (FINAL CONTRIBUTION SCORE) */}
      <section aria-labelledby="section-overall" className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#2D2D2D] pb-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-[#1F1C14] border border-[#A8893D]/30 text-[#D4AF57] mt-0.5">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h2 id="section-overall" className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
                3. Overall Performance
              </h2>
              <p className="text-[13px] text-[#858585] mt-0.5 font-normal">
                Official CricImpact Contribution Score synthesizing Batting Performance (P2) and Team Contribution (P3).
              </p>
            </div>
          </div>

          <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-[#101010] text-[#858585] border border-[#2D2D2D] font-sans">
            Par Benchmark = 50.0 / 100
          </span>
        </div>

        {/* Prominent Score Tile & Verdict */}
        <div className="bg-[#101010] p-6 rounded-xl border border-[#2D2D2D] flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div>
            <span className="text-[11px] font-semibold text-[#858585] tracking-wider uppercase block">
              Official CricImpact Average Score
            </span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-sans text-5xl sm:text-6xl font-bold text-[#D4AF57] tabular-nums leading-none">
                {score !== null && score !== undefined ? Number(score).toFixed(1) : '—'}
              </span>
              <span className="text-xl font-normal text-[#858585]">/ 100</span>
            </div>
            <div className="mt-2.5 text-xs text-[#858585] flex items-center gap-2 font-sans">
              <span>Par = 50.0</span>
              <span className="text-[#2D2D2D]">•</span>
              <span className={`font-semibold ${score >= 50.0 ? 'text-[#5A9E60]' : 'text-[#C25454]'}`}>
                {score !== null ? `${score >= 50.0 ? '+' : ''}${(score - 50.0).toFixed(1)} vs Par` : ''}
              </span>
            </div>
          </div>

          <div className="sm:max-w-md p-4 rounded-lg bg-[#152718] border border-[#2A4D30] text-xs sm:text-[13px] text-[#F2F2F2] font-sans">
            <strong className="text-[#5A9E60] block mb-1">Seasonal Performance Summary:</strong>
            {score >= 70
              ? 'Elite contributor across demanding match conditions. Consistently elevated team scoring and absorbed situational pressure.'
              : score >= 55
              ? 'Strong positive contributor above par. Maintained positive team position across the majority of appearances.'
              : score >= 48
              ? 'Solid par-level contributor. Batting output matched baseline situational expectations.'
              : 'Sub-par return relative to situational demands across the season.'}
          </div>
        </div>

        {/* Gauge & Timeline Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ContributionGauge score={score} />
          <MatchScoreTimeline matches={matches} />
        </div>

        {/* Match-by-Match Innings Table */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <h3 className="font-heading text-[18px] sm:text-[20px] font-bold text-[#F2F2F2] tracking-wide">
              Season Match Appearances & Inning Logs
            </h3>
            <span className="text-[12.5px] text-[#858585] font-sans">
              Click any match row to view the full individual match report
            </span>
          </div>
          <MatchContributionTable matches={matches} playerId={playerData.player} />
        </div>

        {/* View B Qualified Sensitivity Comparison (if applicable) */}
        {playerData.view_b_qualified && (
          <div className="bg-[#101010] rounded-xl p-5 border border-[#2D2D2D]">
            <h4 className="font-heading text-sm font-bold text-[#F2F2F2] mb-3">
              Sensitivity Analysis (View B: Qualified Batting Innings)
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-sans">
              <div>
                <span className="text-[11px] font-semibold text-[#858585] block font-sans mb-1">Qualified Innings</span>
                <span className="text-lg font-bold text-[#F2F2F2] tabular-nums">
                  {playerData.view_b_qualified.qualified_batting_innings}
                </span>
              </div>
              <div>
                <span className="text-[11px] font-semibold text-[#858585] block font-sans mb-1">Cameos Excluded</span>
                <span className="text-lg font-bold text-[#D4AF57] tabular-nums">
                  {playerData.view_b_qualified.excluded_small_opportunity_innings}
                </span>
              </div>
              <div>
                <span className="text-[11px] font-semibold text-[#858585] block font-sans mb-1">Qualified Avg Score</span>
                <span className="text-lg font-bold text-[#5A9E60] tabular-nums">
                  {playerData.view_b_qualified.qualified_average_contribution_score !== null
                    ? Number(playerData.view_b_qualified.qualified_average_contribution_score).toFixed(1)
                    : '—'}
                </span>
              </div>
              <div>
                <span className="text-[11px] font-semibold text-[#858585] block font-sans mb-1">Qualified Team Share</span>
                <span className="text-lg font-bold text-[#F2F2F2] tabular-nums">
                  {playerData.view_b_qualified.qualified_team_contribution_share !== null
                    ? `${Number(playerData.view_b_qualified.qualified_team_contribution_share).toFixed(1)}%`
                    : '—'}
                </span>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
