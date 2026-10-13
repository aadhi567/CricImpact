import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  Wind, 
  RotateCw, 
  Filter, 
  Search, 
  ArrowUpDown, 
  Info, 
  ChevronRight, 
  X, 
  Activity, 
  Award, 
  Layers 
} from 'lucide-react';
import { getSeasons, getTeams, getMatchupRankings, getBatterMatchupDetail } from '../services/api';
import { useCompetition } from '../context/CompetitionContext';

export default function BatterBowlingMatchup() {
  const [searchParams] = useSearchParams();
  const tabParam = searchParams.get('tab');
  const { competition } = useCompetition();

  // Filters
  const [seasons, setSeasons] = useState([]);
  const [teams, setTeams] = useState([]);
  const [selectedSeason, setSelectedSeason] = useState('All Seasons');
  const [selectedTeam, setSelectedTeam] = useState('All Teams');
  const [selectedTab, setSelectedTab] = useState(null);
  const activeTab = selectedTab || (tabParam && ['pace', 'spin', 'split'].includes(tabParam) ? tabParam : 'pace');
  const setActiveTab = (tab) => setSelectedTab(tab);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Minimum sample rule
  const [minBalls, setMinBalls] = useState(100);
  const [minRuns, setMinRuns] = useState(80);
  const [customSampleOpen, setCustomSampleOpen] = useState(false);

  // Data states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [rankingsData, setRankingsData] = useState({ pace: [], spin: [] });

  // Detail modal / selection
  const [selectedBatter, setSelectedBatter] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [batterDetail, setBatterDetail] = useState(null);

  // Load seasons on mount or competition change
  useEffect(() => {
    let isMounted = true;
    async function loadMeta() {
      try {
        const seasonsRes = await getSeasons(competition);
        if (isMounted && seasonsRes && seasonsRes.seasons) {
          setSeasons(['All Seasons', ...seasonsRes.seasons]);
          setSelectedSeason('All Seasons');
          setSelectedTeam('All Teams');
          setSelectedBatter(null);
        }
      } catch (err) {
        console.error('Failed to load seasons:', err);
      }
    }
    loadMeta();
    return () => {
      isMounted = false;
    };
  }, [competition]);

  // Update teams when season or competition changes
  useEffect(() => {
    async function loadTeams() {
      try {
        const seasonParam = selectedSeason === 'All Seasons' ? null : selectedSeason;
        const teamsRes = await getTeams(seasonParam, competition);
        if (teamsRes && teamsRes.teams) {
          setTeams(['All Teams', ...teamsRes.teams]);
          setSelectedTeam((curr) => {
            if (curr !== 'All Teams' && !teamsRes.teams.includes(curr)) {
              return 'All Teams';
            }
            return curr;
          });
        }
      } catch (err) {
        console.error('Failed to load teams:', err);
      }
    }
    loadTeams();
  }, [selectedSeason, competition]);

  // Load matchup rankings
  useEffect(() => {
    async function fetchRankings() {
      setLoading(true);
      setError(null);
      try {
        const data = await getMatchupRankings({
          season: selectedSeason,
          team: selectedTeam,
          minBalls,
          minRuns,
          competition,
        });

        const paceList = data?.results?.pace?.rankings || [];
        const spinList = data?.results?.spin?.rankings || [];

        setRankingsData({
          pace: paceList,
          spin: spinList,
        });
      } catch (err) {
        setError(err.message || 'Failed to fetch batter matchup rankings.');
      } finally {
        setLoading(false);
      }
    }

    fetchRankings();
  }, [selectedSeason, selectedTeam, minBalls, minRuns, competition]);

  // Load batter detail on selection
  useEffect(() => {
    if (!selectedBatter) {
      return;
    }

    let isMounted = true;
    async function fetchDetail() {
      setDetailLoading(true);
      try {
        const detail = await getBatterMatchupDetail(selectedBatter, {
          season: selectedSeason,
          team: selectedTeam,
          competition,
        });
        if (isMounted) {
          setBatterDetail(detail);
        }
      } catch (err) {
        console.error('Failed to load batter detail:', err);
      } finally {
        if (isMounted) {
          setDetailLoading(false);
        }
      }
    }

    fetchDetail();
    return () => {
      isMounted = false;
    };
  }, [selectedBatter, selectedSeason, selectedTeam, competition]);

  // Filter lists by search term
  const filteredPace = useMemo(() => {
    if (!searchTerm.trim()) return rankingsData.pace;
    const term = searchTerm.toLowerCase();
    return rankingsData.pace.filter((r) => r.batter.toLowerCase().includes(term));
  }, [rankingsData.pace, searchTerm]);

  const filteredSpin = useMemo(() => {
    if (!searchTerm.trim()) return rankingsData.spin;
    const term = searchTerm.toLowerCase();
    return rankingsData.spin.filter((r) => r.batter.toLowerCase().includes(term));
  }, [rankingsData.spin, searchTerm]);

  return (
    <div className="w-full space-y-8 font-mono text-[#F2F2F2]">
      {/* Page Header */}
      <div className="border-b border-[#2D2D2D] pb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="p-2.5 rounded-lg bg-[#1F1C14] border border-[#A8893D]/40 text-[#D4AF57]">
                <Layers className="w-5 h-5" />
              </span>
              <h1 className="font-heading text-[30px] sm:text-[34px] lg:text-[36px] font-bold tracking-wider text-[#F2F2F2] leading-tight">
                Batters vs Bowling Type
              </h1>
            </div>
            <p className="mt-1.5 text-[15px] sm:text-[16px] font-normal text-[#B8B8B8] leading-relaxed max-w-5xl">
              Matchup performance rankings measuring scoring rate against Pace and Spin bowling.
            </p>
          </div>

          {/* Model separation tag */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#101010] border border-[#2D2D2D] text-[12.5px] sm:text-[13px] font-medium text-[#858585] self-start md:self-auto">
            <span className="w-2 h-2 rounded-full bg-[#D4AF57]" />
            Matchup Analytics • Separate from Contribution Score
          </div>
        </div>

        {/* Methodology & Rule Explanatory Banner */}
        <div className="mt-5 p-5 sm:p-6 rounded-xl bg-[#161616] border border-[#2D2D2D] shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-[#D4AF57] shrink-0 mt-0.5" />
            <div className="text-[14px] sm:text-[14.5px] font-normal text-[#B8B8B8] leading-relaxed">
              <p>
                <strong className="text-[#F2F2F2] font-semibold">About this ranking: </strong>
                Strike Rate vs Pace/Spin measures how quickly a batter scores against each bowling type.
                Formula: <span className="font-mono text-[#D4AF57] font-medium bg-[#101010] px-2 py-0.5 rounded border border-[#2D2D2D]">Strike Rate = (Runs / Balls) × 100</span>.
                Legal balls faced excludes wides and no-balls.
              </p>
              <p className="mt-1.5 text-[13px] text-[#858585]">
                <span className="font-semibold text-[#F2F2F2]">Minimum sample rule:</span>{' '}
                <span className="text-[#D4AF57] font-semibold">100 balls or 80 runs.</span>{' '}
                This prevents extremely small samples from dominating the leaderboards.
              </p>
            </div>
          </div>
          <div className="shrink-0 text-right">
            <span className="text-[12px] font-medium text-[#858585] block">
              Independent Matchup Metric
            </span>
            <span className="text-[13px] font-semibold text-[#F2F2F2]">
              Pace vs Spin Statistics
            </span>
          </div>
        </div>

        {competition !== 'ipl' && (
          <div className="mt-4 p-4 rounded-xl bg-[#1F1C14] border border-[#D4AF57]/40 text-[#E0C068] text-[13.5px] flex items-center justify-between">
            <span>
              Pace vs Spin matchup classification is currently configured for <strong>IPL</strong> matches. Switch to <strong>IPL</strong> in the competition selector to view bowler-type splits.
            </span>
          </div>
        )}
      </div>

      {/* Control Toolbar: Filters */}
      <div className="bg-[#161616] rounded-xl border border-[#2D2D2D] p-4 sm:p-5 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          {/* Left: Tab Selectors */}
          <div className="flex items-center gap-1.5 p-1 bg-[#101010] rounded-lg border border-[#2D2D2D] self-start">
            <button
              type="button"
              onClick={() => setActiveTab('pace')}
              className={`px-3.5 py-2 rounded-md text-[13px] font-semibold flex items-center gap-2 transition-all cursor-pointer ${
                activeTab === 'pace'
                  ? 'bg-[#D4AF57] text-[#080808] shadow-xs'
                  : 'text-[#858585] hover:text-[#F2F2F2]'
              }`}
            >
              <Wind className="w-4 h-4" />
              <span>Top vs Pace ({filteredPace.length})</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('spin')}
              className={`px-3.5 py-2 rounded-md text-[13px] font-semibold flex items-center gap-2 transition-all cursor-pointer ${
                activeTab === 'spin'
                  ? 'bg-[#D4AF57] text-[#080808] shadow-xs'
                  : 'text-[#858585] hover:text-[#F2F2F2]'
              }`}
            >
              <RotateCw className="w-4 h-4" />
              <span>Top vs Spin ({filteredSpin.length})</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('split')}
              className={`px-3.5 py-2 rounded-md text-[13px] font-semibold flex items-center gap-2 transition-all cursor-pointer ${
                activeTab === 'split'
                  ? 'bg-[#D4AF57] text-[#080808] shadow-xs'
                  : 'text-[#858585] hover:text-[#F2F2F2]'
              }`}
            >
              <ArrowUpDown className="w-4 h-4" />
              <span>Side-by-Side</span>
            </button>
          </div>

          {/* Right: Search & Selectors */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="relative min-w-[220px] flex-1 sm:flex-initial">
              <Search className="w-4 h-4 text-[#858585] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search batter..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3.5 py-2 text-[13.5px] bg-[#101010] border border-[#2D2D2D] rounded-lg text-[#F2F2F2] placeholder-[#858585] focus:outline-hidden focus:border-[#D4AF57]"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => setSearchTerm('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#858585] hover:text-[#F2F2F2]"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Season Filter */}
            <div className="flex items-center gap-1.5">
              <span className="text-[12.5px] font-medium text-[#858585]">Season:</span>
              <select
                value={selectedSeason}
                onChange={(e) => setSelectedSeason(e.target.value)}
                className="text-[13.5px] bg-[#101010] border border-[#2D2D2D] rounded-lg px-3 py-2 text-[#F2F2F2] font-medium focus:outline-hidden focus:border-[#D4AF57] cursor-pointer"
              >
                {seasons.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            {/* Team Filter */}
            <div className="flex items-center gap-1.5">
              <span className="text-[12.5px] font-medium text-[#858585]">Team:</span>
              <select
                value={selectedTeam}
                onChange={(e) => setSelectedTeam(e.target.value)}
                className="text-[13.5px] bg-[#101010] border border-[#2D2D2D] rounded-lg px-3 py-2 text-[#F2F2F2] font-medium focus:outline-hidden focus:border-[#D4AF57] max-w-[170px] truncate cursor-pointer"
              >
                {teams.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            {/* Threshold Popover Button */}
            <button
              type="button"
              onClick={() => setCustomSampleOpen(!customSampleOpen)}
              className={`text-[12.5px] px-3 py-2 rounded-lg border flex items-center gap-1.5 transition-colors cursor-pointer ${
                minBalls !== 100 || minRuns !== 80
                  ? 'bg-[#1F1C14] border-[#A8893D] text-[#D4AF57] font-semibold'
                  : 'bg-[#101010] border-[#2D2D2D] text-[#858585] hover:text-[#F2F2F2]'
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              <span>Sample: ≥{minBalls}B or ≥{minRuns}R</span>
            </button>
          </div>
        </div>

        {/* Custom Sample Expandable Box */}
        {customSampleOpen && (
          <div className="pt-3 border-t border-[#2D2D2D] flex flex-wrap items-center justify-between gap-4 text-xs bg-[#101010] p-3 rounded-md">
            <div className="flex items-center gap-4">
              <span className="font-semibold text-[#F2F2F2]">Adjust Minimum Sample:</span>
              <div className="flex items-center gap-2">
                <label htmlFor="min-balls-input" className="text-[#858585]">Min Balls:</label>
                <input
                  id="min-balls-input"
                  type="number"
                  min="0"
                  max="1000"
                  value={minBalls}
                  onChange={(e) => setMinBalls(Math.max(0, parseInt(e.target.value) || 0))}
                  className="w-16 px-2 py-1 bg-[#080808] border border-[#2D2D2D] rounded text-center text-[#F2F2F2] font-semibold font-mono"
                />
              </div>
              <div className="flex items-center gap-2">
                <label htmlFor="min-runs-input" className="text-[#858585]">Min Runs:</label>
                <input
                  id="min-runs-input"
                  type="number"
                  min="0"
                  max="1000"
                  value={minRuns}
                  onChange={(e) => setMinRuns(Math.max(0, parseInt(e.target.value) || 0))}
                  className="w-16 px-2 py-1 bg-[#080808] border border-[#2D2D2D] rounded text-center text-[#F2F2F2] font-semibold font-mono"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setMinBalls(100);
                  setMinRuns(80);
                }}
                className="text-[11px] px-2.5 py-1 text-[#858585] hover:text-[#F2F2F2] underline cursor-pointer"
              >
                Reset to Default (100B / 80R)
              </button>
              <button
                type="button"
                onClick={() => setCustomSampleOpen(false)}
                className="px-3 py-1 bg-[#D4AF57] text-[#080808] rounded text-xs font-bold cursor-pointer"
              >
                Apply
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      {error && (
        <div className="p-4 rounded-xl bg-[#271414] border border-[#4D2626] text-[#C25454] text-sm">
          <strong>Error loading matchup rankings:</strong> {error}
        </div>
      )}

      {loading ? (
        <div className="bg-[#161616] rounded-xl border border-[#2D2D2D] p-12 text-center space-y-3">
          <Activity className="w-8 h-8 text-[#D4AF57] animate-pulse mx-auto" />
          <p className="text-sm font-semibold text-[#F2F2F2]">Calculating Matchup Rankings...</p>
          <p className="text-xs text-[#858585]">
            Aggregating ball-by-ball performance against Pace and Spin deliveries.
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {/* TAB: TOP BATTERS VS PACE */}
          {(activeTab === 'pace' || activeTab === 'split') && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Wind className="w-5 h-5 text-[#D4AF57]" />
                  <h2 className="font-heading text-[17px] font-bold text-[#F2F2F2] tracking-tight">
                    Top Batters vs Pace
                  </h2>
                </div>
                <span className="text-xs font-medium text-[#858585]">
                  Sorted by Strike Rate (descending) • {filteredPace.length} eligible batters
                </span>
              </div>

              <RankingTable
                data={filteredPace}
                bowlingType="Pace"
                onSelectBatter={setSelectedBatter}
                selectedBatter={selectedBatter}
              />
            </div>
          )}

          {/* TAB: TOP BATTERS VS SPIN */}
          {(activeTab === 'spin' || activeTab === 'split') && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <RotateCw className="w-5 h-5 text-[#D4AF57]" />
                  <h2 className="font-heading text-[17px] font-bold text-[#F2F2F2] tracking-tight">
                    Top Batters vs Spin
                  </h2>
                </div>
                <span className="text-xs font-medium text-[#858585]">
                  Sorted by Strike Rate (descending) • {filteredSpin.length} eligible batters
                </span>
              </div>

              <RankingTable
                data={filteredSpin}
                bowlingType="Spin"
                onSelectBatter={setSelectedBatter}
                selectedBatter={selectedBatter}
              />
            </div>
          )}
        </div>
      )}

      {/* Selected Batter Detail Drawer/Modal */}
      {selectedBatter && (
        <div className="fixed inset-0 z-50 bg-[#080808]/80 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#161616] max-w-xl w-full p-6 shadow-xl border border-[#2D2D2D] rounded-xl space-y-6 animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-[#2D2D2D] pb-4">
              <div>
                <span className="text-xs font-semibold text-[#D4AF57] uppercase tracking-wider">
                  Batter Matchup Profile
                </span>
                <h3 className="font-heading text-2xl font-bold text-[#F2F2F2] tracking-tight">
                  {selectedBatter}
                </h3>
                <p className="text-xs text-[#858585] mt-0.5">
                  Scope: {selectedSeason} • {selectedTeam}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedBatter(null)}
                className="p-1.5 rounded-lg text-[#858585] hover:text-[#F2F2F2] hover:bg-[#222222] border border-transparent hover:border-[#2D2D2D] cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {detailLoading ? (
              <div className="py-12 text-center text-sm text-[#858585]">
                <Activity className="w-6 h-6 text-[#D4AF57] animate-spin mx-auto mb-2" />
                Loading matchup breakdown...
              </div>
            ) : batterDetail ? (
              <div className="space-y-6">
                {/* Two Cards: Pace vs Spin */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Pace Card */}
                  <div className="p-4 rounded-xl bg-[#101010] border border-[#2D2D2D] space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[#F2F2F2] flex items-center gap-1.5">
                        <Wind className="w-4 h-4 text-[#D4AF57]" />
                        BATTER VS PACE
                      </span>
                      <span className="text-[11px] px-2 py-0.5 rounded bg-[#161616] text-[#858585] font-semibold border border-[#2D2D2D]">
                        Fast & Medium
                      </span>
                    </div>

                    <div className="space-y-1.5 pt-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-[#858585]">Runs:</span>
                        <span className="font-semibold text-[#F2F2F2] tabular-nums font-mono">
                          {batterDetail.pace.runs}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-[#858585]">Balls Faced:</span>
                        <span className="font-semibold text-[#F2F2F2] tabular-nums font-mono">
                          {batterDetail.pace.balls}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs pt-1.5 border-t border-[#2D2D2D]">
                        <span className="font-semibold text-[#F2F2F2]">Strike Rate:</span>
                        <span className="font-bold text-base text-[#D4AF57] tabular-nums font-mono">
                          {batterDetail.pace.strike_rate.toFixed(1)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Spin Card */}
                  <div className="p-4 rounded-xl bg-[#101010] border border-[#2D2D2D] space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[#F2F2F2] flex items-center gap-1.5">
                        <RotateCw className="w-4 h-4 text-[#D4AF57]" />
                        BATTER VS SPIN
                      </span>
                      <span className="text-[11px] px-2 py-0.5 rounded bg-[#161616] text-[#858585] font-semibold border border-[#2D2D2D]">
                        Wrist & Finger
                      </span>
                    </div>

                    <div className="space-y-1.5 pt-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-[#858585]">Runs:</span>
                        <span className="font-semibold text-[#F2F2F2] tabular-nums font-mono">
                          {batterDetail.spin.runs}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-[#858585]">Balls Faced:</span>
                        <span className="font-semibold text-[#F2F2F2] tabular-nums font-mono">
                          {batterDetail.spin.balls}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs pt-1.5 border-t border-[#2D2D2D]">
                        <span className="font-semibold text-[#F2F2F2]">Strike Rate:</span>
                        <span className="font-bold text-base text-[#D4AF57] tabular-nums font-mono">
                          {batterDetail.spin.strike_rate.toFixed(1)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Matchup Comparison & Advantage Summary */}
                <div className="p-4 rounded-xl bg-[#101010] border border-[#2D2D2D] shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[#F2F2F2] flex items-center gap-1.5">
                      <Award className="w-4 h-4 text-[#D4AF57]" />
                      Matchup Differential
                    </span>
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full font-bold ${
                        batterDetail.difference.advantage_type === 'Spin'
                          ? 'bg-[#152718] text-[#5A9E60] border border-[#2A4D30]'
                          : batterDetail.difference.advantage_type === 'Pace'
                          ? 'bg-[#1F1C14] text-[#D4AF57] border border-[#A8893D]/40'
                          : 'bg-[#161616] text-[#858585] border border-[#2D2D2D]'
                      }`}
                    >
                      {batterDetail.difference.advantage_text}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center text-xs pt-1">
                    <div className="p-2 bg-[#161616] rounded border border-[#2D2D2D]">
                      <span className="block text-[11px] text-[#858585]">SR Diff</span>
                      <span className="font-bold text-sm text-[#F2F2F2] tabular-nums font-mono">
                        {batterDetail.difference.sr_difference > 0 ? '+' : ''}
                        {batterDetail.difference.sr_difference.toFixed(1)}
                      </span>
                    </div>

                    <div className="p-2 bg-[#161616] rounded border border-[#2D2D2D]">
                      <span className="block text-[11px] text-[#858585]">Runs Diff (Spin-Pace)</span>
                      <span className="font-bold text-sm text-[#F2F2F2] tabular-nums font-mono">
                        {batterDetail.difference.runs_difference > 0 ? '+' : ''}
                        {batterDetail.difference.runs_difference}
                      </span>
                    </div>

                    <div className="p-2 bg-[#161616] rounded border border-[#2D2D2D]">
                      <span className="block text-[11px] text-[#858585]">Balls Diff (Spin-Pace)</span>
                      <span className="font-bold text-sm text-[#F2F2F2] tabular-nums font-mono">
                        {batterDetail.difference.balls_difference > 0 ? '+' : ''}
                        {batterDetail.difference.balls_difference}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Non-Contribution Model Disclaimer */}
                <div className="p-3 bg-[#101010] rounded-lg text-xs text-[#858585] text-center border border-[#2D2D2D]">
                  Pure matchup performance • Distinct from Contribution Score
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-sm text-[#858585]">
                No matchup breakdown available for this batter.
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedBatter(null)}
                className="px-4 py-2 rounded-lg bg-[#101010] hover:bg-[#222222] border border-[#2D2D2D] text-[#F2F2F2] text-xs font-semibold cursor-pointer"
              >
                Close Profile
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Reusable ranking table for Pace / Spin leaderboards.
 */
function RankingTable({ data, bowlingType, onSelectBatter, selectedBatter }) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-[#161616] rounded-xl border border-[#2D2D2D] p-8 text-center text-xs text-[#858585]">
        No batters met the eligibility criteria for {bowlingType} bowling with current filters.
      </div>
    );
  }

  return (
    <div className="bg-[#161616] rounded-xl overflow-hidden border border-[#2D2D2D]">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#2D2D2D] bg-[#161616] text-[#858585] text-[12.5px] sm:text-[13px] font-semibold uppercase tracking-wider">
              <th className="py-3.5 px-4 text-center w-14 sm:w-16">Rank</th>
              <th className="py-3.5 px-4 text-left">Batter</th>
              <th className="py-3.5 px-4 text-right">Balls Faced</th>
              <th className="py-3.5 px-4 text-right">Runs</th>
              <th className="py-3.5 px-4 text-right">Strike Rate</th>
              <th className="py-3.5 px-4 text-center w-24">Detail</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#222222] text-[#F2F2F2] text-[14px] sm:text-[14.5px] font-normal">
            {data.map((row) => {
              const isSelected = selectedBatter === row.batter;
              const isTop3 = row.rank <= 3;
              return (
                <tr
                  key={row.batter}
                  onClick={() => onSelectBatter(row.batter)}
                  className={`cursor-pointer transition-colors hover:bg-[#1A1A1A] ${
                    isSelected ? 'bg-[#1D1D1D]' : ''
                  }`}
                >
                  {/* Rank */}
                  <td className="py-3.5 px-4 text-center font-bold">
                    <span
                      className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-[12px] ${
                        row.rank === 1
                          ? 'bg-[#D4AF57] text-[#080808] font-bold shadow-xs'
                          : row.rank === 2
                          ? 'bg-[#858585] text-[#080808] font-bold'
                          : row.rank === 3
                          ? 'bg-[#A8893D] text-[#080808] font-bold'
                          : 'text-[#858585]'
                      }`}
                    >
                      {row.rank}
                    </span>
                  </td>

                  {/* Batter Name */}
                  <td className="py-3.5 px-4 font-semibold text-[14px] sm:text-[14.5px] text-[#F2F2F2] whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <span className="hover:text-[#D4AF57] transition-colors">{row.batter}</span>
                      {isTop3 && (
                        <span className="text-[11px] font-bold text-[#D4AF57] bg-[#1F1C14] px-2 py-0.5 rounded border border-[#A8893D]/40">
                          Top {row.rank}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Balls Faced */}
                  <td className="py-3.5 px-4 text-right tabular-nums text-[13.5px] sm:text-[14px] text-[#858585] font-mono">
                    {row.balls}
                  </td>

                  {/* Runs */}
                  <td className="py-3.5 px-4 text-right tabular-nums text-[14px] sm:text-[14.5px] font-semibold text-[#F2F2F2] font-mono">
                    {row.runs}
                  </td>

                  {/* Strike Rate */}
                  <td className="py-3.5 px-4 text-right tabular-nums font-semibold text-[14px] text-[#F2F2F2] font-mono">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded ${
                        row.strike_rate >= 150
                          ? 'bg-[#152718] text-[#5A9E60] border border-[#2A4D30]'
                          : row.strike_rate >= 130
                          ? 'text-[#F2F2F2]'
                          : 'text-[#858585]'
                      }`}
                    >
                      {row.strike_rate.toFixed(1)}
                    </span>
                  </td>

                  {/* Detail Action */}
                  <td className="py-3.5 px-4 text-center">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectBatter(row.batter);
                      }}
                      className="inline-flex items-center gap-1 text-[12.5px] sm:text-[13px] font-semibold text-[#D4AF57] hover:text-[#E1C878] hover:underline cursor-pointer"
                    >
                      <span>View</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
