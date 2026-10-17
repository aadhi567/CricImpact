import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Users,
  ArrowUpDown,
  ExternalLink,
  Info,
  X,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import SeasonFilter from '../components/SeasonFilter';
import {
  getSeasons,
  getTeams,
  getPlayers,
} from '../services/api';
import { useCompetition, TOURNAMENT_TYPES, resolveDefaultSeason } from '../context/CompetitionContext';

export default function Players() {
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
  const [selectedTeam, setSelectedTeam] = useState('');
  const [minRuns, setMinRuns] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  // Pagination State
  const [pageSize, setPageSize] = useState(50);
  const [currentPage, setCurrentPage] = useState(1);

  // Data States
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // View A vs View B toggle
  const [viewMode, setViewMode] = useState('view_a');

  // Sorting
  const [sortField, setSortField] = useState('average_contribution_score');
  const [sortDirection, setSortDirection] = useState('desc');

  // Comparison State (Max 5, Min 2)
  const [selectedForCompare, setSelectedForCompare] = useState([]);
  const [compareWarning, setCompareWarning] = useState('');

  // Clear comparison selection whenever season changes
  const handleSeasonChange = (s) => {
    setSelectedSeason(s);
    setSelectedTeam('');
    setSelectedForCompare([]);
    setCompareWarning('');
  };

  const handleToggleCompare = (playerName) => {
    setCompareWarning('');
    if (selectedForCompare.includes(playerName)) {
      setSelectedForCompare((prev) => prev.filter((p) => p !== playerName));
    } else {
      if (selectedForCompare.length >= 5) {
        setCompareWarning('Maximum 5 players can be compared.');
        setTimeout(() => setCompareWarning(''), 4000);
        return;
      }
      setSelectedForCompare((prev) => [...prev, playerName]);
    }
  };

  const handleRemoveCompare = (playerName) => {
    setCompareWarning('');
    setSelectedForCompare((prev) => prev.filter((p) => p !== playerName));
  };

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
        setSelectedTeam('');
        setSelectedForCompare([]);
      } catch (err) {
        setError(err.message || 'Failed to load player seasons.');
        setLoading(false);
      }
    }
    init();
  }, [competition, tournamentType, setSelectedSeason]);

  // 2. Load teams when season, competition, or tournamentType changes
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

  // 3. Load players when filters change
  useEffect(() => {
    if (!selectedSeason) return;

    let isMounted = true;
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const playRes = await getPlayers({
          season: selectedSeason,
          team: selectedTeam,
          minRuns,
          search: searchQuery,
          limit: 500,
          competition,
          tournamentType,
        });

        if (isMounted) {
          setPlayers(playRes.players || []);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, [selectedSeason, selectedTeam, minRuns, searchQuery, competition, tournamentType]);

  // Handle Sort
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Sorted Players
  const sortedPlayers = useMemo(() => {
    const list = [...players];
    list.sort((a, b) => {
      let valA;
      let valB;

      if (sortField === 'strike_rate') {
        valA = a.balls_faced > 0 ? (a.actual_runs / a.balls_faced) * 100 : 0;
        valB = b.balls_faced > 0 ? (b.actual_runs / b.balls_faced) * 100 : 0;
      } else {
        valA = a[sortField];
        valB = b[sortField];
      }

      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      if (typeof valA === 'string') {
        return sortDirection === 'asc'
          ? valA.localeCompare(valB)
          : valB.localeCompare(valA);
      }
      return sortDirection === 'asc' ? valA - valB : valB - valA;
    });
    return list;
  }, [players, sortField, sortDirection]);

  const totalPages = useMemo(() => {
    if (pageSize === 'all') return 1;
    return Math.max(1, Math.ceil(sortedPlayers.length / Number(pageSize)));
  }, [sortedPlayers.length, pageSize]);

  const paginatedPlayers = useMemo(() => {
    if (pageSize === 'all') return sortedPlayers;
    const size = Number(pageSize) || 50;
    const start = (currentPage - 1) * size;
    return sortedPlayers.slice(start, start + size);
  }, [sortedPlayers, currentPage, pageSize]);

  const currentSeasonLabel = useMemo(() => {
    const opt = seasonOptions.find((o) => o.value === selectedSeason);
    return opt ? opt.label : selectedSeason;
  }, [seasonOptions, selectedSeason]);

  return (
    <div className="w-full space-y-8 font-sans text-[#F2F2F2]">
      {/* 1. Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#2D2D2D]">
        <div>
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-[11px] sm:text-[12px] font-sans uppercase tracking-wider text-[#D4AF57] font-semibold mb-1.5">
            <Users className="w-4 h-4 shrink-0" />
            <span>INDIVIDUAL PLAYER ANALYSIS</span>
            {competition === 't20i' && tournamentType && tournamentType !== 'all' && (
              <>
                <span className="text-[#858585]">•</span>
                <span className="text-[#D4AF57] bg-[#1E190E] px-2 py-0.5 rounded border border-[#3D351E]">
                  {TOURNAMENT_TYPES.find((t) => t.id === tournamentType)?.label || tournamentType}
                </span>
              </>
            )}
            <span className="text-[#858585]">•</span>
            <span className="text-[#F2F2F2]">{selectedSeason ? currentSeasonLabel : 'Season Overview'}</span>
          </div>
          <h1 className="font-heading text-[22px] sm:text-[30px] lg:text-[36px] font-bold text-[#F2F2F2] tracking-wide leading-tight break-words">
            INDIVIDUAL PLAYER ANALYSIS
          </h1>
          <p className="text-[14px] sm:text-[16px] font-normal text-[#B8B8B8] mt-1.5 leading-relaxed max-w-5xl">
            Evaluate individual batter contribution, situation handling, and multi-player comparisons across {activeMeta?.name || 'the season'}.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto shrink-0 flex-wrap">
          {competition === 't20i' && (
            <span className="px-3 py-1.5 sm:px-3.5 sm:py-2 rounded-lg text-[12px] sm:text-[13px] font-medium bg-[#161616] text-[#858585] border border-[#2D2D2D]">
              Tournament: <strong className="text-[#D4AF57] ml-1 font-semibold">{TOURNAMENT_TYPES.find((t) => t.id === tournamentType)?.label || 'All International T20Is'}</strong>
            </span>
          )}
          <span className="px-3 py-1.5 sm:px-3.5 sm:py-2 rounded-lg text-[12px] sm:text-[13px] font-medium bg-[#161616] text-[#858585] border border-[#2D2D2D]">
            Players: <strong className="text-[#D4AF57] ml-1 font-semibold">{sortedPlayers.length}</strong>
          </span>
        </div>
      </div>

      {/* 2. Filter Bar */}
      <SeasonFilter
        tournamentType={tournamentType}
        onTournamentTypeChange={setTournamentType}
        showTournamentType={competition === 't20i'}
        seasons={seasons}
        seasonOptions={seasonOptions}
        selectedSeason={selectedSeason}
        onSeasonChange={handleSeasonChange}
        teams={teams}
        selectedTeam={selectedTeam}
        onTeamChange={(t) => {
          setSelectedTeam(t);
          setCurrentPage(1);
        }}
        minRuns={minRuns}
        onMinRunsChange={(r) => {
          setMinRuns(r);
          setCurrentPage(1);
        }}
        searchQuery={searchQuery}
        onSearchChange={(q) => {
          setSearchQuery(q);
          setCurrentPage(1);
        }}
      />

      {error && (
        <div className="p-4 rounded-xl bg-[#271414] border border-[#4D2626] text-[#C25454] text-[13px] font-medium">
          Error loading players: {error}
        </div>
      )}

      {/* 3. Player Analytical Table */}
      <div
        id="players-table"
        className="bg-[#161616] rounded-xl border border-[#2D2D2D] shadow-xs overflow-hidden max-w-full min-w-0"
      >
        <div className="p-4 sm:p-5 border-b border-[#2D2D2D] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="font-heading text-[19px] sm:text-[23px] font-bold text-[#F2F2F2]">
                Season Player Analytical Table
              </h2>
              <span className="text-[13px] font-normal text-[#858585]">({sortedPlayers.length} players)</span>
            </div>
            <p className="text-[13px] font-normal text-[#858585] mt-1">
              Click any player row to open match analysis. Click "[+ Compare]" to select up to 5 batters.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
            {(selectedTeam !== '' || minRuns !== 0 || searchQuery.trim() !== '') && (
              <button
                type="button"
                onClick={() => {
                  setSelectedTeam('');
                  setMinRuns(0);
                  setSearchQuery('');
                }}
                className="flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium bg-[#161616] border border-[#2D2D2D] text-[#D4AF57] hover:text-[#E1C878] hover:border-[#D4AF57]/40 transition-colors cursor-pointer"
                title="Reset search and filters"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Reset Filters</span>
              </button>
            )}

            {/* View A vs View B Toggle */}
            <div className="inline-flex rounded-lg bg-[#101010] p-1 border border-[#2D2D2D] self-start sm:self-auto shrink-0 max-w-full">
              <button
                type="button"
                onClick={() => setViewMode('view_a')}
                className={`px-2.5 sm:px-3.5 py-1.5 rounded-md text-[12px] sm:text-[13px] font-semibold transition-colors cursor-pointer ${
                  viewMode === 'view_a'
                    ? 'bg-[#D4AF57] text-[#080808] shadow-xs'
                    : 'text-[#858585] hover:text-[#F2F2F2]'
                }`}
                title="View A: Primary complete record of all genuine batting innings"
              >
                <span>View A</span>
                <span className="hidden sm:inline">: All Innings</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('view_b')}
                className={`px-2.5 sm:px-3.5 py-1.5 rounded-md text-[12px] sm:text-[13px] font-semibold transition-colors cursor-pointer ${
                  viewMode === 'view_b'
                    ? 'bg-[#D4AF57] text-[#080808] shadow-xs'
                    : 'text-[#858585] hover:text-[#F2F2F2]'
                }`}
                title="View B: Qualified sensitivity view (excludes negligible cameos)"
              >
                <span>View B</span>
                <span className="hidden sm:inline">: Qualified</span>
                <span className="hidden md:inline"> Sensitivity</span>
              </button>
            </div>
          </div>
        </div>

        {/* Informational Context Bar */}
        <div className="px-4 sm:px-5 py-2.5 bg-[#121212] border-b border-[#2D2D2D] text-[12px] sm:text-[12.5px] font-normal text-[#858585] flex items-center gap-2">
          <Info className="w-4 h-4 text-[#D4AF57] shrink-0" />
          <span>
            <strong className="text-[#F2F2F2] font-semibold">Contextual Analytics:</strong> This analytical table evaluates performance against situational expectations. Par = 50.0.
          </span>
        </div>

        {/* Responsive Table */}
        <div className="overflow-x-auto w-full max-w-full min-w-0">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#2D2D2D] bg-[#161616] text-[#858585] font-semibold text-[12.5px] sm:text-[13px] tracking-wider sticky top-0 z-10">
                <th
                  onClick={() => handleSort('player')}
                  className="py-3.5 px-4 sm:px-5 cursor-pointer hover:text-[#F2F2F2] transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>PLAYER</span>
                    <ArrowUpDown className="w-3.5 h-3.5 text-[#858585]" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('team')}
                  className="py-3.5 px-3.5 cursor-pointer hover:text-[#F2F2F2] transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>TEAM</span>
                    <ArrowUpDown className="w-3.5 h-3.5 text-[#858585]" />
                  </div>
                </th>
                <th
                  className="py-3.5 px-3 text-center text-[#858585]"
                  title="Total match appearances in the selected season (Batting Innings + DNB)"
                >
                  <span>MATCHES</span>
                </th>
                <th
                  onClick={() =>
                    handleSort(
                      viewMode === 'view_a' ? 'batting_innings' : 'qualified_batting_innings'
                    )
                  }
                  className="py-3.5 px-3 text-center cursor-pointer hover:text-[#F2F2F2] transition-colors"
                  title="Number of actual batting opportunities evaluated in this season. Did Not Bat (DNB) is not treated as a zero contribution."
                >
                  <div className="flex items-center justify-center gap-1.5">
                    <span>BATTING INNINGS</span>
                    <ArrowUpDown className="w-3.5 h-3.5 text-[#858585]" />
                  </div>
                </th>
                <th
                  className="py-3.5 px-3 text-center text-[#858585]"
                  title="Did Not Bat appearances. Strictly excluded from the denominator to prevent artificial dilution."
                >
                  <span>DNB</span>
                </th>
                <th
                  onClick={() => handleSort('actual_runs')}
                  className="py-3.5 px-3.5 text-right cursor-pointer hover:text-[#F2F2F2] transition-colors"
                  title="Total runs scored across actual batting opportunities."
                >
                  <div className="flex items-center justify-end gap-1.5">
                    <span>RUNS</span>
                    <ArrowUpDown className="w-3.5 h-3.5 text-[#858585]" />
                  </div>
                </th>
                <th className="py-3.5 px-3 text-right text-[#858585]" title="Total balls faced by the batter.">
                  BALLS
                </th>
                <th
                  onClick={() => handleSort('strike_rate')}
                  className="py-3.5 px-3 text-right cursor-pointer hover:text-[#F2F2F2] transition-colors"
                  title="Batting strike rate (runs per 100 balls faced)."
                >
                  <div className="flex items-center justify-end gap-1.5">
                    <span>SR</span>
                    <ArrowUpDown className="w-3.5 h-3.5 text-[#858585]" />
                  </div>
                </th>
                <th
                  onClick={() =>
                    handleSort(
                      viewMode === 'view_a'
                        ? 'average_contribution_score'
                        : 'qualified_average_contribution_score'
                    )
                  }
                  className="py-3.5 px-4 sm:px-5 text-center cursor-pointer hover:text-[#F2F2F2] transition-colors"
                  title="Overall contribution for a batting opportunity. 50 represents the model's par benchmark. Average Contribution Score across actual batting opportunities."
                >
                  <div className="flex items-center justify-center gap-1.5">
                    <span>AVG CONTRIBUTION</span>
                    <ArrowUpDown className="w-3.5 h-3.5 text-[#858585]" />
                  </div>
                </th>
                <th
                  onClick={() =>
                    handleSort(
                      viewMode === 'view_a'
                        ? 'total_positive_raw_contribution'
                        : 'qualified_total_positive_contribution'
                    )
                  }
                  className="py-3.5 px-3.5 text-right cursor-pointer hover:text-[#F2F2F2] transition-colors"
                  title="Positive portion of the player's underlying raw contribution. It is not runs scored."
                >
                  <div className="flex items-center justify-end gap-1.5">
                    <span>POSITIVE CONTRIBUTION</span>
                    <ArrowUpDown className="w-3.5 h-3.5 text-[#858585]" />
                  </div>
                </th>
                <th
                  onClick={() =>
                    handleSort(
                      viewMode === 'view_a'
                        ? 'season_team_contribution_share'
                        : 'qualified_team_contribution_share'
                    )
                  }
                  className="py-3.5 px-3.5 text-right cursor-pointer hover:text-[#F2F2F2] transition-colors"
                  title="Player's share of the team's total positive model contribution. It is not a share of team runs."
                >
                  <div className="flex items-center justify-end gap-1.5">
                    <span>TEAM SHARE</span>
                    <ArrowUpDown className="w-3.5 h-3.5 text-[#858585]" />
                  </div>
                </th>
                <th className="py-3.5 px-4 text-center text-[#858585]">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#222222] text-[#F2F2F2] text-[13.5px] sm:text-[14px] font-normal font-sans">
              {loading ? (
                Array.from({ length: 6 }).map((_, idx) => (
                  <tr key={`skel-p-${idx}`} className="animate-pulse">
                    <td className="py-4 px-4 sm:px-5">
                      <div className="skeleton h-4 w-32 rounded" />
                    </td>
                    <td className="py-4 px-3.5">
                      <div className="skeleton h-4 w-12 rounded" />
                    </td>
                    <td className="py-4 px-3 text-center">
                      <div className="skeleton h-4 w-8 mx-auto rounded" />
                    </td>
                    <td className="py-4 px-3 text-center">
                      <div className="skeleton h-4 w-8 mx-auto rounded" />
                    </td>
                    <td className="py-4 px-3 text-center">
                      <div className="skeleton h-4 w-12 mx-auto rounded-full" />
                    </td>
                    <td className="py-4 px-3.5 text-right">
                      <div className="skeleton h-4 w-10 ml-auto rounded" />
                    </td>
                    <td className="py-4 px-3 text-right">
                      <div className="skeleton h-4 w-10 ml-auto rounded" />
                    </td>
                    <td className="py-4 px-3 text-right">
                      <div className="skeleton h-4 w-12 ml-auto rounded" />
                    </td>
                    <td className="py-4 px-4 sm:px-5 text-center">
                      <div className="skeleton h-6 w-14 mx-auto rounded-full" />
                    </td>
                    <td className="py-4 px-3.5 text-right">
                      <div className="skeleton h-4 w-12 ml-auto rounded" />
                    </td>
                    <td className="py-4 px-3.5 text-right">
                      <div className="skeleton h-4 w-12 ml-auto rounded" />
                    </td>
                    <td className="py-4 px-4 text-center">
                      <div className="skeleton h-6 w-20 mx-auto rounded" />
                    </td>
                  </tr>
                ))
              ) : sortedPlayers.length === 0 ? (
                <tr>
                  <td colSpan="12" className="py-16 text-center">
                    <div className="max-w-md mx-auto space-y-3">
                      <div className="w-12 h-12 rounded-full bg-[#1A1A1A] border border-[#2D2D2D] flex items-center justify-center mx-auto text-[#D4AF57]">
                        <Users className="w-6 h-6" />
                      </div>
                      <div className="text-[16px] font-semibold text-[#F2F2F2]">No Batters Found</div>
                      <p className="text-[13px] text-[#858585]">
                        No players matched your filter criteria ({selectedTeam || 'All Teams'}, {minRuns > 0 ? `Min ${minRuns} runs` : 'Any runs'}{searchQuery ? `, "${searchQuery}"` : ''}).
                      </p>
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedTeam('');
                          setMinRuns(0);
                          setSearchQuery('');
                          setCurrentPage(1);
                        }}
                        className="btn-secondary text-[12.5px] py-1.5 px-4 cursor-pointer inline-flex items-center gap-1.5"
                      >
                        Reset Filters
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                paginatedPlayers.map((p) => {
                  const score =
                    viewMode === 'view_a'
                      ? p.average_contribution_score
                      : p.qualified_average_contribution_score;
                  const posContrib =
                    viewMode === 'view_a'
                      ? p.total_positive_raw_contribution
                      : p.qualified_total_positive_contribution;
                  const teamShare =
                    viewMode === 'view_a'
                      ? p.season_team_contribution_share
                      : p.qualified_team_contribution_share;
                  const innings =
                    viewMode === 'view_a'
                      ? p.batting_innings
                      : p.qualified_batting_innings;
                  const sr =
                    p.balls_faced > 0 ? ((p.actual_runs / p.balls_faced) * 100).toFixed(1) : '—';
                  const matches =
                    p.matches_played || (p.batting_innings + (p.did_not_bat_matches || 0));

                  let scoreBadge = 'bg-[#101010] text-[#858585] border-[#2D2D2D]';
                  if (score !== null && score !== undefined) {
                    if (score >= 65)
                      scoreBadge = 'bg-[#152718] text-[#5A9E60] border-[#2A4D30] font-bold';
                    else if (score >= 52)
                      scoreBadge = 'bg-[#152718] text-[#5A9E60] border-[#2A4D30]/60 font-semibold';
                    else if (score >= 48)
                      scoreBadge = 'bg-[#1F1C14] text-[#D4AF57] border-[#A8893D]/40 font-medium';
                    else
                      scoreBadge = 'bg-[#271414] text-[#C25454] border-[#4D2626] font-semibold';
                  }

                  return (
                    <tr
                      key={`${p.player}-${p.season}-${p.team}`}
                      onClick={() =>
                        navigate(`/player/${encodeURIComponent(p.player)}/${selectedSeason}`)
                      }
                      className="cursor-pointer transition-colors hover:bg-[#1A1A1A]"
                    >
                      {/* Player */}
                      <td className="py-3.5 px-4 sm:px-5 whitespace-nowrap">
                        <span className="font-semibold text-[14.5px] text-[#F2F2F2] hover:text-[#D4AF57] transition-colors">
                          {p.player}
                        </span>
                        {p.not_outs > 0 && (
                          <span className="text-[12px] font-normal text-[#858585] ml-1.5 font-sans">
                            ({p.not_outs} NO)
                          </span>
                        )}
                      </td>

                      {/* Team */}
                      <td className="py-3.5 px-3.5 whitespace-nowrap text-[#B8B8B8] text-[13.5px]">{p.team}</td>

                      {/* Matches */}
                      <td className="py-3.5 px-3 text-center whitespace-nowrap text-[#B8B8B8] tabular-nums">
                        {matches}
                      </td>

                      {/* Batting Innings */}
                      <td className="py-3.5 px-3 text-center whitespace-nowrap font-medium text-[#F2F2F2] tabular-nums">
                        {innings}
                      </td>

                      {/* DNB Matches */}
                      <td className="py-3.5 px-3 text-center whitespace-nowrap tabular-nums">
                        {p.did_not_bat_matches > 0 ? (
                          <span className="badge-dnb">
                            {p.did_not_bat_matches} DNB
                          </span>
                        ) : (
                          <span className="text-[#555555]">0</span>
                        )}
                      </td>

                      {/* Actual Runs */}
                      <td className="py-3.5 px-3.5 text-right font-medium tabular-nums whitespace-nowrap text-[#F2F2F2]">
                        {p.actual_runs}
                      </td>

                      {/* Balls Faced */}
                      <td className="py-3.5 px-3 text-right whitespace-nowrap text-[#858585] tabular-nums">
                        {p.balls_faced}
                      </td>

                      {/* Strike Rate */}
                      <td className="py-3.5 px-3 text-right whitespace-nowrap text-[#B8B8B8] tabular-nums">
                        {sr}
                      </td>

                      {/* Contribution Score */}
                      <td className="py-3.5 px-4 sm:px-5 text-center whitespace-nowrap">
                        {score !== null && score !== undefined ? (
                          <span
                            className={`inline-block px-3 py-1 rounded-full text-[13px] border tabular-nums ${scoreBadge}`}
                          >
                            {Number(score).toFixed(1)}
                          </span>
                        ) : (
                          <span className="text-[12px] text-[#858585] font-medium px-2.5 py-0.5 rounded bg-[#101010] border border-[#2D2D2D]">
                            —
                          </span>
                        )}
                      </td>

                      {/* Positive Raw Contribution */}
                      <td className="py-3.5 px-3.5 text-right whitespace-nowrap tabular-nums text-[#5A9E60] font-medium">
                        {posContrib !== null ? Number(posContrib).toFixed(2) : '—'}
                      </td>

                      {/* Team Contribution Share */}
                      <td className="py-3.5 px-3.5 text-right whitespace-nowrap tabular-nums text-[#F2F2F2]">
                        {teamShare !== null ? `${Number(teamShare).toFixed(1)}%` : '—'}
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-4 text-center whitespace-nowrap">
                        <div className="flex items-center justify-center gap-2">
                          <Link
                            to={`/player/${encodeURIComponent(p.player)}/${selectedSeason}`}
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-[13px] text-[#D4AF57] hover:text-[#E1C878] font-semibold hover:underline px-1.5 py-0.5"
                            title="Open Player Profile"
                          >
                            <span>Analyze</span>
                            <ExternalLink className="w-3.5 h-3.5" />
                          </Link>

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleToggleCompare(p.player);
                            }}
                            className={`inline-flex items-center gap-1 text-[12.5px] px-2.5 py-1 rounded-md font-semibold transition-all cursor-pointer ${
                              selectedForCompare.includes(p.player)
                                ? 'bg-[#D4AF57] text-[#080808] shadow-xs'
                                : 'bg-[#101010] text-[#B8B8B8] border border-[#2D2D2D] hover:text-[#F2F2F2] hover:border-[#D4AF57]/40'
                            }`}
                            title={
                              selectedForCompare.includes(p.player)
                                ? 'Remove from comparison'
                                : 'Add to player comparison (max 5)'
                            }
                          >
                            {selectedForCompare.includes(p.player) ? '✓ Compare' : '+ Compare'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {sortedPlayers.length > 0 && (
          <div className="p-4 sm:p-5 border-t border-[#2D2D2D] bg-[#101010] flex flex-col sm:flex-row items-center justify-between gap-3 text-[13px]">
            <div className="flex items-center gap-3 text-[#858585]">
              <span>
                Showing{' '}
                <strong className="text-[#F2F2F2] font-semibold">
                  {pageSize === 'all'
                    ? 1
                    : Math.min((currentPage - 1) * Number(pageSize) + 1, sortedPlayers.length)}
                </strong>{' '}
                to{' '}
                <strong className="text-[#F2F2F2] font-semibold">
                  {pageSize === 'all'
                    ? sortedPlayers.length
                    : Math.min(currentPage * Number(pageSize), sortedPlayers.length)}
                </strong>{' '}
                of <strong className="text-[#D4AF57] font-semibold">{sortedPlayers.length}</strong> players
              </span>

              <div className="flex items-center gap-2 ml-3">
                <span className="text-[#858585]">Rows:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(e.target.value === 'all' ? 'all' : Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-[#161616] text-[#F2F2F2] border border-[#2D2D2D] rounded-md px-2.5 py-1 text-[12px] focus:outline-none focus:border-[#D4AF57]"
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value="all">All</option>
                </select>
              </div>
            </div>

            {pageSize !== 'all' && totalPages > 1 && (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded-lg bg-[#161616] border border-[#2D2D2D] text-[#858585] hover:text-[#F2F2F2] hover:border-[#D4AF57]/40 disabled:opacity-40 disabled:pointer-events-none transition-colors cursor-pointer"
                  title="Previous page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                <div className="px-3 py-1 rounded-lg bg-[#161616] border border-[#2D2D2D] text-[12px] text-[#858585]">
                  Page <strong className="text-[#F2F2F2]">{currentPage}</strong> of{' '}
                  <strong className="text-[#F2F2F2]">{totalPages}</strong>
                </div>

                <button
                  type="button"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-2 rounded-lg bg-[#161616] border border-[#2D2D2D] text-[#858585] hover:text-[#F2F2F2] hover:border-[#D4AF57]/40 disabled:opacity-40 disabled:pointer-events-none transition-colors cursor-pointer"
                  title="Next page"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Floating Player Comparison Tray */}
      {selectedForCompare.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 w-11/12 max-w-4xl bg-[#161616] border border-[#2D2D2D] rounded-xl shadow-2xl p-4 transition-all">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[12px] font-semibold text-[#D4AF57] mr-1">
                {selectedForCompare.length} / 5 Selected:
              </span>
              {selectedForCompare.map((name) => (
                <span
                  key={name}
                  className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[12px] font-medium bg-[#101010] text-[#F2F2F2] border border-[#2D2D2D]"
                >
                  <span>{name}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveCompare(name)}
                    className="p-0.5 rounded-full hover:bg-[#2D2D2D] text-[#858585] hover:text-[#F2F2F2] transition-colors"
                    title={`Remove ${name}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>

            <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
              <button
                type="button"
                onClick={() => setSelectedForCompare([])}
                className="text-[12px] font-normal text-[#858585] hover:text-[#F2F2F2] underline px-2 py-1 cursor-pointer"
              >
                Clear
              </button>

              {selectedForCompare.length >= 2 ? (
                <button
                  type="button"
                  onClick={() =>
                    navigate(
                      `/compare?season=${selectedSeason}&players=${encodeURIComponent(
                        selectedForCompare.join(',')
                      )}&view=${viewMode}`
                    )
                  }
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-[12px] font-semibold bg-[#D4AF57] hover:bg-[#E1C878] text-[#080808] shadow-xs transition-all cursor-pointer whitespace-nowrap"
                >
                  <Users className="w-3.5 h-3.5" />
                  <span>Compare {selectedForCompare.length} Players</span>
                </button>
              ) : (
                <span className="text-[12px] font-medium text-[#858585] bg-[#101010] px-2.5 py-1 rounded border border-[#2D2D2D]">
                  Select at least 2 players
                </span>
              )}
            </div>
          </div>

          {compareWarning && (
            <div className="mt-1.5 text-center text-[12px] font-semibold text-[#C25454]">
              {compareWarning}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
