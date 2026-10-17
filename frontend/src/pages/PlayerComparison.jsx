import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Users,
  Search,
  X,
  Info,
  ExternalLink,
} from 'lucide-react';
import FourPillarComparisonChart from '../components/Charts/FourPillarComparisonChart';
import PrimaryMetricsComparisonChart from '../components/Charts/PrimaryMetricsComparisonChart';
import Breadcrumbs from '../components/Breadcrumbs';
import { getSeasons, getTeams, getPlayers, comparePlayers } from '../services/api';
import { useCompetition, TOURNAMENT_TYPES, resolveDefaultSeason } from '../context/CompetitionContext';

export default function PlayerComparison() {
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    competition,
    activeMeta,
    tournamentType,
    setTournamentType,
    selectedSeason: globalSeason,
    setSelectedSeason: setGlobalSeason,
  } = useCompetition();

  // URL State
  const seasonParam = searchParams.get('season') || '';
  const playersParam = searchParams.get('players') || '';
  const viewParam = searchParams.get('view') || 'view_a';

  // Local State
  const [seasons, setSeasons] = useState([]);
  const [seasonOptions, setSeasonOptions] = useState([]);
  const [selectedSeason, setSelectedSeason] = useState(seasonParam || globalSeason || '');
  const [viewMode, setViewMode] = useState(viewParam);
  const [selectedPlayers, setSelectedPlayers] = useState(
    playersParam ? playersParam.split(',').map((p) => p.trim()).filter(Boolean) : []
  );

  // Filter Integration States
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState('');
  const [minRuns, setMinRuns] = useState(0);
  const [minInnings, setMinInnings] = useState(0);
  const [minBalls, setMinBalls] = useState(0);

  // Available players pool for current season
  const [availablePlayers, setAvailablePlayers] = useState([]);
  const [playerSearch, setPlayerSearch] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const dropdownRef = useRef(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Comparison Results
  const [comparisonData, setComparisonData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [limitWarning, setLimitWarning] = useState('');

  // 1. Load seasons on mount or when competition/tournamentType changes
  useEffect(() => {
    async function loadSeasons() {
      try {
        const data = await getSeasons(competition, tournamentType);
        const availSeasons = data.seasons || [];
        setSeasons(availSeasons);
        setSeasonOptions(data.season_options || []);

        setSelectedSeason((curr) => {
          const candidate = curr || globalSeason;
          if (candidate && availSeasons.includes(candidate)) {
            return candidate;
          }
          return resolveDefaultSeason(availSeasons, data.default_season);
        });
        setSelectedPlayers([]);
      } catch (err) {
        setError(err.message);
      }
    }
    loadSeasons();
  }, [competition, tournamentType, globalSeason]);

  // 2. Load teams when season, competition, or tournamentType changes
  useEffect(() => {
    if (!selectedSeason) return;
    async function loadTeamsList() {
      try {
        const data = await getTeams(selectedSeason, competition, tournamentType);
        setTeams(data.teams || []);
      } catch {
        // non-blocking
      }
    }
    loadTeamsList();
  }, [selectedSeason, competition, tournamentType]);

  // 3. Load available players when season, competition or filters change
  useEffect(() => {
    if (!selectedSeason) return;

    async function loadSeasonPlayers() {
      try {
        const data = await getPlayers({
          season: selectedSeason,
          team: selectedTeam || undefined,
          minRuns: minRuns ? Number(minRuns) : undefined,
          minInnings: minInnings ? Number(minInnings) : undefined,
          minBalls: minBalls ? Number(minBalls) : undefined,
          limit: 1000,
          competition,
          tournamentType,
        });
        setAvailablePlayers(data.players || []);
      } catch {
        // non-blocking
      }
    }
    loadSeasonPlayers();
  }, [selectedSeason, selectedTeam, minRuns, minInnings, minBalls, competition, tournamentType]);

  // 4. Keep URL query in sync
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedSeason) params.set('season', selectedSeason);
    if (selectedPlayers.length > 0) params.set('players', selectedPlayers.join(','));
    if (viewMode) params.set('view', viewMode);
    setSearchParams(params, { replace: true });
  }, [selectedSeason, selectedPlayers, viewMode, setSearchParams]);

  // 5. Fetch comparison data when players (>=2) or season or viewMode change
  useEffect(() => {
    if (!selectedSeason || selectedPlayers.length < 2) {
      return;
    }

    let isMounted = true;
    async function fetchComparison() {
      setLoading(true);
      setError(null);
      try {
        const res = await comparePlayers({
          season: selectedSeason,
          players: selectedPlayers,
          view: viewMode,
          competition,
          tournamentType,
        });
        if (isMounted) {
          setComparisonData(res);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      }
    }

    fetchComparison();
    return () => {
      isMounted = false;
    };
  }, [selectedSeason, selectedPlayers, viewMode, competition, tournamentType]);

  // Add a player to comparison (max 5)
  const addPlayer = (playerName) => {
    setLimitWarning('');
    if (selectedPlayers.includes(playerName)) {
      return;
    }
    if (selectedPlayers.length >= 5) {
      setLimitWarning('Maximum 5 players can be compared.');
      return;
    }
    setSelectedPlayers((prev) => [...prev, playerName]);
    setPlayerSearch('');
    setIsDropdownOpen(false);
  };

  // Remove player
  const removePlayer = (playerName) => {
    setLimitWarning('');
    setSelectedPlayers((prev) => prev.filter((p) => p !== playerName));
  };

  // Filtered dropdown options
  const filteredDropdownPlayers = useMemo(() => {
    const q = playerSearch.trim().toLowerCase();
    return availablePlayers
      .filter((p) => !selectedPlayers.includes(p.player))
      .filter((p) => !q || p.player.toLowerCase().includes(q))
      .slice(0, 15);
  }, [availablePlayers, selectedPlayers, playerSearch]);

  const playersList = comparisonData?.players || [];
  const obs = comparisonData?.analytical_observations;

  return (
    <div className="w-full space-y-8 font-sans text-[#F2F2F2]">
      {/* Top Breadcrumb & Title */}
      <Breadcrumbs
        items={[
          { to: '/dashboard', label: 'Dashboard' },
          { label: 'Player Contribution Comparison' },
        ]}
        backTo="/dashboard"
        backLabel="Back to Dashboard"
      />

      <div className="border-b border-[#2D2D2D] pb-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="font-heading text-[22px] sm:text-[30px] lg:text-[36px] font-bold text-[#F2F2F2] tracking-wide leading-tight break-words">
              Player Contribution Comparison
            </h1>
            <p className="text-[14px] sm:text-[16px] font-normal text-[#B8B8B8] mt-1.5 max-w-5xl leading-relaxed">
              Side-by-side contextual evaluation of 2 to 5 batters within {activeMeta?.name || 'the same season'}. Contribution is not simply runs or strike rate.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto font-sans">
            <span className="px-3.5 py-1.5 rounded-lg text-[13px] font-medium bg-[#161616] text-[#D4AF57] border border-[#2D2D2D]">
              {selectedPlayers.length} Selected
            </span>
          </div>
        </div>
      </div>

      {/* Selector & Season Filter Bar */}
      <div className="bg-[#161616] rounded-xl p-4 sm:p-5 border border-[#2D2D2D] space-y-4">
        <div className={`grid grid-cols-1 ${competition === 't20i' ? 'md:grid-cols-4' : 'md:grid-cols-3'} gap-4 items-center`}>
          {/* Tournament Type Selector (if t20i) */}
          {competition === 't20i' && (
            <div>
              <label className="block text-[12.5px] sm:text-[13px] font-semibold text-[#D4AF57] uppercase tracking-wider mb-1.5">
                Tournament Type
              </label>
              <select
                value={tournamentType}
                onChange={(e) => setTournamentType(e.target.value)}
                className="w-full bg-[#101010] border border-[#A8893D]/60 rounded-lg px-3.5 py-2 text-[13.5px] sm:text-[14px] font-semibold text-[#F2F2F2] focus:outline-hidden focus:border-[#D4AF57] cursor-pointer"
              >
                {TOURNAMENT_TYPES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Season Selector */}
          <div>
            <label className="block text-[12.5px] sm:text-[13px] font-semibold text-[#858585] uppercase tracking-wider mb-1.5">
              {competition === 't20i' && (tournamentType === 'world_cup' || tournamentType === 'asia_cup')
                ? 'Edition / Year'
                : 'Comparison Season'}
            </label>
            <select
              value={selectedSeason}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedSeason(val);
                setGlobalSeason(val);
                setSelectedPlayers([]);
                setComparisonData(null);
              }}
              className="w-full bg-[#101010] border border-[#2D2D2D] rounded-lg px-3.5 py-2 text-[13.5px] sm:text-[14px] font-semibold text-[#F2F2F2] focus:outline-hidden focus:border-[#D4AF57] cursor-pointer"
            >
              {seasonOptions.length > 0 ? (
                seasonOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))
              ) : (
                seasons.map((s) => (
                  <option key={s} value={s}>
                    {competition === 't20i' ? s : `${s} Season`}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Add Player Search Input */}
          <div ref={dropdownRef} className="md:col-span-2 relative">
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-[12.5px] sm:text-[13px] font-semibold text-[#858585] uppercase tracking-wider">
                Select Batters to Compare
              </label>
              <span className={`text-[12.5px] font-bold tabular-nums ${selectedPlayers.length === 5 ? 'text-[#D4AF57]' : 'text-[#858585]'}`}>
                {selectedPlayers.length} / 5 selected
              </span>
            </div>

            <div className="relative">
              <Search className="w-4 h-4 text-[#858585] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                placeholder={
                  selectedPlayers.length >= 5
                    ? 'Maximum 5 players selected'
                    : 'Search batter by name to add (e.g. Kohli, Head, Klaasen)...'
                }
                disabled={selectedPlayers.length >= 5}
                value={playerSearch}
                onChange={(e) => {
                  setPlayerSearch(e.target.value);
                  setIsDropdownOpen(true);
                  setHighlightedIndex(-1);
                }}
                onFocus={() => {
                  setIsDropdownOpen(true);
                  setHighlightedIndex(-1);
                }}
                onKeyDown={(e) => {
                  if (!isDropdownOpen || filteredDropdownPlayers.length === 0) return;
                  if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    setHighlightedIndex((prev) =>
                      prev < filteredDropdownPlayers.length - 1 ? prev + 1 : 0
                    );
                  } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    setHighlightedIndex((prev) =>
                      prev > 0 ? prev - 1 : filteredDropdownPlayers.length - 1
                    );
                  } else if (e.key === 'Enter') {
                    e.preventDefault();
                    const target =
                      highlightedIndex >= 0
                        ? filteredDropdownPlayers[highlightedIndex]
                        : filteredDropdownPlayers[0];
                    if (target) {
                      addPlayer(target.player);
                      setIsDropdownOpen(false);
                    }
                  } else if (e.key === 'Escape') {
                    e.preventDefault();
                    setIsDropdownOpen(false);
                  }
                }}
                className="w-full bg-[#101010] border border-[#2D2D2D] rounded-lg pl-10 pr-3.5 py-2 text-[13.5px] sm:text-[14px] text-[#F2F2F2] placeholder-[#858585] focus:outline-hidden focus:border-[#D4AF57] disabled:opacity-50"
              />
            </div>

            {/* Dropdown Suggestions */}
            {isDropdownOpen && selectedPlayers.length < 5 && filteredDropdownPlayers.length > 0 && (
              <div className="absolute left-0 right-0 top-full mt-1.5 bg-[#161616] border border-[#2D2D2D] rounded-xl shadow-2xl z-30 max-h-60 overflow-y-auto divide-y divide-[#2D2D2D]">
                {filteredDropdownPlayers.map((p, idx) => {
                  const isHighlighted = idx === highlightedIndex;
                  return (
                    <button
                      key={`${p.player}-${p.team}`}
                      type="button"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => addPlayer(p.player)}
                      onMouseEnter={() => setHighlightedIndex(idx)}
                      className={`w-full px-4 py-3 text-left flex items-center justify-between transition-colors cursor-pointer text-[13.5px] ${
                        isHighlighted ? 'bg-[#252525] ring-1 ring-[#D4AF57]/40' : 'hover:bg-[#202020]'
                      }`}
                    >
                      <div>
                        <span className="font-bold text-[#F2F2F2]">{p.player}</span>
                        <span className="text-[#858585] ml-2 font-medium">({p.team})</span>
                      </div>
                      <div className="text-right text-[#858585]">
                        <span>{p.actual_runs} runs</span>
                        <span className="text-[#D4AF57] ml-2 font-bold tabular-nums">
                          Score: {p.average_contribution_score !== null ? Number(p.average_contribution_score).toFixed(1) : '—'}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Player Pool Filters */}
        <div className="pt-3 border-t border-[#2D2D2D] grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <label className="block text-[11.5px] sm:text-[12px] font-semibold text-[#858585] uppercase tracking-wider mb-1">
              Filter by Team
            </label>
            <select
              value={selectedTeam}
              onChange={(e) => setSelectedTeam(e.target.value)}
              className="w-full bg-[#101010] border border-[#2D2D2D] rounded-lg px-3 py-1.5 text-[12.5px] sm:text-[13px] text-[#F2F2F2] focus:outline-hidden focus:border-[#D4AF57] cursor-pointer"
            >
              <option value="">All Teams ({availablePlayers.length})</option>
              {teams.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11.5px] sm:text-[12px] font-semibold text-[#858585] uppercase tracking-wider mb-1">
              Min Runs
            </label>
            <select
              value={minRuns}
              onChange={(e) => setMinRuns(Number(e.target.value))}
              className="w-full bg-[#101010] border border-[#2D2D2D] rounded-lg px-3 py-1.5 text-[12.5px] sm:text-[13px] text-[#F2F2F2] focus:outline-hidden focus:border-[#D4AF57] cursor-pointer"
            >
              <option value={0}>Any Runs (0+)</option>
              <option value={100}>100+ Runs</option>
              <option value={200}>200+ Runs</option>
              <option value={300}>300+ Runs</option>
              <option value={400}>400+ Runs</option>
              <option value={500}>500+ Runs</option>
            </select>
          </div>

          <div>
            <label className="block text-[11.5px] sm:text-[12px] font-semibold text-[#858585] uppercase tracking-wider mb-1">
              Min Innings
            </label>
            <select
              value={minInnings}
              onChange={(e) => setMinInnings(Number(e.target.value))}
              className="w-full bg-[#101010] border border-[#2D2D2D] rounded-lg px-3 py-1.5 text-[12.5px] sm:text-[13px] text-[#F2F2F2] focus:outline-hidden focus:border-[#D4AF57] cursor-pointer"
            >
              <option value={0}>Any Innings</option>
              <option value={3}>3+ Innings</option>
              <option value={5}>5+ Innings</option>
              <option value={10}>10+ Innings</option>
            </select>
          </div>

          <div>
            <label className="block text-[11.5px] sm:text-[12px] font-semibold text-[#858585] uppercase tracking-wider mb-1">
              Min Balls
            </label>
            <div className="flex items-center gap-1.5">
              <select
                value={minBalls}
                onChange={(e) => setMinBalls(Number(e.target.value))}
                className="w-full bg-[#101010] border border-[#2D2D2D] rounded-lg px-3 py-1.5 text-[12.5px] sm:text-[13px] text-[#F2F2F2] focus:outline-hidden focus:border-[#D4AF57] cursor-pointer"
              >
                <option value={0}>Any Balls</option>
                <option value={50}>50+ Balls</option>
                <option value={100}>100+ Balls</option>
                <option value={200}>200+ Balls</option>
              </select>

              {(selectedTeam || minRuns > 0 || minInnings > 0 || minBalls > 0) && (
                <button
                  type="button"
                  onClick={() => {
                    setSelectedTeam('');
                    setMinRuns(0);
                    setMinInnings(0);
                    setMinBalls(0);
                  }}
                  className="px-2 py-1 text-[11px] rounded bg-[#101010] text-[#858585] hover:text-[#F2F2F2] border border-[#2D2D2D] whitespace-nowrap cursor-pointer transition-colors"
                  title="Clear pool filters"
                >
                  Reset
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Selected Player Chips */}
        <div className="pt-3 border-t border-[#2D2D2D] flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-semibold text-[#858585] uppercase tracking-wider mr-1">
              Active:
            </span>
            {selectedPlayers.length === 0 ? (
              <span className="text-xs text-[#858585] italic">No players selected yet.</span>
            ) : (
              selectedPlayers.map((p) => (
                <span
                  key={p}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs font-bold bg-[#101010] text-[#F2F2F2] border border-[#2D2D2D]"
                >
                  <span>{p}</span>
                  <button
                    type="button"
                    onClick={() => removePlayer(p)}
                    className="p-0.5 rounded hover:bg-[#202020] text-[#858585] hover:text-[#D4AF57] transition-colors cursor-pointer"
                    title={`Remove ${p}`}
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </span>
              ))
            )}
          </div>

          {/* View A vs View B Toggle */}
          <div className="inline-flex rounded-lg bg-[#101010] p-1 border border-[#2D2D2D] max-w-full">
            <button
              onClick={() => setViewMode('view_a')}
              className={`px-2.5 sm:px-3 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
                viewMode === 'view_a'
                  ? 'bg-[#D4AF57] text-[#080808] font-bold'
                  : 'text-[#B8B8B8] hover:text-[#F2F2F2]'
              }`}
            >
              <span>View A</span>
              <span className="hidden sm:inline">: All Innings</span>
            </button>
            <button
              onClick={() => setViewMode('view_b')}
              className={`px-2.5 sm:px-3 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
                viewMode === 'view_b'
                  ? 'bg-[#D4AF57] text-[#080808] font-bold'
                  : 'text-[#B8B8B8] hover:text-[#F2F2F2]'
              }`}
            >
              <span>View B</span>
              <span className="hidden sm:inline">: Qualified</span>
            </button>
          </div>
        </div>

        {limitWarning && (
          <div className="p-3 rounded-lg bg-[#271414] border border-[#4D2626] text-[#C25454] text-xs">
            {limitWarning}
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-[#271414] border border-[#4D2626] text-[#C25454] text-xs">
          {error}
        </div>
      )}

      {/* When fewer than 2 players are selected */}
      {selectedPlayers.length < 2 && (
        <div className="bg-[#161616] rounded-xl p-12 border border-[#2D2D2D] text-center space-y-3">
          <div className="w-10 h-10 rounded-xl bg-[#101010] border border-[#2D2D2D] mx-auto flex items-center justify-center text-[#D4AF57]">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-[#F2F2F2]">Select at Least 2 Players to Compare</h2>
            <p className="text-xs text-[#858585] max-w-md mx-auto mt-1 leading-relaxed">
              Use the player search above or click "[+ Compare]" on any player row in the Season Dashboard table.
            </p>
          </div>
          <div className="pt-2">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#101010] hover:bg-[#202020] text-xs font-semibold text-[#F2F2F2] border border-[#2D2D2D] transition-colors"
            >
              Browse Season Players
            </Link>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && selectedPlayers.length >= 2 && (
        <div className="py-16 text-center text-[#858585]">
          <div className="text-xs font-medium">Loading multi-player comparison...</div>
        </div>
      )}

      {/* Comparison Results */}
      {!loading && comparisonData && playersList.length >= 2 && (
        <div className="space-y-6">
          {/* Section 11 Core Message: "Contribution is not simply runs or strike rate" */}
          <div className="bg-[#161616] rounded-xl p-5 sm:p-6 border border-[#D4AF57]/30 space-y-3">
            <div className="flex items-center gap-2.5">
              <Info className="w-5 h-5 text-[#D4AF57]" />
              <h3 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2]">
                Key analytical principle: Contribution ≠ runs or strike rate
              </h3>
            </div>
            <p className="text-[15px] sm:text-[16px] font-normal text-[#B8B8B8] leading-relaxed">
              Batters accumulate volume differently depending on batting position, match situation, and chase demands. The Contribution Model evaluates what each run was worth in context, how team win trajectory changed, and whether performance met situational expectations.
            </p>
          </div>

          {/* Analytical Observations Summary */}
          {obs && (
            <div className="bg-[#161616] rounded-xl p-6 sm:p-7 border border-[#2D2D2D] space-y-4">
              <div className="flex items-center gap-2.5 mb-1">
                <Info className="w-5 h-5 text-[#D4AF57]" />
                <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2]">
                  Comparative dimension leaders
                </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                {obs.dimensions &&
                  obs.dimensions.map((dim, idx) => (
                    <div
                      key={idx}
                      className="bg-[#101010] rounded-xl p-5 border border-[#2D2D2D] flex flex-col justify-between"
                    >
                      <div>
                        <div className="text-[12px] sm:text-[12.5px] font-semibold text-[#858585] uppercase tracking-wider mb-1.5">
                          {dim.dimension}
                        </div>
                        <div className="text-[15px] sm:text-[16px] font-bold text-[#F2F2F2]">
                          Leader: <span className="text-[#D4AF57] font-semibold">{dim.leader}</span>
                        </div>
                        <div className="text-[13px] sm:text-[13.5px] font-normal text-[#B8B8B8] mt-2.5 leading-relaxed">
                          {dim.observation}
                        </div>
                      </div>
                      <div className="mt-4 pt-3 border-t border-[#2D2D2D] text-right">
                        <span className="text-[22px] sm:text-[26px] font-bold text-[#F2F2F2] tabular-nums font-sans">
                          {dim.value !== null ? Number(dim.value).toFixed(dim.unit.includes('%') ? 1 : 2) : '—'}
                        </span>
                        <span className="text-[13px] text-[#858585] ml-1.5">{dim.unit}</span>
                      </div>
                    </div>
                  ))}
              </div>

              <div className="p-4 bg-[#101010] rounded-xl border border-[#2D2D2D] text-[13px] sm:text-[13.5px] font-normal text-[#B8B8B8] leading-relaxed">
                <strong className="text-[#F2F2F2] font-semibold">Methodological note:</strong> {obs.summary_note}
              </div>
            </div>
          )}

          {/* Primary Side-by-Side Comparison Table */}
          <div className="bg-[#161616] rounded-xl border border-[#2D2D2D] overflow-hidden">
            <div className="p-5 sm:p-6 border-b border-[#2D2D2D] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2]">
                  Side-by-side dimension table
                </h2>
                <p className="text-[13px] sm:text-[13.5px] font-normal text-[#858585] mt-1">
                  Direct comparison across volume, contextual contribution, and scoring pillars.
                </p>
              </div>
              <span className="text-[12.5px] sm:text-[13px] font-medium text-[#B8B8B8] bg-[#101010] px-3.5 py-1.5 rounded-lg border border-[#2D2D2D]">
                {playersList.length} Batters Compared
              </span>
            </div>

            <div className="overflow-x-auto max-w-full">
              <table className="w-full text-left border-collapse text-[14px] sm:text-[14.5px] font-sans">
                <thead>
                  <tr className="border-b border-[#2D2D2D] bg-[#161616] text-[#858585]">
                    <th className="py-3.5 px-4 font-semibold text-[#858585] text-[12.5px] sm:text-[13px] uppercase tracking-wider sticky left-0 bg-[#161616] z-10 min-w-[220px]">
                      Metric / Dimension
                    </th>
                    {playersList.map((p) => (
                      <th
                        key={p.player}
                        className="py-3.5 px-4 text-center text-[#F2F2F2] min-w-[170px]"
                      >
                        <div className="font-semibold text-[15px] text-[#F2F2F2]">{p.player}</div>
                        <div className="text-[13px] text-[#858585] font-normal">{p.team}</div>
                        <Link
                          to={`/player/${encodeURIComponent(p.player)}/${p.season}`}
                          className="inline-flex items-center gap-1 text-[12px] text-[#D4AF57] hover:text-[#E1C878] mt-1 hover:underline font-semibold"
                        >
                          Profile <ExternalLink className="w-3 h-3" />
                        </Link>
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody className="divide-y divide-[#222222] text-[#F2F2F2]">
                  {/* Category Header: Batting Volume */}
                  <tr className="bg-[#101010] font-semibold text-[#858585] text-[12px] uppercase tracking-wider">
                    <td colSpan={playersList.length + 1} className="py-2.5 px-4 sticky left-0 bg-[#101010]">
                      1. Batting volume & participation
                    </td>
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-3 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616] text-[13.5px] sm:text-[14px]">
                      Actual Runs
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans font-bold text-[#F2F2F2] tabular-nums">
                        {p.actual_runs}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616]">
                      Balls Faced
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans text-[#858585] tabular-nums">
                        {p.balls_faced}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616]">
                      Strike Rate
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans text-[#F2F2F2] tabular-nums">
                        {p.strike_rate !== null ? p.strike_rate.toFixed(1) : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616]">
                      Batting Innings
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans text-[#5A9E60] font-bold tabular-nums">
                        {p.batting_innings}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616]">
                      Matches Played
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans text-[#858585] tabular-nums">
                        {p.matches_played}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616]">
                      Did Not Bat (DNB)
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans text-[#858585] tabular-nums">
                        {p.did_not_bat_matches > 0 ? (
                          <span className="badge-dnb">{p.did_not_bat_matches} DNB</span>
                        ) : (
                          '0'
                        )}
                      </td>
                    ))}
                  </tr>

                  {/* Category Header: Core Contribution */}
                  <tr className="bg-[#101010] font-semibold text-[#858585] text-[12px] uppercase tracking-wider">
                    <td colSpan={playersList.length + 1} className="py-2.5 px-4 sticky left-0 bg-[#101010]">
                      2. Contextual contribution metrics
                    </td>
                  </tr>
                  <tr className="bg-[#101010] hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-3 px-4 font-bold text-[#F2F2F2] sticky left-0 bg-[#101010] text-[14px]">
                      Contribution Score (0–100)
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-3 px-4 text-center">
                        {p.contribution_score !== null ? (
                          <span
                            className={`inline-block px-3 py-1 rounded-full text-[13.5px] font-bold border tabular-nums font-sans ${
                              p.contribution_score >= 65
                                ? 'bg-[#152718] text-[#5A9E60] border-[#2A4D30]'
                                : p.contribution_score >= 52
                                ? 'bg-[#161616] text-[#D4AF57] border-[#D4AF57]/40'
                                : p.contribution_score >= 48
                                ? 'bg-[#161616] text-[#F2F2F2] border-[#2D2D2D]'
                                : 'bg-[#271414] text-[#C25454] border-[#4D2626]'
                            }`}
                          >
                            {Number(p.contribution_score).toFixed(1)}
                          </span>
                        ) : (
                          <span className="text-[#858585] font-semibold">—</span>
                        )}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616] text-[13.5px] sm:text-[14px]">
                      Positive Contribution (Raw)
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans font-bold text-[#5A9E60] tabular-nums text-[14px]">
                        {p.total_positive_raw_contribution !== null
                          ? `+${Number(p.total_positive_raw_contribution).toFixed(2)}`
                          : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616] text-[13.5px] sm:text-[14px]">
                      Team Contribution Share (%)
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans font-bold text-[#F2F2F2] tabular-nums text-[14px]">
                        {p.season_team_contribution_share !== null
                          ? `${Number(p.season_team_contribution_share).toFixed(1)}%`
                          : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616] text-[13.5px] sm:text-[14px]">
                      Contrib / Batting Opp
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans text-[#858585] tabular-nums text-[13.5px]">
                        {p.contribution_per_batting_opportunity !== null
                          ? Number(p.contribution_per_batting_opportunity).toFixed(4)
                          : '—'}
                      </td>
                    ))}
                  </tr>

                  {/* Category Header: Core Scoring Pillars */}
                  <tr className="bg-[#101010] font-semibold text-[#858585] text-[12px] uppercase tracking-wider">
                    <td colSpan={playersList.length + 1} className="py-2.5 px-4 sticky left-0 bg-[#101010] border-l-2 border-[#D4AF57]">
                      3. Context & core scoring pillars (50% Adj P2 + 50% Adj P3)
                    </td>
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616] text-[13.5px] sm:text-[14px]">
                      P1: Match Context (Leverage Signal)
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans font-bold text-[#F2F2F2] tabular-nums text-[14px]">
                        {p.pillars?.pillar1_match_context !== null ? Number(p.pillars.pillar1_match_context).toFixed(1) : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#D4AF57] sticky left-0 bg-[#161616] text-[13.5px] sm:text-[14px]">
                      P2: Batter Execution (50% Weight)
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans font-bold text-[#F2F2F2] tabular-nums text-[14px]">
                        {p.pillars?.adjusted_p2 !== null && p.pillars?.adjusted_p2 !== undefined
                           ? Number(p.pillars.adjusted_p2).toFixed(1)
                          : p.pillars?.pillar2_batter_performance !== null
                          ? Number(p.pillars.pillar2_batter_performance).toFixed(1)
                          : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#5A9E60] sticky left-0 bg-[#161616] text-[13.5px] sm:text-[14px]">
                      P3: Team-State Impact (50% Weight)
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans font-bold text-[#F2F2F2] tabular-nums text-[14px]">
                        {p.pillars?.adjusted_p3 !== null && p.pillars?.adjusted_p3 !== undefined
                          ? Number(p.pillars.adjusted_p3).toFixed(1)
                          : p.pillars?.pillar3_team_state_impact !== null
                          ? Number(p.pillars.pillar3_team_state_impact).toFixed(1)
                          : '—'}
                      </td>
                    ))}
                  </tr>

                  {/* Category Header: Contextual Breakdown */}
                  <tr className="bg-[#101010] font-semibold text-[#858585] text-[12px] uppercase tracking-wider">
                    <td colSpan={playersList.length + 1} className="py-2.5 px-4 sticky left-0 bg-[#101010]">
                      4. Contextual phase breakdown
                    </td>
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616]">
                      1st Innings Contribution
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans text-[#F2F2F2] tabular-nums">
                        {p.first_innings_contribution !== null ? Number(p.first_innings_contribution).toFixed(1) : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616]">
                      Chase (2nd Innings) Contribution
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans text-[#F2F2F2] tabular-nums">
                        {p.chase_contribution !== null ? Number(p.chase_contribution).toFixed(1) : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616]">
                      Powerplay (0–6)
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans text-[#F2F2F2] tabular-nums">
                        {p.powerplay_contribution !== null ? Number(p.powerplay_contribution).toFixed(1) : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616]">
                      Middle Overs (6–16)
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans text-[#F2F2F2] tabular-nums">
                        {p.middle_over_contribution !== null ? Number(p.middle_over_contribution).toFixed(1) : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616]">
                      Death Overs (16–20)
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans text-[#F2F2F2] tabular-nums">
                        {p.death_over_contribution !== null ? Number(p.death_over_contribution).toFixed(1) : '—'}
                      </td>
                    ))}
                  </tr>
                  <tr className="hover:bg-[#1A1A1A] transition-colors">
                    <td className="py-2.5 px-4 font-semibold text-[#B8B8B8] sticky left-0 bg-[#161616]">
                      High Pressure
                    </td>
                    {playersList.map((p) => (
                      <td key={p.player} className="py-2.5 px-4 text-center font-sans text-[#F2F2F2] tabular-nums">
                        {p.high_pressure_contribution !== null ? Number(p.high_pressure_contribution).toFixed(1) : '—'}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Comparison Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <FourPillarComparisonChart players={playersList} />
            <PrimaryMetricsComparisonChart players={playersList} />
          </div>
        </div>
      )}
    </div>
  );
}
