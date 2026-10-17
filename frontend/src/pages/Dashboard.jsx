import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  Users,
  Award,
  TrendingUp,
  Compass,
  ArrowUpDown,
  ExternalLink,
  Info,
  X,
  Zap,
  ShieldCheck,
} from 'lucide-react';
import MetricCard from '../components/MetricCard';
import SeasonFilter from '../components/SeasonFilter';
import RunsVsContributionScatter from '../components/Charts/RunsVsContributionScatter';
import StrikeRateVsContributionScatter from '../components/Charts/StrikeRateVsContributionScatter';
import {
  getSeasons,
  getTeams,
  getDashboardSummary,
  getPlayers,
  getScatterData,
} from '../services/api';
import { useCompetition, TOURNAMENT_TYPES, resolveDefaultSeason } from '../context/CompetitionContext';

export default function Dashboard({ initialFocus }) {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    competition,
    activeMeta,
    tournamentType,
    setTournamentType,
    selectedSeason,
    setSelectedSeason,
  } = useCompetition();

  // Scroll to players table, top contributors, or season overview if requested
  useEffect(() => {
    if (initialFocus === 'players' || location.hash === '#players-table') {
      const el = document.getElementById('players-table');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
      }
    } else if (initialFocus === 'seasons' || location.hash === '#season-overview') {
      const el = document.getElementById('season-overview');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
      }
    } else if (initialFocus === 'matches') {
      const el = document.getElementById('players-table');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
      }
    } else if (location.hash === '#top-contributors') {
      const el = document.getElementById('top-contributors');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }, [initialFocus, location.hash]);

  // Filter States
  const [seasons, setSeasons] = useState([]);
  const [seasonOptions, setSeasonOptions] = useState([]);
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState('');
  const [minRuns, setMinRuns] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  // Data States
  const [summary, setSummary] = useState(null);
  const [players, setPlayers] = useState([]);
  const [scatterPoints, setScatterPoints] = useState([]);
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

        // Keep the selected season when valid; otherwise dynamically resolve default season
        setSelectedSeason((curr) => {
          if (curr && availSeasons.includes(curr)) {
            return curr;
          }
          return resolveDefaultSeason(availSeasons, data.default_season);
        });
        setSelectedTeam('');
        setSelectedForCompare([]);
      } catch (err) {
        setError(err.message || 'Failed to load season data.');
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

  // 3. Load summary, players, and scatter data when filters change
  useEffect(() => {
    if (!selectedSeason) return;

    let isMounted = true;
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const [sumRes, playRes, scatRes] = await Promise.all([
          getDashboardSummary({ season: selectedSeason, team: selectedTeam, minRuns, competition, tournamentType }),
          getPlayers({
            season: selectedSeason,
            team: selectedTeam,
            minRuns,
            search: searchQuery,
            limit: 500,
            competition,
            tournamentType,
          }),
          getScatterData({
            season: selectedSeason,
            team: selectedTeam,
            limit: 1200,
            competition,
            tournamentType,
          }),
        ]);

        if (isMounted) {
          setSummary(sumRes);
          setPlayers(playRes.players || []);
          setScatterPoints(scatRes.points || []);
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

      // Handle nulls always at bottom
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

  // Top Contributors (min 2 innings, sorted by contribution score)
  const topContributors = useMemo(() => {
    return [...players]
      .filter((p) => p.batting_innings >= 2 && p.average_contribution_score !== null)
      .sort((a, b) => (b.average_contribution_score || 0) - (a.average_contribution_score || 0))
      .slice(0, 5);
  }, [players]);

  const currentSeasonLabel = useMemo(() => {
    const opt = seasonOptions.find((o) => o.value === selectedSeason);
    return opt ? opt.label : selectedSeason;
  }, [seasonOptions, selectedSeason]);

  return (
    <div className="w-full space-y-8 font-mono text-[#F2F2F2]">
      {/* 1. Page Header (Cinzel 30–36px, Inter/Mono 15–16px) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#2D2D2D]">
        <div>
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-[11px] sm:text-[12px] font-mono uppercase tracking-wider text-[#D4AF57] font-semibold mb-1.5">
            <ShieldCheck className="w-4 h-4 shrink-0" />
            <span>{activeMeta?.short_name || 'T20'} CONTRIBUTION ANALYSIS</span>
            {competition === 't20i' && tournamentType && tournamentType !== 'all' && (
              <>
                <span className="text-[#858585]">•</span>
                <span className="text-[#D4AF57] bg-[#1E190E] px-2 py-0.5 rounded border border-[#3D351E]">
                  {TOURNAMENT_TYPES.find((t) => t.id === tournamentType)?.label || tournamentType}
                </span>
              </>
            )}
            <span className="text-[#858585]">•</span>
            <span className="text-[#F2F2F2]">
              {selectedSeason ? currentSeasonLabel : 'SEASON OVERVIEW'}
            </span>
          </div>
          <h1 className="font-heading text-[22px] sm:text-[30px] lg:text-[36px] font-bold text-[#F2F2F2] tracking-wide leading-tight break-words">
            {activeMeta?.name ? `${activeMeta.name.toUpperCase()} ANALYSIS` : 'SEASON CONTRIBUTION ANALYSIS'}
          </h1>
          <p className="text-[14px] sm:text-[16px] font-normal text-[#B8B8B8] mt-1.5 leading-relaxed max-w-5xl">
            Analyze contextual batter contribution across actual batting opportunities in {activeMeta?.name || 'T20 cricket'}.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto shrink-0 flex-wrap">
          {competition === 't20i' && (
            <span className="px-3.5 py-2 rounded-lg text-[13px] font-medium bg-[#161616] text-[#858585] border border-[#2D2D2D]">
              Tournament: <strong className="text-[#D4AF57] ml-1 font-semibold">{TOURNAMENT_TYPES.find((t) => t.id === tournamentType)?.label || 'All International T20Is'}</strong>
            </span>
          )}
          <span className="px-3.5 py-2 rounded-lg text-[13px] font-medium bg-[#161616] text-[#858585] border border-[#2D2D2D]">
            Season: <strong className="text-[#D4AF57] ml-1 font-semibold">{currentSeasonLabel || 'Loading...'}</strong>
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
        onTeamChange={setSelectedTeam}
        minRuns={minRuns}
        onMinRunsChange={setMinRuns}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {error && (
        <div className="p-4 rounded-xl bg-[#271414] border border-[#4D2626] text-[#C25454] text-[13px] font-medium">
          Error loading dashboard data: {error}
        </div>
      )}

      {/* 3. Top Contributors Ranking Section */}
      <div id="top-contributors" className="bg-[#161616] rounded-xl border border-[#2D2D2D] overflow-hidden shadow-xs">
        <div className="px-5 py-4 border-b border-[#2D2D2D] bg-[#101010] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <Award className="w-5 h-5 text-[#D4AF57]" />
              <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
                TOP SEASON CONTRIBUTORS
              </h2>
              <span className="text-[11.5px] font-sans text-[#D4AF57] bg-[#161616] px-2.5 py-0.5 rounded border border-[#3D351E]">
                Par = 50.0
              </span>
            </div>
            <p className="text-[13px] font-sans text-[#858585] mt-1">
              Players with the highest average Contribution Score among qualified batting opportunities (minimum 2 batting innings).
            </p>
          </div>
          <span className="text-[12px] font-sans text-[#858585] self-start sm:self-auto shrink-0 bg-[#161616] px-3 py-1 rounded-md border border-[#2D2D2D]">
            {selectedSeason || 'Season'} Qualification: ≥2 Innings
          </span>
        </div>

        {loading ? (
          <div className="py-6 text-center text-[12px] text-[#858585]">
            Loading top contributors...
          </div>
        ) : topContributors.length === 0 ? (
          <div className="py-6 text-center text-[12px] text-[#858585]">
            No qualified batters found for current filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse font-sans">
              <thead>
                <tr className="border-b border-[#2D2D2D] bg-[#101010] text-[#858585] font-semibold text-[12.5px] sm:text-[13px] tracking-wider uppercase">
                  <th className="py-3.5 px-3 text-center w-14 sm:w-16">Rank</th>
                  <th className="py-3.5 px-4 sm:px-5">Batter</th>
                  <th className="py-3.5 px-3.5">Team</th>
                  <th className="py-3.5 px-3.5 text-right">Runs</th>
                  <th className="py-3.5 px-3.5 text-right">SR</th>
                  <th className="py-3.5 px-4 sm:px-5 text-center">Contribution</th>
                  <th className="py-3.5 px-3.5 text-right">Positive Contrib</th>
                  <th className="py-3.5 px-3.5 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#222222] text-[#F2F2F2] text-[14px] sm:text-[14.5px] font-normal">
                {topContributors.map((p, idx) => {
                  const sr = p.balls_faced > 0 ? ((p.actual_runs / p.balls_faced) * 100).toFixed(1) : '—';
                  let rankBadge = 'text-[#858585]';
                  if (idx === 0) rankBadge = 'bg-[#2E2717] text-[#D4AF57] border border-[#D4AF57]/40 font-bold'; // Gold
                  else if (idx === 1) rankBadge = 'bg-[#222222] text-[#B8B8B8] border border-[#3D3D3D] font-bold'; // Silver
                  else if (idx === 2) rankBadge = 'bg-[#241D17] text-[#A8893D] border border-[#A8893D]/30 font-bold'; // Bronze

                  return (
                    <tr
                      key={`top-${p.player}-${p.season}`}
                      onClick={() => navigate(`/player/${encodeURIComponent(p.player)}/${selectedSeason}`)}
                      className="cursor-pointer hover:bg-[#1D1D1D] transition-colors"
                    >
                      <td className="py-3 px-3 text-center">
                        <span
                          className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-[12px] ${rankBadge}`}
                        >
                          {idx + 1}
                        </span>
                      </td>
                      <td className="py-3 px-4 sm:px-5 font-semibold text-[14.5px] text-[#F2F2F2] hover:text-[#D4AF57] whitespace-nowrap">
                        {p.player}
                        {p.not_outs > 0 && (
                          <span className="text-[12px] font-normal text-[#858585] ml-1.5 font-sans">
                            ({p.not_outs} NO)
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3.5 text-[#858585] whitespace-nowrap text-[13px]">{p.team}</td>
                      <td className="py-3 px-3.5 text-right font-medium tabular-nums whitespace-nowrap text-[#F2F2F2]">
                        {p.actual_runs}
                      </td>
                      <td className="py-3 px-3.5 text-right tabular-nums whitespace-nowrap text-[#858585]">
                        {sr}
                      </td>
                      <td className="py-3 px-4 sm:px-5 text-center whitespace-nowrap">
                        <span className="inline-block px-3 py-1 rounded-full text-[13px] font-semibold bg-[#101010] text-[#D4AF57] border border-[#D4AF57]/40 tabular-nums">
                          {p.average_contribution_score !== null
                            ? Number(p.average_contribution_score).toFixed(1)
                            : '—'}
                        </span>
                      </td>
                      <td className="py-3 px-3.5 text-right font-sans text-[#5A9E60] font-medium tabular-nums whitespace-nowrap">
                        {p.total_positive_raw_contribution !== null
                          ? Number(p.total_positive_raw_contribution).toFixed(2)
                          : '—'}
                      </td>
                      <td className="py-3 px-3.5 text-center whitespace-nowrap">
                        <span className="text-[#D4AF57] hover:underline font-semibold text-[13px] inline-flex items-center gap-1.5">
                          Analyze <ExternalLink className="w-3.5 h-3.5" />
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 4. Season Contribution Overview KPI Cards */}
      <div id="season-overview" className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2]">
            Season Contribution Overview
          </h2>
          <span className="text-[12px] font-sans text-[#858585] bg-[#161616] px-3 py-1 rounded-md border border-[#2D2D2D] self-start sm:self-auto">
            Strategy 4 Hybrid Scoring • Par Benchmark = 50.0
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <MetricCard
            title="Avg Contribution"
            value={summary?.average_contribution_score}
            subtitle="Par benchmark = 50.0"
            icon={Award}
            isScore={true}
            tooltip="The average Contribution Score across the player's actual batting opportunities in this season. Par benchmark = 50.0. DNB appearances are NOT treated as zero batting opportunities."
          />

          <MetricCard
            title="Total Positive Contribution"
            value={
              summary?.total_positive_contribution !== null &&
              summary?.total_positive_contribution !== undefined
                ? Number(summary.total_positive_contribution).toFixed(1)
                : '—'
            }
            subtitle="Cumulative above-par impact"
            icon={Zap}
            variant="accent"
            tooltip="Total positive raw contribution accumulated across genuine batting opportunities in this season."
          />

          <MetricCard
            title="Avg Team Contribution Share"
            value={
              summary?.average_team_contribution_share !== null &&
              summary?.average_team_contribution_share !== undefined
                ? `${Number(summary.average_team_contribution_share).toFixed(1)}%`
                : '—'
            }
            subtitle="Mean share of team positive impact"
            icon={TrendingUp}
            variant="positive"
            tooltip="Average percentage of team positive contribution delivered by individual batters."
          />

          <MetricCard
            title="Batting Opportunities"
            value={summary?.total_batting_innings}
            subtitle={`${summary?.total_dnb_matches || 0} DNB excluded`}
            icon={Compass}
            tooltip="Number of actual batting opportunities evaluated in this season. DNB is not counted as a zero contribution."
          />

          <MetricCard
            title="Players Evaluated"
            value={summary?.total_players}
            subtitle={`Across ${summary?.total_matches_played || 0} match slots`}
            icon={Users}
            tooltip="Number of unique batters included in the selected season's analysis."
          />
        </div>
      </div>

      {/* 5. Player Analytical Table (Cinzel 21-23px, Headers 12.5-13px, Content 14-14.5px) */}
      <div
        id="players-table"
        className="bg-[#161616] rounded-xl border border-[#2D2D2D] shadow-xs overflow-hidden"
      >
        <div className="p-4 sm:p-5 border-b border-[#2D2D2D] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2]">
                Season player analytical table
              </h2>
              <span className="text-[13px] font-normal text-[#858585]">({sortedPlayers.length} players)</span>
            </div>
            <p className="text-[13px] font-normal text-[#858585] mt-1">
              Click any player row to open match analysis. Click "[+ Compare]" to select up to 5 batters.
            </p>
          </div>

          {/* View A vs View B Toggle (Buttons: 13px) */}
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

        {/* Informational Context Bar */}
        <div className="px-4 py-2 bg-[#101010] border-b border-[#2D2D2D] text-[12px] font-normal text-[#858585] flex items-center gap-2">
          <Info className="w-3.5 h-3.5 text-[#D4AF57] shrink-0" />
          <span>
            <strong className="text-[#F2F2F2] font-semibold">Contextual Analytics:</strong> This analytical table evaluates performance against situational expectations. Par = 50.0.
          </span>
        </div>

        {/* Full-width Responsive Table (Table header: 10-11px, Table content: 12-13px) */}
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
            <tbody className="divide-y divide-[#222222] text-[#F2F2F2] text-[14px] sm:text-[14.5px] font-normal font-sans">
              {loading ? (
                Array.from({ length: 6 }).map((_, idx) => (
                  <tr key={`skel-${idx}`} className="animate-pulse">
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
                        }}
                        className="btn-secondary text-[12.5px] py-1.5 px-4 cursor-pointer inline-flex items-center gap-1.5"
                      >
                        Reset Filters
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                sortedPlayers.map((p) => {
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

                  // Score badge coloring for Gold & Onyx
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
                      {/* Player (Player name: 14.5px) */}
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
      </div>

      {/* 6. Scatter Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <RunsVsContributionScatter data={scatterPoints} />
        <StrikeRateVsContributionScatter data={scatterPoints} />
      </div>

      {/* 7. Floating Player Comparison Tray */}
      {selectedForCompare.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 w-11/12 max-w-4xl bg-[#161616] border border-[#2D2D2D] rounded-xl shadow-2xl p-4 transition-all">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[13px] font-semibold text-[#D4AF57] mr-1">
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
