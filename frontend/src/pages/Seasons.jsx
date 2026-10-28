import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Trophy,
  Award,
  ExternalLink,
  ShieldCheck,
  Info,
} from 'lucide-react';
import { getSeasons, getPlayers } from '../services/api';
import { useCompetition, TOURNAMENT_TYPES, resolveDefaultSeason } from '../context/CompetitionContext';

export default function Seasons() {
  const navigate = useNavigate();
  const {
    competition,
    tournamentType,
    setTournamentType,
    selectedSeason,
    setSelectedSeason,
  } = useCompetition();

  const [seasons, setSeasons] = useState([]);
  const [seasonOptions, setSeasonOptions] = useState([]);
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retryKey, setRetryKey] = useState(0);

  const minRunsThreshold = useMemo(() => {
    if (competition === 'ipl') return 350;
    if (tournamentType === 'world_cup' || tournamentType === 'asia_cup') return 100;
    return 150;
  }, [competition, tournamentType]);

  // 1. Load seasons on mount or when competition/tournamentType changes
  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        const data = await getSeasons(competition, tournamentType);
        if (cancelled) return;
        const availSeasons = data.seasons || [];
        setSeasons(availSeasons);
        setSeasonOptions(data.season_options || []);

        setSelectedSeason((curr) => {
          if (curr && availSeasons.includes(curr)) {
            return curr;
          }
          return resolveDefaultSeason(availSeasons, data.default_season);
        });
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load available seasons.');
          setLoading(false);
        }
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, [competition, tournamentType, setSelectedSeason, retryKey]);

  // 2. Load players for the selected season and competition
  useEffect(() => {
    if (!selectedSeason) return;
    let isMounted = true;

    async function loadLeaderboard() {
      setLoading(true);
      setError(null);
      try {
        const data = await getPlayers({
          season: selectedSeason,
          minRuns: minRunsThreshold,
          limit: 200,
          competition,
          tournamentType,
        });

        if (isMounted) {
          setPlayers(data.players || []);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'Failed to load player leaderboard.');
          setLoading(false);
        }
      }
    }

    loadLeaderboard();
    return () => {
      isMounted = false;
    };
  }, [selectedSeason, competition, tournamentType, minRunsThreshold, retryKey]);

  // 3. Rank eligible players by Average Contribution Score descending, secondary tie-breaker: actual_runs descending
  const top10Leaderboard = useMemo(() => {
    const eligible = [...players].filter(
      (p) => p.actual_runs >= minRunsThreshold && p.average_contribution_score !== null
    );

    eligible.sort((a, b) => {
      const scoreDiff = (b.average_contribution_score || 0) - (a.average_contribution_score || 0);
      if (Math.abs(scoreDiff) > 0.0001) {
        return scoreDiff;
      }
      // Tie-breaker: Total runs descending
      return (b.actual_runs || 0) - (a.actual_runs || 0);
    });

    return eligible.slice(0, 10);
  }, [players, minRunsThreshold]);

  const top3 = top10Leaderboard.slice(0, 3);

  const currentSeasonLabel = useMemo(() => {
    const opt = seasonOptions.find((o) => o.value === selectedSeason);
    if (opt) return opt.label;
    if (!selectedSeason) return 'All Seasons';
    return competition === 't20i' ? selectedSeason : `${selectedSeason} Season`;
  }, [seasonOptions, selectedSeason, competition]);

  return (
    <div className="w-full space-y-6 sm:space-y-7 font-sans text-[#F2F2F2]">
      {/* 1. Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#2D2D2D]">
        <div>
          <div className="flex flex-wrap items-center gap-1.5 text-[11px] sm:text-[11.5px] font-sans uppercase tracking-wider text-[#D4AF57] font-semibold mb-1">
            <Trophy className="w-3.5 h-3.5 shrink-0" />
            <span>SEASON LEADERBOARD</span>
            <span className="text-[#858585]">•</span>
            <span className="text-[#F2F2F2]">{currentSeasonLabel}</span>
          </div>
          <h1 className="font-heading text-[22px] sm:text-[26px] lg:text-[28px] font-bold text-[#F2F2F2] tracking-wide leading-tight break-words">
            TOP 10 BATTERS — {currentSeasonLabel}
          </h1>
          <p className="text-[13px] sm:text-[14px] font-normal text-[#B8B8B8] mt-1 leading-relaxed max-w-4xl">
            Top contributors are ranked by average Contribution Score among batters who scored at least {minRunsThreshold} runs in the selected tournament/season.
          </p>
        </div>

        {/* Filter Selectors */}
        <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto shrink-0 bg-[#161616] p-1.5 sm:p-2 rounded-lg border border-[#2D2D2D]">
          {competition === 't20i' && (
            <div className="flex items-center gap-1.5">
              <span className="text-[11.5px] font-semibold text-[#D4AF57] uppercase tracking-wider pl-1">
                Type:
              </span>
              <select
                value={tournamentType}
                onChange={(e) => setTournamentType(e.target.value)}
                className="bg-[#101010] border border-[#A8893D]/60 text-[#D4AF57] font-bold text-[12px] sm:text-[12.5px] rounded-md px-2.5 py-1.5 focus:outline-hidden cursor-pointer"
              >
                {TOURNAMENT_TYPES.map((t) => (
                  <option key={t.id} value={t.id} className="bg-[#101010] text-[#F2F2F2]">
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-center gap-1.5">
            <span className="text-[11.5px] font-semibold text-[#858585] uppercase tracking-wider pl-1">
              {competition === 't20i' && (tournamentType === 'world_cup' || tournamentType === 'asia_cup') ? 'Edition:' : 'Season:'}
            </span>
            <select
              value={selectedSeason}
              onChange={(e) => setSelectedSeason(e.target.value)}
              className="bg-[#101010] border border-[#2D2D2D] text-[#D4AF57] font-bold text-[12px] sm:text-[12.5px] rounded-md px-2.5 py-1.5 focus:outline-hidden focus:border-[#D4AF57] transition-colors cursor-pointer"
            >
              {seasonOptions.length > 0 ? (
                seasonOptions.map((opt) => (
                  <option key={opt.value} value={opt.value} className="bg-[#101010] text-[#F2F2F2]">
                    {opt.label}
                  </option>
                ))
              ) : (
                seasons.map((s) => (
                  <option key={s} value={s} className="bg-[#101010] text-[#F2F2F2]">
                    {competition === 't20i' ? s : `${s} Season`}
                  </option>
                ))
              )}
            </select>
          </div>
        </div>
      </div>

      {/* 2. Methodology & Rules Badges */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-sans text-[12px] sm:text-[12.5px]">
        <div className="bg-[#161616] p-3 sm:p-3.5 rounded-lg border border-[#2D2D2D] flex items-center gap-3 shadow-xs">
          <div className="w-7 h-7 rounded-md bg-[#1C1A14] border border-[#3D351E] flex items-center justify-center text-[#D4AF57] shrink-0">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wider text-[#858585] font-semibold">Eligibility Requirement</div>
            <div className="font-bold text-[#F2F2F2] text-[13px] sm:text-[13.5px]">{minRunsThreshold}+ Runs in {competition === 't20i' ? 'Tournament' : 'Season'}</div>
          </div>
        </div>

        <div className="bg-[#161616] p-3 sm:p-3.5 rounded-lg border border-[#2D2D2D] flex items-center gap-3 shadow-xs">
          <div className="w-7 h-7 rounded-md bg-[#1C1A14] border border-[#3D351E] flex items-center justify-center text-[#D4AF57] shrink-0">
            <Award className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wider text-[#858585] font-semibold">Ranking Criterion</div>
            <div className="font-bold text-[#D4AF57] text-[13px] sm:text-[13.5px]">Average Contribution Score</div>
          </div>
        </div>

        <div className="bg-[#161616] p-3 sm:p-3.5 rounded-lg border border-[#2D2D2D] flex items-center gap-3 shadow-xs">
          <div className="w-7 h-7 rounded-md bg-[#101010] border border-[#2D2D2D] flex items-center justify-center text-[#858585] shrink-0">
            <Info className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wider text-[#858585] font-semibold">Model Par Benchmark</div>
            <div className="font-bold text-[#F2F2F2] text-[13px] sm:text-[13.5px]">50.0 Baseline per Opportunity</div>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-[#271414] border border-[#4D2626] text-[#C25454] text-[12.5px] font-medium flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div>
            <span className="font-semibold block sm:inline">Error loading season leaderboard: </span>
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => {
              setError(null);
              setLoading(true);
              setRetryKey((k) => k + 1);
            }}
            className="self-start sm:self-auto px-2.5 py-1 rounded-md bg-[#3D1A1A] hover:bg-[#4D2222] border border-[#6B2E2E] text-[#F2F2F2] text-xs font-semibold transition-colors cursor-pointer shrink-0"
          >
            Retry
          </button>
        </div>
      )}

      {/* 3. Top 3 Compact Ranking Cards */}
      {!loading && top3.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-3.5">
          {top3.map((p, idx) => {
            let cardAccent = 'border-[#3D351E] bg-[#161616]';
            let badgeBg = 'bg-[#2E2717] text-[#D4AF57] border-[#D4AF57]/40';
            let titleColor = 'text-[#D4AF57]';
            let rankLabel = '#1 Leader';

            if (idx === 1) {
              cardAccent = 'border-[#3D3D3D] bg-[#161616]';
              badgeBg = 'bg-[#222222] text-[#B8B8B8] border-[#3D3D3D]';
              titleColor = 'text-[#B8B8B8]';
              rankLabel = '#2 Runner-up';
            } else if (idx === 2) {
              cardAccent = 'border-[#3D3020] bg-[#161616]';
              badgeBg = 'bg-[#241D17] text-[#A8893D] border-[#A8893D]/30';
              titleColor = 'text-[#A8893D]';
              rankLabel = '#3 Third';
            }

            const sr = p.balls_faced > 0 ? ((p.actual_runs / p.balls_faced) * 100).toFixed(1) : '—';

            return (
              <div
                key={`top3-${p.player}`}
                onClick={() => navigate(`/player/${encodeURIComponent(p.player)}/${encodeURIComponent(selectedSeason || p.season)}?competition=${encodeURIComponent(competition || 'ipl')}`)}
                className={`p-4 sm:p-4.5 rounded-lg border shadow-xs transition-all hover:bg-[#1C1C1C] cursor-pointer space-y-2.5 ${cardAccent}`}
              >
                <div className="flex items-center justify-between">
                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${badgeBg}`}>
                    {rankLabel}
                  </span>
                  <span className="text-[12px] text-[#858585]">{p.team}</span>
                </div>

                <div>
                  <h3 className="font-heading text-[16px] sm:text-[17px] font-bold text-[#F2F2F2] hover:text-[#D4AF57] transition-colors">
                    {p.player}
                  </h3>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className={`font-heading text-[24px] sm:text-[28px] font-bold tabular-nums ${titleColor}`}>
                      {Number(p.average_contribution_score).toFixed(1)}
                    </span>
                    <span className="text-[12px] text-[#858585]">Avg Contribution</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-[#222222] grid grid-cols-3 gap-2 text-[12px] text-[#858585]">
                  <div>
                    <span className="block text-[10.5px] text-[#666666] uppercase">Runs</span>
                    <strong className="text-[#F2F2F2] font-semibold tabular-nums text-[12.5px] sm:text-[13px]">{p.actual_runs}</strong>
                  </div>
                  <div>
                    <span className="block text-[10.5px] text-[#666666] uppercase">SR</span>
                    <strong className="text-[#F2F2F2] font-semibold tabular-nums text-[12.5px] sm:text-[13px]">{sr}</strong>
                  </div>
                  <div>
                    <span className="block text-[10.5px] text-[#666666] uppercase">Innings</span>
                    <strong className="text-[#F2F2F2] font-semibold tabular-nums text-[12.5px] sm:text-[13px]">{p.batting_innings}</strong>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 4. Top 10 Season Leaderboard Table */}
      <div className="bg-[#161616] rounded-xl border border-[#2D2D2D] shadow-xs overflow-hidden max-w-full min-w-0">
        <div className="px-3.5 sm:px-4 py-3 border-b border-[#2D2D2D] bg-[#101010] flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div>
            <h2 className="font-heading text-[16px] sm:text-[18px] font-bold text-[#F2F2F2] tracking-wide">
              SEASON TOP 10 LEADERBOARD TABLE
            </h2>
            <p className="text-[12px] font-sans text-[#858585] mt-0.5">
              Ranked descending by Average Contribution Score. Only batters scoring {minRunsThreshold}+ runs in {currentSeasonLabel} are eligible.
            </p>
          </div>
          <span className="text-[11.5px] font-sans text-[#D4AF57] bg-[#161616] px-2.5 py-1 rounded-md border border-[#3D351E] self-start sm:self-auto">
            {top10Leaderboard.length} / 10 Ranked
          </span>
        </div>

        {loading ? (
          <div className="p-4 space-y-2.5">
            {Array.from({ length: 5 }).map((_, idx) => (
              <div key={`skel-s-${idx}`} className="skeleton h-10 w-full rounded-md" />
            ))}
          </div>
        ) : top10Leaderboard.length === 0 ? (
          <div className="py-12 text-center text-[13px] text-[#858585]">
            No players reached the {minRunsThreshold}+ runs eligibility threshold in {currentSeasonLabel}.
          </div>
        ) : (
          <div className="overflow-x-auto w-full max-w-full min-w-0">
            <table className="w-full text-left border-collapse font-sans">
              <thead>
                <tr className="border-b border-[#2D2D2D] bg-[#101010] text-[#858585] font-semibold text-[11px] sm:text-[11.5px] tracking-wider uppercase">
                  <th className="py-2.5 px-3 text-center w-12 sm:w-14">RANK</th>
                  <th className="py-2.5 px-3 sm:px-3.5">BATTER</th>
                  <th className="py-2.5 px-2.5 sm:px-3">TEAM</th>
                  <th className="py-2.5 px-2.5 sm:px-3 text-right">RUNS</th>
                  <th className="py-2.5 px-2 text-right">BALLS</th>
                  <th className="py-2.5 px-2 text-right">SR</th>
                  <th className="py-2.5 px-2 text-center">INNS</th>
                  <th className="py-2.5 px-3 text-center">AVG CONTRIB</th>
                  <th className="py-2.5 px-2.5 sm:px-3 text-right">POS CONTRIB</th>
                  <th className="py-2.5 px-2.5 sm:px-3 text-right">TEAM SHARE</th>
                  <th className="py-2.5 px-3 text-center">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#222222] text-[#F2F2F2] text-[12.5px]">
                {top10Leaderboard.map((p, idx) => {
                  const sr = p.balls_faced > 0 ? ((p.actual_runs / p.balls_faced) * 100).toFixed(1) : '—';

                  let rankBadge = 'text-[#858585]';
                  if (idx === 0) rankBadge = 'bg-[#2E2717] text-[#D4AF57] border border-[#D4AF57]/40 font-bold';
                  else if (idx === 1) rankBadge = 'bg-[#222222] text-[#B8B8B8] border border-[#3D3D3D] font-bold';
                  else if (idx === 2) rankBadge = 'bg-[#241D17] text-[#A8893D] border border-[#A8893D]/30 font-bold';

                  const score = p.average_contribution_score;
                  let scoreBadge = 'bg-[#101010] text-[#858585] border-[#2D2D2D]';
                  if (score !== null && score !== undefined) {
                    if (score >= 65) scoreBadge = 'bg-[#152718] text-[#5A9E60] border-[#2A4D30] font-bold';
                    else if (score >= 52) scoreBadge = 'bg-[#152718] text-[#5A9E60] border-[#2A4D30]/60 font-semibold';
                    else if (score >= 48) scoreBadge = 'bg-[#1F1C14] text-[#D4AF57] border-[#A8893D]/40 font-medium';
                    else scoreBadge = 'bg-[#271414] text-[#C25454] border-[#4D2626] font-semibold';
                  }

                  return (
                    <tr
                      key={`top10-${p.player}`}
                      onClick={() => navigate(`/player/${encodeURIComponent(p.player)}/${encodeURIComponent(selectedSeason || p.season)}?competition=${encodeURIComponent(competition || 'ipl')}`)}
                      className="cursor-pointer hover:bg-[#1A1A1A] transition-colors"
                    >
                      {/* Rank */}
                      <td className="py-2 px-3 text-center">
                        <span
                          className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[11px] ${rankBadge}`}
                        >
                          {idx + 1}
                        </span>
                      </td>

                      {/* Batter */}
                      <td className="py-2 px-3 sm:px-3.5 whitespace-nowrap">
                        <span className="font-semibold text-[13px] sm:text-[13.5px] text-[#F2F2F2] hover:text-[#D4AF57] transition-colors">
                          {p.player}
                        </span>
                        {p.not_outs > 0 && (
                          <span className="text-[11px] font-normal text-[#858585] ml-1 font-sans">
                            ({p.not_outs} NO)
                          </span>
                        )}
                      </td>

                      {/* Team */}
                      <td className="py-2 px-2.5 sm:px-3 text-[#858585] text-[12px] sm:text-[12.5px] whitespace-nowrap">
                        {p.team}
                      </td>

                      {/* Runs */}
                      <td className="py-2 px-2.5 sm:px-3 text-right font-bold text-[#F2F2F2] tabular-nums whitespace-nowrap">
                        {p.actual_runs}
                      </td>

                      {/* Balls */}
                      <td className="py-2 px-2 text-right text-[#858585] tabular-nums whitespace-nowrap">
                        {p.balls_faced}
                      </td>

                      {/* Strike Rate */}
                      <td className="py-2 px-2 text-right text-[#B8B8B8] tabular-nums whitespace-nowrap">
                        {sr}
                      </td>

                      {/* Batting Innings */}
                      <td className="py-2 px-2 text-center text-[#F2F2F2] tabular-nums whitespace-nowrap">
                        {p.batting_innings}
                      </td>

                      {/* Average Contribution */}
                      <td className="py-2 px-3 text-center whitespace-nowrap">
                        <span
                          className={`inline-block px-2.5 py-0.5 rounded-full text-[12px] border tabular-nums ${scoreBadge}`}
                        >
                          {score !== null ? Number(score).toFixed(1) : '—'}
                        </span>
                      </td>

                      {/* Positive Contribution */}
                      <td className="py-2 px-2.5 sm:px-3 text-right font-sans text-[#5A9E60] font-medium tabular-nums whitespace-nowrap">
                        {p.total_positive_raw_contribution !== null
                          ? Number(p.total_positive_raw_contribution).toFixed(2)
                          : '—'}
                      </td>

                      {/* Team Share */}
                      <td className="py-2 px-2.5 sm:px-3 text-right font-sans text-[#F2F2F2] tabular-nums whitespace-nowrap">
                        {p.season_team_contribution_share !== null
                          ? `${Number(p.season_team_contribution_share).toFixed(1)}%`
                          : '—'}
                      </td>

                      {/* Action */}
                      <td className="py-2 px-3 text-center whitespace-nowrap">
                        <Link
                          to={`/player/${encodeURIComponent(p.player)}/${encodeURIComponent(selectedSeason || p.season)}?competition=${encodeURIComponent(competition || 'ipl')}`}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 text-[12px] font-semibold text-[#D4AF57] hover:text-[#E1C878] hover:underline"
                        >
                          <span>Analyze</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
