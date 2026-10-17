import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Calendar,
  MapPin,
  ArrowRight,
  Filter,
  Search,
  Award,
  Trophy,
  SlidersHorizontal,
  RotateCcw,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { getSeasons, getTeams, getMatches } from '../services/api';
import { useCompetition, TOURNAMENT_TYPES, resolveDefaultSeason } from '../context/CompetitionContext';

export default function Matches() {
  const navigate = useNavigate();
  const {
    competition,
    activeMeta,
    tournamentType,
    setTournamentType,
    selectedSeason,
    setSelectedSeason,
  } = useCompetition();

  // Filters State
  const [seasons, setSeasons] = useState([]);
  const [seasonOptions, setSeasonOptions] = useState([]);
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState('All Teams');
  const [selectedOpponent, setSelectedOpponent] = useState('All Opponents');
  const [selectedResult, setSelectedResult] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(false);

  // Data State
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 1. Load available seasons on mount or when competition/tournamentType changes
  useEffect(() => {
    async function init() {
      try {
        const data = await getSeasons(competition, tournamentType);
        const availSeasons = data.seasons || [];
        setSeasons(availSeasons);
        setSeasonOptions(data.season_options || []);

        setSelectedSeason((curr) => {
          if (curr && availSeasons.includes(curr)) {
            return curr;
          }
          return resolveDefaultSeason(availSeasons, data.default_season);
        });
        setSelectedTeam('All Teams');
        setSelectedOpponent('All Opponents');
      } catch (err) {
        setError(err.message || 'Failed to load matches data.');
        setLoading(false);
      }
    }
    init();
  }, [competition, tournamentType, setSelectedSeason]);

  // 2. Load teams when season, competition or tournamentType changes
  useEffect(() => {
    async function loadTeams() {
      if (!selectedSeason) return;
      try {
        const data = await getTeams(selectedSeason, competition, tournamentType);
        setTeams(data.teams || []);
      } catch {
        // non-blocking
      }
    }
    loadTeams();
  }, [selectedSeason, competition, tournamentType]);

  // 3. Load matches when filters change
  useEffect(() => {
    if (!selectedSeason) return;
    let isMounted = true;

    async function loadMatchesData() {
      setLoading(true);
      setError(null);
      try {
        const res = await getMatches({
          season: selectedSeason,
          team: selectedTeam,
          opponent: selectedOpponent,
          search: searchQuery,
          limit: 300,
          competition,
          tournamentType,
        });

        if (isMounted) {
          setMatches(res.matches || []);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      }
    }

    loadMatchesData();
    return () => {
      isMounted = false;
    };
  }, [selectedSeason, selectedTeam, selectedOpponent, searchQuery, competition, tournamentType]);

  // Filter by result (Won / Lost relative to selected team if applicable)
  const filteredMatches = useMemo(() => {
    if (selectedResult === 'all') return matches;
    return matches.filter((m) => {
      if (selectedTeam !== 'All Teams') {
        const teamWon = m.winner === selectedTeam;
        return selectedResult === 'won' ? teamWon : !teamWon;
      }
      return true;
    });
  }, [matches, selectedResult, selectedTeam]);

  const activeTournamentMeta = useMemo(() => {
    return TOURNAMENT_TYPES.find((t) => t.id === tournamentType) || TOURNAMENT_TYPES[0];
  }, [tournamentType]);

  const currentSeasonLabel = useMemo(() => {
    const opt = seasonOptions.find((o) => o.value === selectedSeason);
    if (opt) return opt.label;
    if (!selectedSeason) return 'All Seasons';
    return competition === 't20i' ? selectedSeason : `${selectedSeason} Season`;
  }, [seasonOptions, selectedSeason, competition]);

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    try {
      const parts = dateStr.split('-');
      if (parts.length === 3) {
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const mIdx = parseInt(parts[1], 10) - 1;
        return `${parseInt(parts[2], 10)} ${months[mIdx] || parts[1]} ${parts[0]}`;
      }
      return dateStr;
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="w-full space-y-8 font-sans text-[#F2F2F2]">
      {/* 1. Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#2D2D2D]">
        <div>
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-[11px] sm:text-[12.5px] font-sans uppercase tracking-wider text-[#D4AF57] font-semibold mb-1.5">
            <Calendar className="w-4 h-4 shrink-0" />
            <span>MATCH-BY-MATCH ANALYSIS</span>
            <span className="text-[#858585]">•</span>
            {competition === 't20i' && (
              <>
                <span className="text-[#D4AF57]">{activeTournamentMeta.label}</span>
                <span className="text-[#858585]">•</span>
              </>
            )}
            <span className="text-[#F2F2F2]">{currentSeasonLabel}</span>
          </div>
          <h1 className="font-heading text-[22px] sm:text-[30px] lg:text-[36px] font-bold text-[#F2F2F2] tracking-wide leading-tight break-words">
            MATCH-BY-MATCH ANALYSIS
          </h1>
          <p className="text-[14px] sm:text-[16px] font-normal text-[#B8B8B8] mt-1.5 leading-relaxed max-w-5xl">
            Analyze every match in {activeMeta?.name || 'the tournament'} and inspect how individual batters performed relative to situational expectations.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
          <span className="px-3 py-1.5 sm:px-3.5 sm:py-2 rounded-lg text-[12px] sm:text-[13.5px] font-medium bg-[#161616] text-[#858585] border border-[#2D2D2D]">
            Matches: <strong className="text-[#D4AF57] ml-1 font-semibold">{filteredMatches.length}</strong>
          </span>
        </div>
      </div>

      {/* 2. Filter Bar */}
      <div className="bg-[#161616] p-4 sm:p-5 rounded-xl border border-[#2D2D2D] shadow-xs space-y-4 font-sans">
        <div className="flex items-center justify-between border-b border-[#2D2D2D] pb-3 text-[12px] sm:text-[12.5px] uppercase tracking-wider text-[#858585]">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-[#D4AF57]" />
            <span className="font-semibold text-[#F2F2F2]">Match Filters</span>
            {(selectedTeam !== 'All Teams' || selectedOpponent !== 'All Opponents' || selectedResult !== 'all' || searchQuery.trim() !== '') && (
              <span className="px-2 py-0.5 rounded bg-[#1E190E] text-[#D4AF57] border border-[#3D351E] text-[11px] font-semibold lowercase">
                active
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {(selectedTeam !== 'All Teams' || selectedOpponent !== 'All Opponents' || selectedResult !== 'all' || searchQuery.trim() !== '') && (
              <button
                type="button"
                onClick={() => {
                  setSelectedTeam('All Teams');
                  setSelectedOpponent('All Opponents');
                  setSelectedResult('all');
                  setSearchQuery('');
                }}
                className="flex items-center gap-1.5 text-[12px] sm:text-[12.5px] text-[#D4AF57] hover:text-[#E1C878] transition-colors cursor-pointer"
                title="Reset all active filters"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>
            )}
            <button
              type="button"
              onClick={() => setAdvancedFiltersOpen(!advancedFiltersOpen)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#121212] hover:bg-[#1A1A1A] border border-[#2D2D2D] text-[12px] sm:text-[12.5px] text-[#B8B8B8] hover:text-[#F2F2F2] transition-colors cursor-pointer"
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-[#D4AF57]" />
              <span>Advanced Filters</span>
              {advancedFiltersOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* Primary Filters Row */}
        <div className={`grid grid-cols-1 sm:grid-cols-2 ${competition === 't20i' ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-4`}>
          {/* Tournament Type Filter (for International T20Is) */}
          {competition === 't20i' && (
            <div>
              <label className="block text-[12.5px] sm:text-[13px] font-semibold text-[#D4AF57] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <Trophy className="w-3.5 h-3.5 text-[#D4AF57]" />
                Tournament Type
              </label>
              <select
                value={tournamentType}
                onChange={(e) => setTournamentType(e.target.value)}
                className="w-full bg-[#101010] border border-[#A8893D]/60 text-[#F2F2F2] rounded-lg px-3.5 py-2 focus:outline-hidden focus:border-[#D4AF57] transition-colors cursor-pointer text-[13.5px] sm:text-[14px] font-medium"
              >
                {TOURNAMENT_TYPES.map((t) => (
                  <option key={t.id} value={t.id} className="bg-[#101010] text-[#F2F2F2]">
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Season Filter */}
          <div>
            <label className="block text-[12.5px] sm:text-[13px] font-semibold text-[#858585] uppercase tracking-wider mb-1.5">
              {competition === 't20i' && (tournamentType === 'world_cup' || tournamentType === 'asia_cup')
                ? 'Edition / Year'
                : 'Season'}
            </label>
            <select
              value={selectedSeason}
              onChange={(e) => {
                setSelectedSeason(e.target.value);
                setSelectedTeam('All Teams');
                setSelectedOpponent('All Opponents');
              }}
              className="w-full bg-[#101010] border border-[#2D2D2D] text-[#F2F2F2] rounded-lg px-3.5 py-2 focus:outline-hidden focus:border-[#D4AF57] transition-colors cursor-pointer text-[13.5px] sm:text-[14px]"
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

          {/* Search Box */}
          <div className={competition === 't20i' ? '' : 'sm:col-span-2 lg:col-span-1'}>
            <label className="block text-[12.5px] sm:text-[13px] font-semibold text-[#858585] uppercase tracking-wider mb-1.5">
              Search Match
            </label>
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3.5 top-3 text-[#858585] pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search team or venue..."
                className="w-full bg-[#101010] border border-[#2D2D2D] text-[#F2F2F2] rounded-lg pl-10 pr-3.5 py-2 text-[13.5px] sm:text-[14px] focus:outline-hidden focus:border-[#D4AF57] placeholder-[#666666] transition-colors"
              />
            </div>
          </div>
        </div>

        {/* Expandable Advanced Filters Drawer */}
        {advancedFiltersOpen && (
          <div className="pt-4 border-t border-[#222222] grid grid-cols-1 sm:grid-cols-3 gap-4 bg-[#121212]/50 p-4 rounded-xl">
            {/* Team Filter */}
            <div>
              <label className="block text-[12.5px] sm:text-[13px] font-semibold text-[#858585] uppercase tracking-wider mb-1.5">
                Team
              </label>
              <select
                value={selectedTeam}
                onChange={(e) => setSelectedTeam(e.target.value)}
                className="w-full bg-[#101010] border border-[#2D2D2D] text-[#F2F2F2] rounded-lg px-3.5 py-2 focus:outline-hidden focus:border-[#D4AF57] transition-colors cursor-pointer text-[13.5px] sm:text-[14px]"
              >
                <option value="All Teams">All Teams</option>
                {teams.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            {/* Opponent Filter */}
            <div>
              <label className="block text-[12.5px] sm:text-[13px] font-semibold text-[#858585] uppercase tracking-wider mb-1.5">
                Opponent
              </label>
              <select
                value={selectedOpponent}
                onChange={(e) => setSelectedOpponent(e.target.value)}
                className="w-full bg-[#101010] border border-[#2D2D2D] text-[#F2F2F2] rounded-lg px-3.5 py-2 focus:outline-hidden focus:border-[#D4AF57] transition-colors cursor-pointer text-[13.5px] sm:text-[14px]"
              >
                <option value="All Opponents">All Opponents</option>
                {teams.map((t) => (
                  <option key={`opp-${t}`} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            {/* Result Filter (if team selected) */}
            <div>
              <label className="block text-[12.5px] sm:text-[13px] font-semibold text-[#858585] uppercase tracking-wider mb-1.5">
                Result
              </label>
              <select
                value={selectedResult}
                onChange={(e) => setSelectedResult(e.target.value)}
                disabled={selectedTeam === 'All Teams'}
                className={`w-full bg-[#101010] border border-[#2D2D2D] rounded-lg px-3.5 py-2 focus:outline-hidden transition-colors text-[13.5px] sm:text-[14px] ${
                  selectedTeam === 'All Teams'
                    ? 'text-[#666666] cursor-not-allowed opacity-60'
                    : 'text-[#F2F2F2] focus:border-[#D4AF57] cursor-pointer'
                }`}
                title={selectedTeam === 'All Teams' ? 'Select a team first to filter by win/loss' : ''}
              >
                <option value="all">All Results</option>
                <option value="won">Matches Won</option>
                <option value="lost">Matches Lost</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-[#271414] border border-[#4D2626] text-[#C25454] text-[13px] font-medium">
          Error loading matches: {error}
        </div>
      )}

      {/* 3. Match List Table */}
      <div className="bg-[#161616] rounded-xl border border-[#2D2D2D] shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-[#2D2D2D] bg-[#101010] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
              MATCH LIST ({filteredMatches.length} MATCHES)
            </h2>
            <p className="text-[13px] sm:text-[13.5px] font-sans text-[#858585] mt-1">
              Select any match to view the complete batter contribution ratings and performance breakdown.
            </p>
          </div>
          <span className="text-[12px] font-sans text-[#D4AF57] bg-[#161616] px-3 py-1.5 rounded-lg border border-[#3D351E] self-start sm:self-auto">
            {currentSeasonLabel}
          </span>
        </div>

        {loading ? (
          <div className="p-6 space-y-3">
            {Array.from({ length: 5 }).map((_, idx) => (
              <div key={`skel-m-${idx}`} className="skeleton h-16 w-full rounded-lg" />
            ))}
          </div>
        ) : filteredMatches.length === 0 ? (
          <div className="py-16 text-center">
            <div className="max-w-md mx-auto space-y-3">
              <div className="w-12 h-12 rounded-full bg-[#1A1A1A] border border-[#2D2D2D] flex items-center justify-center mx-auto text-[#D4AF57]">
                <Calendar className="w-6 h-6" />
              </div>
              <div className="text-[16px] font-semibold text-[#F2F2F2]">No Matches Found</div>
              <p className="text-[13px] text-[#858585]">
                No matches matched your selected filters. Try clearing team filters or search keywords.
              </p>
              <button
                type="button"
                onClick={() => {
                  setSelectedTeam('All Teams');
                  setSelectedOpponent('All Opponents');
                  setSelectedResult('all');
                  setSearchQuery('');
                }}
                className="btn-secondary text-[12.5px] py-1.5 px-4 cursor-pointer inline-flex items-center gap-1.5"
              >
                Reset Filters
              </button>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto w-full max-w-full min-w-0">
            <table className="w-full text-left border-collapse font-sans">
              <thead>
                <tr className="border-b border-[#2D2D2D] bg-[#101010] text-[#858585] font-semibold text-[12.5px] sm:text-[13px] tracking-wider uppercase">
                  <th className="py-3.5 px-4 whitespace-nowrap">DATE</th>
                  <th className="py-3.5 px-4 min-w-[280px]">MATCH</th>
                  <th className="py-3.5 px-4 min-w-[210px]">VENUE</th>
                  <th className="py-3.5 px-4 min-w-[220px]">RESULT</th>
                  <th className="py-3.5 px-4 min-w-[210px]">TOP CONTRIBUTOR</th>
                  <th className="py-3.5 px-4 text-center">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#222222] text-[#F2F2F2] text-[14px] sm:text-[14.5px]">
                {filteredMatches.map((m) => {
                  const isT1Winner = m.winner === m.team1;
                  const isT2Winner = m.winner === m.team2;

                  return (
                    <tr
                      key={m.match_id}
                      onClick={() => navigate(`/matches/${m.match_id}`)}
                      className="cursor-pointer hover:bg-[#1A1A1A] transition-colors group"
                    >
                      {/* Date */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-[#858585] text-[13px] font-sans">
                        {formatDate(m.date)}
                      </td>

                      {/* Match & Scores */}
                      <td className="py-3.5 px-4">
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between gap-3">
                            <span
                              className={`font-semibold text-[14px] sm:text-[14.5px] transition-colors ${
                                isT1Winner ? 'text-[#F2F2F2]' : 'text-[#B8B8B8]'
                              }`}
                            >
                              {m.team1}
                            </span>
                            {m.team1_score !== null && (
                              <span className="font-sans text-[13.5px] sm:text-[14px] font-semibold tabular-nums text-[#D4AF57]">
                                {m.team1_score}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center justify-between gap-3">
                            <span
                              className={`font-semibold text-[14px] sm:text-[14.5px] transition-colors ${
                                isT2Winner ? 'text-[#F2F2F2]' : 'text-[#B8B8B8]'
                              }`}
                            >
                              {m.team2}
                            </span>
                            {m.team2_score !== null && (
                              <span className="font-sans text-[13.5px] sm:text-[14px] font-semibold tabular-nums text-[#D4AF57]">
                                {m.team2_score}
                              </span>
                            )}
                          </div>
                          {m.event_name && m.event_name !== 'Indian Premier League' && (
                            <div className="pt-1">
                              <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded bg-[#1F1C14] border border-[#D4AF57]/40 text-[#D4AF57]">
                                <Trophy className="w-3 h-3" />
                                {m.event_name}
                                {m.stage ? ` • ${m.stage}` : ''}
                              </span>
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Venue */}
                      <td className="py-3.5 px-4 text-[13px] sm:text-[13.5px] text-[#858585]">
                        <div className="flex items-start gap-2">
                          <MapPin className="w-4 h-4 shrink-0 mt-0.5 text-[#666666]" />
                          <span className="line-clamp-2 leading-snug">{m.venue}</span>
                        </div>
                      </td>

                      {/* Result */}
                      <td className="py-3.5 px-4">
                        <div className="space-y-1.5">
                          <div className="text-[13.5px] sm:text-[14px] font-medium text-[#F2F2F2] leading-snug">
                            {m.result}
                          </div>
                          {m.winner && (
                            <span className="inline-flex items-center gap-1 text-[11.5px] sm:text-[12px] font-semibold px-2.5 py-0.5 rounded-md bg-[#152718] text-[#5A9E60] border border-[#2A4D30]">
                              Winner: {m.winner}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Top Contributor */}
                      <td className="py-3.5 px-4">
                        {m.top_contributor ? (
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <Award className="w-4 h-4 text-[#D4AF57] shrink-0" />
                              <span className="font-semibold text-[14px] sm:text-[14.5px] text-[#F2F2F2]">
                                {m.top_contributor.player}
                              </span>
                              <span className="inline-block px-2 py-0.5 rounded text-[12px] font-bold bg-[#1C1A14] text-[#D4AF57] border border-[#3D351E] tabular-nums">
                                {m.top_contributor.contribution_score}
                              </span>
                            </div>
                            <div className="text-[12px] sm:text-[12.5px] text-[#858585] tabular-nums pl-6">
                              {m.top_contributor.runs} runs ({m.top_contributor.balls}b) • SR {m.top_contributor.sr}
                            </div>
                          </div>
                        ) : (
                          <span className="text-[13px] text-[#858585]">—</span>
                        )}
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-4 text-center whitespace-nowrap">
                        <Link
                          to={`/matches/${m.match_id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[12.5px] sm:text-[13px] font-semibold bg-[#101010] text-[#D4AF57] hover:text-[#080808] hover:bg-[#D4AF57] border border-[#2D2D2D] hover:border-[#D4AF57] transition-all"
                        >
                          <span>View Match</span>
                          <ArrowRight className="w-3.5 h-3.5" />
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
