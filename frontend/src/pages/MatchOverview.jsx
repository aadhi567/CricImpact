import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  MapPin,
  Trophy,
  Award,
  ExternalLink,
  ArrowUpDown,
  Info,
} from 'lucide-react';
import { getMatchOverview } from '../services/api';
import { useCompetition } from '../context/CompetitionContext';
import Breadcrumbs from '../components/Breadcrumbs';

export default function MatchOverview() {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const { competition } = useCompetition();

  const [matchData, setMatchData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Sorting: 'contribution' | 'runs' | 'strike_rate'
  const [sortField, setSortField] = useState('contribution');
  const [sortDirection, setSortDirection] = useState('desc');

  useEffect(() => {
    let isMounted = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getMatchOverview(matchId, competition);
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
  }, [matchId, competition]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedBatters = useMemo(() => {
    if (!matchData?.batters) return [];

    const qualified = matchData.batters.filter((b) => b.is_qualified);
    const limited = matchData.batters.filter((b) => !b.is_qualified);

    const comparator = (a, b) => {
      let valA;
      let valB;

      if (sortField === 'contribution') {
        valA = a.contribution_score;
        valB = b.contribution_score;
      } else if (sortField === 'runs') {
        valA = a.runs;
        valB = b.runs;
      } else if (sortField === 'strike_rate') {
        valA = a.strike_rate;
        valB = b.strike_rate;
      } else if (sortField === 'balls') {
        valA = a.balls;
        valB = b.balls;
      } else {
        valA = a[sortField];
        valB = b[sortField];
      }

      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      if (valA !== valB) {
        return sortDirection === 'asc' ? valA - valB : valB - valA;
      }
      return (b.runs || 0) - (a.runs || 0);
    };

    qualified.sort(comparator);
    limited.sort(comparator);

    return [...qualified, ...limited];
  }, [matchData, sortField, sortDirection]);

  if (loading) {
    return (
      <div className="w-full px-5 sm:px-7 lg:px-8 py-16 text-center text-[#858585] font-mono">
        <div className="inline-block animate-pulse text-sm font-semibold">
          Loading match contribution breakdown for Match #{matchId}...
        </div>
      </div>
    );
  }

  if (error || !matchData) {
    return (
      <div className="w-full px-5 sm:px-7 lg:px-8 py-12 font-mono">
        <Link
          to="/matches"
          className="inline-flex items-center gap-1.5 text-xs text-[#D4AF57] hover:text-[#E1C878] font-semibold mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Matches
        </Link>
        <div className="bg-[#271414] border border-[#4D2626] rounded-xl p-6 text-[#C25454]">
          <h2 className="text-base font-bold text-[#F2F2F2]">Match Not Found</h2>
          <p className="text-sm mt-1 text-[#858585]">
            {error || `No match record found for Match #${matchId}.`}
          </p>
        </div>
      </div>
    );
  }

  const isT1Winner = matchData.winner === matchData.team1;
  const isT2Winner = matchData.winner === matchData.team2;

  return (
    <div className="w-full space-y-8 font-mono text-[#F2F2F2]">
      {/* Navigation Breadcrumb */}
      <Breadcrumbs
        items={[
          { to: '/matches', label: 'Matches' },
          { label: `Match #${matchData.match_id}: ${matchData.team1} vs ${matchData.team2}` },
        ]}
        backTo="/matches"
        backLabel="Back to Matches"
      />

      {/* 1. MATCH HEADER */}
      <div className="bg-[#161616] rounded-xl p-5 sm:p-6 border border-[#2D2D2D] shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#2D2D2D] pb-3.5 text-[12px] text-[#858585]">
          <div className="flex flex-wrap items-center gap-2.5">
            {matchData.event_name && (
              <span className="px-2.5 py-1 rounded-md font-semibold bg-[#1F1C14] text-[#D4AF57] border border-[#D4AF57]/40 flex items-center gap-1.5 text-[12px]">
                <Trophy className="w-3.5 h-3.5 text-[#D4AF57]" />
                {matchData.event_name}
                {matchData.stage ? ` • ${matchData.stage}` : ''}
              </span>
            )}
            <span className="px-2.5 py-1 rounded-md font-semibold bg-[#101010] text-[#D4AF57] border border-[#3D351E] text-[12px]">
              {matchData.season} Season
            </span>
            <span className="text-[12.5px]">Match #{matchData.match_id}</span>
            <span>•</span>
            <span className="flex items-center gap-1.5 text-[12.5px]">
              <Calendar className="w-3.5 h-3.5 text-[#666666]" />
              {matchData.date}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-[12px] sm:text-[12.5px] text-[#858585]">
            <MapPin className="w-4 h-4 text-[#666666]" />
            <span>{matchData.venue}{matchData.city ? `, ${matchData.city}` : ''}</span>
          </div>
        </div>

        {/* Head-to-Head Scoreboard */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
          {/* Team 1 */}
          <div
            className={`p-5 sm:p-6 rounded-xl border transition-all ${
              isT1Winner
                ? 'bg-[#152718]/30 border-[#2A4D30] text-[#F2F2F2]'
                : 'bg-[#101010] border-[#2D2D2D] text-[#B8B8B8]'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[12px] uppercase tracking-wider text-[#858585] font-semibold block">
                  Team 1 (1st Innings)
                </span>
                <span className="font-heading text-[22px] sm:text-[25px] font-bold text-[#F2F2F2] block mt-1">
                  {matchData.team1}
                </span>
              </div>
              {matchData.team1_score !== null && (
                <div className="text-right">
                  <span className="font-mono text-[28px] sm:text-[34px] font-bold text-[#D4AF57] tabular-nums">
                    {matchData.team1_score}
                  </span>
                  <span className="text-[12px] text-[#858585] block font-mono">runs</span>
                </div>
              )}
            </div>
            {isT1Winner && (
              <span className="inline-block mt-3 text-[11.5px] sm:text-[12px] font-semibold text-[#5A9E60] bg-[#152718] px-2.5 py-0.5 rounded-md border border-[#2A4D30]">
                ✓ Match Winner
              </span>
            )}
          </div>

          {/* Team 2 */}
          <div
            className={`p-5 sm:p-6 rounded-xl border transition-all ${
              isT2Winner
                ? 'bg-[#152718]/30 border-[#2A4D30] text-[#F2F2F2]'
                : 'bg-[#101010] border-[#2D2D2D] text-[#B8B8B8]'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[12px] uppercase tracking-wider text-[#858585] font-semibold block">
                  Team 2 (2nd Innings)
                </span>
                <span className="font-heading text-[22px] sm:text-[25px] font-bold text-[#F2F2F2] block mt-1">
                  {matchData.team2}
                </span>
              </div>
              {matchData.team2_score !== null && (
                <div className="text-right">
                  <span className="font-mono text-[28px] sm:text-[34px] font-bold text-[#D4AF57] tabular-nums">
                    {matchData.team2_score}
                  </span>
                  <span className="text-[12px] text-[#858585] block font-mono">runs</span>
                </div>
              )}
            </div>
            {isT2Winner && (
              <span className="inline-block mt-3 text-[11.5px] sm:text-[12px] font-semibold text-[#5A9E60] bg-[#152718] px-2.5 py-0.5 rounded-md border border-[#2A4D30]">
                ✓ Match Winner
              </span>
            )}
          </div>
        </div>

        {/* Match Result Banner */}
        <div className="bg-[#101010] p-4 rounded-xl border border-[#2D2D2D] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[13.5px]">
          <div className="flex items-center gap-2.5">
            <Trophy className="w-4 h-4 text-[#D4AF57] shrink-0" />
            <span className="font-bold text-[15px] sm:text-[16px] text-[#F2F2F2]">{matchData.result}</span>
          </div>

          <div className="flex items-center gap-4 text-[12.5px] sm:text-[13px] text-[#858585]">
            {matchData.player_of_match && (
              <span>
                Player of the Match:{' '}
                <strong className="text-[#D4AF57] font-semibold">{matchData.player_of_match}</strong>
              </span>
            )}
            {matchData.toss_winner && (
              <span>
                Toss: {matchData.toss_winner} ({matchData.toss_decision})
              </span>
            )}
          </div>
        </div>

        {/* Match Contributor Summary */}
        <div className="bg-[#101010] p-4 sm:p-4.5 rounded-xl border border-[#2D2D2D] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[13px]">
          <div className="flex items-center gap-3 flex-wrap">
            <Award className="w-4 h-4 text-[#D4AF57] shrink-0" />
            <span className="text-[#858585] uppercase tracking-wider text-[12px] font-semibold">
              Best Contributor:
            </span>
            {matchData.top_qualified_contributor ? (
              <div className="flex items-center gap-2.5 flex-wrap">
                <span className="font-bold text-[#F2F2F2] text-[15px]">
                  {matchData.top_qualified_contributor.player}
                </span>
                <span className="px-2.5 py-0.5 rounded-md text-[12px] font-bold bg-[#1C1A14] text-[#D4AF57] border border-[#3D351E] tabular-nums">
                  Score {matchData.top_qualified_contributor.contribution_score}
                </span>
                <span className="text-[#858585] text-[12px] sm:text-[12.5px] tabular-nums">
                  ({matchData.top_qualified_contributor.runs} runs, {matchData.top_qualified_contributor.balls} balls • SR {matchData.top_qualified_contributor.strike_rate})
                </span>
                <span className="text-[11px] uppercase font-semibold text-[#5A9E60] bg-[#152718] px-2 py-0.5 rounded border border-[#2A4D30]">
                  Qualified #1
                </span>
              </div>
            ) : (
              <span className="text-[#858585] italic">
                No qualified match ranking — insufficient batting sample.
              </span>
            )}
          </div>

          {matchData.top_qualified_contributor && (
            <Link
              to={`/match/${matchId}/player/${encodeURIComponent(matchData.top_qualified_contributor.player)}`}
              className="inline-flex items-center gap-1.5 text-[12.5px] sm:text-[13px] font-semibold text-[#D4AF57] hover:text-[#E1C878] transition-colors self-start sm:self-auto"
            >
              <span>Analyze Best Contributor</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>
      </div>

      {/* 2. MATCH CONTRIBUTION RATINGS */}
      <div className="bg-[#161616] rounded-xl border border-[#2D2D2D] shadow-xs overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-[#2D2D2D] bg-[#101010] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <Award className="w-4 h-4 text-[#D4AF57]" />
              <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
                MATCH CONTRIBUTION RATINGS
              </h2>
              <span className="text-[11px] sm:text-[11.5px] font-mono text-[#D4AF57] bg-[#161616] px-2.5 py-0.5 rounded border border-[#3D351E]">
                Par = 50.0
              </span>
            </div>
            <p className="text-[13px] sm:text-[13.5px] font-mono text-[#858585] mt-1">
              Evaluates every batter with an actual batting opportunity. Match rankings use a minimum sample of 10 balls or 20 runs.
            </p>
          </div>

          {/* Sorting Quick-Toggles */}
          <div className="flex items-center gap-1.5 self-start sm:self-auto shrink-0 bg-[#161616] p-1.5 rounded-lg border border-[#2D2D2D] text-[12px]">
            <span className="text-[#858585] px-2 text-[12px]">Sort by:</span>
            <button
              type="button"
              onClick={() => handleSort('contribution')}
              className={`px-3 py-1.5 rounded-md font-semibold transition-colors cursor-pointer text-[12px] sm:text-[12.5px] ${
                sortField === 'contribution'
                  ? 'bg-[#D4AF57] text-[#080808]'
                  : 'text-[#858585] hover:text-[#F2F2F2]'
              }`}
            >
              Contribution {sortField === 'contribution' && (sortDirection === 'desc' ? '↓' : '↑')}
            </button>
            <button
              type="button"
              onClick={() => handleSort('runs')}
              className={`px-3 py-1.5 rounded-md font-semibold transition-colors cursor-pointer text-[12px] sm:text-[12.5px] ${
                sortField === 'runs'
                  ? 'bg-[#D4AF57] text-[#080808]'
                  : 'text-[#858585] hover:text-[#F2F2F2]'
              }`}
            >
              Runs {sortField === 'runs' && (sortDirection === 'desc' ? '↓' : '↑')}
            </button>
            <button
              type="button"
              onClick={() => handleSort('strike_rate')}
              className={`px-3 py-1.5 rounded-md font-semibold transition-colors cursor-pointer text-[12px] sm:text-[12.5px] ${
                sortField === 'strike_rate'
                  ? 'bg-[#D4AF57] text-[#080808]'
                  : 'text-[#858585] hover:text-[#F2F2F2]'
              }`}
            >
              SR {sortField === 'strike_rate' && (sortDirection === 'desc' ? '↓' : '↑')}
            </button>
          </div>
        </div>

        {/* Informational Context & Eligibility Bar */}
        <div className="px-5 py-3 bg-[#101010] border-b border-[#2D2D2D] text-[12px] text-[#858585] flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 flex-wrap">
            <div
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#161616] border border-[#3D351E] text-[#D4AF57] font-semibold cursor-help"
              title="All batting opportunities remain visible. The qualification threshold only prevents extremely small samples from being presented as the primary match ranking."
            >
              <Info className="w-3.5 h-3.5 text-[#D4AF57]" />
              <span>Ranking eligibility: 10+ balls OR 20+ runs</span>
            </div>
            <span className="text-[#666666] hidden sm:inline">•</span>
            <span className="text-[#858585]">
              {sortedBatters.length} batting opportunities evaluated ({matchData.qualified_count || 0} qualified, {matchData.limited_sample_count || 0} limited sample)
            </span>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-3.5 text-[11.5px]">
            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded font-semibold bg-[#1C1A14] text-[#D4AF57] border border-[#3D351E]">
                QUALIFIED
              </span>
              <span className="text-[#858585]">Eligible for match ranking</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded font-medium bg-[#1C1C1C] text-[#858585] border border-[#333333]">
                LIMITED SAMPLE
              </span>
              <span className="text-[#666666]">Excluded from ranking</span>
            </div>
          </div>
        </div>

        {/* Batters Table */}
        <div className="overflow-x-auto w-full">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#2D2D2D] bg-[#161616] text-[#858585] font-semibold text-[12.5px] sm:text-[13px] tracking-wider uppercase">
                <th className="py-3.5 px-3.5 text-center w-12 sm:w-16">RANK</th>
                <th className="py-3.5 px-4">BATTER</th>
                <th className="py-3.5 px-3.5">TEAM</th>
                <th className="py-3.5 px-3 text-center">INNS</th>
                <th
                  onClick={() => handleSort('runs')}
                  className="py-3.5 px-3.5 text-right cursor-pointer hover:text-[#F2F2F2] transition-colors"
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>RUNS</span>
                    <ArrowUpDown className="w-3.5 h-3.5" />
                  </div>
                </th>
                <th className="py-3.5 px-3 text-right">BALLS</th>
                <th
                  onClick={() => handleSort('strike_rate')}
                  className="py-3.5 px-3 text-right cursor-pointer hover:text-[#F2F2F2] transition-colors"
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>SR</span>
                    <ArrowUpDown className="w-3.5 h-3.5" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('contribution')}
                  className="py-3.5 px-4 text-center cursor-pointer hover:text-[#F2F2F2] transition-colors"
                >
                  <div className="flex items-center justify-center gap-1">
                    <span>CONTRIBUTION</span>
                    <ArrowUpDown className="w-3.5 h-3.5" />
                  </div>
                </th>
                <th className="py-3.5 px-3.5 text-center">RESULT</th>
                <th className="py-3.5 px-3.5 text-center">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#222222] text-[#F2F2F2] text-[14px] sm:text-[14.5px]">
              {sortedBatters.map((b, idx) => {
                // Section divider between qualified and limited-sample
                const isFirstLimited = !b.is_qualified && (idx === 0 || sortedBatters[idx - 1].is_qualified);

                let rankBadge = 'text-[#858585]';
                if (b.is_qualified) {
                  if (b.rank === 1) rankBadge = 'bg-[#2E2717] text-[#D4AF57] border border-[#D4AF57]/40 font-bold';
                  else if (b.rank === 2) rankBadge = 'bg-[#222222] text-[#B8B8B8] border border-[#3D3D3D] font-bold';
                  else if (b.rank === 3) rankBadge = 'bg-[#241D17] text-[#A8893D] border border-[#A8893D]/30 font-bold';
                }

                // Score Badge Styling
                let scoreBadge = 'bg-[#101010] text-[#858585] border-[#2D2D2D]';
                if (b.contribution_score !== null && b.contribution_score !== undefined) {
                  if (b.contribution_score >= 65)
                    scoreBadge = 'bg-[#152718] text-[#5A9E60] border-[#2A4D30] font-bold';
                  else if (b.contribution_score >= 52)
                    scoreBadge = 'bg-[#152718] text-[#5A9E60] border-[#2A4D30]/60 font-semibold';
                  else if (b.contribution_score >= 48)
                    scoreBadge = 'bg-[#1F1C14] text-[#D4AF57] border-[#A8893D]/40 font-medium';
                  else
                    scoreBadge = 'bg-[#271414] text-[#C25454] border-[#4D2626] font-semibold';
                }

                return (
                  <React.Fragment key={`${b.player}-${b.innings}`}>
                    {isFirstLimited && (
                      <tr className="bg-[#121212] border-t-2 border-b border-[#2D2D2D]">
                        <td colSpan={10} className="py-3 px-4 text-[12px] font-semibold text-[#858585] uppercase tracking-wider">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-[#858585]"></span>
                              <span>Limited Sample Batting Opportunities (Excluded from match ranking)</span>
                            </div>
                            <span className="text-[11px] lowercase text-[#666666] font-normal">
                              Batters with &lt; 10 balls and &lt; 20 runs
                            </span>
                          </div>
                        </td>
                      </tr>
                    )}
                    <tr
                      onClick={() => navigate(`/match/${matchId}/player/${encodeURIComponent(b.player)}`)}
                      className="cursor-pointer hover:bg-[#1A1A1A] transition-colors"
                    >
                      {/* Rank */}
                      <td className="py-3.5 px-3.5 text-center whitespace-nowrap">
                        {b.is_qualified && b.rank ? (
                          <span
                            className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-[12px] ${rankBadge}`}
                          >
                            {b.rank}
                          </span>
                        ) : (
                          <span className="text-[#666666] font-bold text-[14px]">—</span>
                        )}
                      </td>

                      {/* Batter */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-[14px] sm:text-[14.5px] text-[#F2F2F2] hover:text-[#D4AF57] transition-colors">
                            {b.player}
                          </span>
                          {b.dismissal_status === 'not out' && (
                            <span className="text-[11px] font-normal text-[#D4AF57] font-mono">
                              (NO)
                            </span>
                          )}
                          {!b.is_qualified && (
                            <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-[#1C1C1C] text-[#858585] border border-[#333333]">
                              Limited Sample
                            </span>
                          )}
                        </div>
                        {b.dismissal_kind && (
                          <div className="text-[12px] text-[#858585] mt-0.5">
                            {b.dismissal_kind}
                          </div>
                        )}
                        {!b.is_qualified && (
                          <div className="text-[11px] text-[#666666] mt-0.5 font-mono">
                            {b.sample_reason || `${b.runs} runs / ${b.balls} balls`}
                          </div>
                        )}
                      </td>

                      {/* Team */}
                      <td className="py-3.5 px-3.5 text-[#858585] text-[13px] sm:text-[13.5px] whitespace-nowrap">
                        {b.team}
                      </td>

                      {/* Innings */}
                      <td className="py-3.5 px-3 text-center text-[#858585] text-[13px] sm:text-[13.5px] tabular-nums">
                        {b.innings === 1 ? '1st' : '2nd'}
                      </td>

                      {/* Runs */}
                      <td className="py-3.5 px-3.5 text-right font-semibold text-[#F2F2F2] tabular-nums whitespace-nowrap text-[14px] sm:text-[14.5px]">
                        {b.runs}
                      </td>

                      {/* Balls */}
                      <td className="py-3.5 px-3 text-right text-[#858585] tabular-nums whitespace-nowrap text-[13.5px] sm:text-[14px]">
                        {b.balls}
                      </td>

                      {/* Strike Rate */}
                      <td className="py-3.5 px-3 text-right text-[#B8B8B8] tabular-nums whitespace-nowrap font-mono text-[13.5px] sm:text-[14px]">
                        {b.strike_rate !== null ? Number(b.strike_rate).toFixed(1) : '—'}
                      </td>

                      {/* Contribution Score */}
                      <td className="py-3.5 px-4 text-center whitespace-nowrap">
                        <span
                          className={`inline-block px-3 py-1 rounded-full text-[13px] sm:text-[13.5px] border tabular-nums ${scoreBadge}`}
                        >
                          {b.contribution_score !== null ? Number(b.contribution_score).toFixed(1) : '—'}
                        </span>
                      </td>

                      {/* Result */}
                      <td className="py-3.5 px-3.5 text-center whitespace-nowrap text-[12px]">
                        {b.won_match ? (
                          <span className="px-2.5 py-0.5 rounded-md font-semibold bg-[#152718] text-[#5A9E60] border border-[#2A4D30]">
                            Won
                          </span>
                        ) : (
                          <span className="px-2.5 py-0.5 rounded-md font-semibold bg-[#271414] text-[#C25454] border border-[#4D2626]">
                            Lost
                          </span>
                        )}
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-3.5 text-center whitespace-nowrap">
                        <Link
                          to={`/match/${matchId}/player/${encodeURIComponent(b.player)}`}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1.5 text-[12.5px] sm:text-[13px] font-semibold text-[#D4AF57] hover:text-[#E1C878] hover:underline"
                        >
                          <span>Analyze</span>
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
