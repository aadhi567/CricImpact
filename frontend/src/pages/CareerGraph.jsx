import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useSearchParams, useParams, Link } from 'react-router-dom';
import {
  TrendingUp,
  Search,
  X,
  Trophy,
  Globe,
  Layers,
  Info,
  ArrowUpDown,
  ExternalLink,
  AlertTriangle,
  RotateCcw,
  Calendar,
} from 'lucide-react';
import Breadcrumbs from '../components/Breadcrumbs';
import ErrorBoundary from '../components/ErrorBoundary';
import CareerRunsChart from '../components/CareerGraphs/CareerRunsChart';
import CareerStrikeRateChart from '../components/CareerGraphs/CareerStrikeRateChart';
import CareerContributionChart from '../components/CareerGraphs/CareerContributionChart';
import CareerPositiveRateChart from '../components/CareerGraphs/CareerPositiveRateChart';
import CareerDotBallChart from '../components/CareerGraphs/CareerDotBallChart';
import CareerHighsLows from '../components/CareerGraphs/CareerHighsLows';
import BowlingTypeTrendsChart from '../components/CareerGraphs/BowlingTypeTrendsChart';
import { getPlayerCareer, searchCareerPlayers, getDatasetCoverage } from '../services/api';

const FEATURED_BATTERS = [
  'V Kohli',
  'RG Sharma',
  'SA Yadav',
  'MS Dhoni',
  'DA Warner',
  'JC Buttler',
  'KL Rahul',
  'SV Samson',
  'Rashid Khan',
];

export default function CareerGraph() {
  const [searchParams, setSearchParams] = useSearchParams();
  const params = useParams();

  // Active player selection from URL or default to 'V Kohli'
  const playerFromUrl = params.playerId || searchParams.get('player') || 'V Kohli';
  const compFromUrl = searchParams.get('comp') || 'combined';

  const [selectedPlayer, setSelectedPlayer] = useState(playerFromUrl);
  const [competitionView, setCompetitionView] = useState(compFromUrl); // 'combined', 'ipl', 't20i'
  const [activeGraphTab, setActiveGraphTab] = useState('all'); // 'all', 'runs', 'sr', 'contrib', 'pos', 'dots'

  // Data states
  const [careerData, setCareerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [datasetCoverage, setDatasetCoverage] = useState(null);

  // Search autocomplete states
  const [searchInput, setSearchInput] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef(null);

  // Table sorting
  const [sortField, setSortField] = useState('season');
  const [sortDirection, setSortDirection] = useState('asc');

  // Sync state if URL changes
  useEffect(() => {
    const p = params.playerId || searchParams.get('player');
    if (p && p !== selectedPlayer) {
      setSelectedPlayer(p);
    }
    const c = searchParams.get('comp');
    if (c && c !== competitionView) {
      setCompetitionView(c);
    }
  }, [params.playerId, searchParams]);

  // Fetch career data whenever selected player or competition changes
  useEffect(() => {
    let cancelled = false;

    async function loadCareer() {
      if (!selectedPlayer) return;
      setLoading(true);
      setError(null);

      try {
        const data = await getPlayerCareer(selectedPlayer, competitionView);
        if (!cancelled) {
          setCareerData(data);
          if (data.dataset_coverage) {
            setDatasetCoverage(data.dataset_coverage);
          }
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load career data.');
          setLoading(false);
        }
      }
    }

    loadCareer();

    return () => {
      cancelled = true;
    };
  }, [selectedPlayer, competitionView]);

  // Initial dataset coverage fetch
  useEffect(() => {
    let cancelled = false;
    async function loadCoverage() {
      try {
        const cov = await getDatasetCoverage();
        if (!cancelled && cov) {
          setDatasetCoverage(cov);
        }
      } catch (err) {
        console.error('Failed to load dataset coverage metadata:', err);
      }
    }
    loadCoverage();
    return () => {
      cancelled = true;
    };
  }, []);

  // Debounced player search
  useEffect(() => {
    if (!searchInput || searchInput.trim().length === 0) {
      setSearchResults([]);
      setSearchLoading(false);
      return;
    }

    const timer = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const results = await searchCareerPlayers(searchInput, { limit: 10 });
        setSearchResults(results);
      } catch {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [searchInput]);

  // Close search dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setSearchOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectPlayer = (playerName) => {
    setSelectedPlayer(playerName);
    setSearchInput('');
    setSearchOpen(false);
    setSearchParams({ player: playerName, comp: competitionView });
  };

  const handleSelectCompetition = (comp) => {
    setCompetitionView(comp);
    setSearchParams({ player: selectedPlayer, comp });
  };

  // Sort timeline table
  const sortedTimeline = useMemo(() => {
    if (!careerData?.timeline) return [];
    return [...careerData.timeline].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      if (typeof aVal === 'string') {
        return sortDirection === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    });
  }, [careerData, sortField, sortDirection]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const summary = careerData?.career_summary;
  const timeline = careerData?.timeline || [];
  const availableComps = careerData?.available_competitions || { ipl: true, t20i: true };

  const renderCoverageIndicator = () => {
    const iplCov = datasetCoverage?.ipl;
    const t20iCov = datasetCoverage?.t20i;

    const isIplReliable = iplCov?.reliable !== false;
    const isT20iReliable = t20iCov?.reliable !== false;

    if (competitionView === 'ipl') {
      const range = iplCov?.display_range || (iplCov?.start_year ? `${iplCov.start_year} – ${iplCov.end_year}` : '2008 – 2026');
      return (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-[#F2F2F2]">
            IPL Records:{' '}
            <span className="text-[#D4AF57] font-bold tracking-wide">{range}</span>
          </span>
          {iplCov?.total_matches ? (
            <span className="text-[10px] text-[#A8893D] bg-[#1F1B12] px-2 py-0.5 rounded border border-[#A8893D]/30 font-medium">
              {iplCov.total_matches.toLocaleString()} matches
            </span>
          ) : null}
          {!isIplReliable && (
            <span className="text-[10px] text-[#C25454]">(Date coverage incomplete)</span>
          )}
        </div>
      );
    }

    if (competitionView === 't20i') {
      const range = t20iCov?.display_range || (t20iCov?.start_year ? `${t20iCov.start_year} – ${t20iCov.end_year}` : '2022 – 2026');
      return (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-[#F2F2F2]">
            International T20I Records:{' '}
            <span className="text-[#D4AF57] font-bold tracking-wide">{range}</span>
          </span>
          {t20iCov?.total_matches ? (
            <span className="text-[10px] text-[#A8893D] bg-[#1F1B12] px-2 py-0.5 rounded border border-[#A8893D]/30 font-medium">
              {t20iCov.total_matches.toLocaleString()} matches
            </span>
          ) : null}
          {!isT20iReliable && (
            <span className="text-[10px] text-[#C25454]">(Date coverage incomplete)</span>
          )}
        </div>
      );
    }

    // Combined View
    const iplRange = iplCov?.display_range || '2008 – 2026';
    const t20iRange = t20iCov?.display_range || '2022 – 2026';
    return (
      <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs">
        <span className="font-semibold text-[#F2F2F2]">
          IPL Records:{' '}
          <span className="text-[#D4AF57] font-bold tracking-wide">{iplRange}</span>
        </span>
        <span className="text-[#4D4D4D] hidden sm:inline">•</span>
        <span className="font-semibold text-[#F2F2F2]">
          International T20I Records:{' '}
          <span className="text-[#D4AF57] font-bold tracking-wide">{t20iRange}</span>
        </span>
      </div>
    );
  };

  return (
    <ErrorBoundary title="Career Graph Analytics Error">
      <div className="w-full space-y-4 sm:space-y-5 font-sans text-[#F2F2F2]">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { to: '/dashboard', label: 'Dashboard' },
          { to: '/players', label: 'Players' },
          { label: 'Career Graph' },
        ]}
        backTo="/players"
        backLabel="Back to Players"
      />

      {/* Page Header */}
      <div className="bg-[#161616] rounded-lg p-4 sm:p-5 border border-[#2D2D2D] flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[#D4AF57] tracking-wider mb-1 uppercase">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Batting Evolution &amp; Contribution Trajectory</span>
          </div>
          <h1 className="font-heading text-xl sm:text-2xl lg:text-[26px] font-bold text-[#F2F2F2] tracking-tight leading-tight">
            Player Career Graph
          </h1>
          <p className="text-xs sm:text-[13.5px] text-[#B8B8B8] mt-1 max-w-3xl leading-relaxed">
            Explore how batting volume, scoring velocity, and CricImpact contribution metrics evolve across a player's career span in IPL, International T20Is, and Combined Career.
          </p>
        </div>

        {/* Player Search Bar with Autocomplete */}
        <div ref={searchRef} className="relative w-full lg:w-96 shrink-0">
          <div className="relative">
            <Search className="w-4 h-4 text-[#858585] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => {
                setSearchInput(e.target.value);
                setSearchOpen(true);
              }}
              onFocus={() => setSearchOpen(true)}
              placeholder="Search batter (e.g. Kohli, Rohit, Dhoni)..."
              className="w-full h-9 pl-9 pr-8 py-1 bg-[#101010] border border-[#2D2D2D] hover:border-[#D4AF57]/60 focus:border-[#D4AF57] rounded-md text-xs sm:text-[13px] text-[#F2F2F2] placeholder-[#666666] outline-hidden transition-all shadow-xs"
            />
            {searchInput && (
              <button
                type="button"
                onClick={() => {
                  setSearchInput('');
                  setSearchResults([]);
                }}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#858585] hover:text-[#F2F2F2]"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Autocomplete Dropdown */}
          {searchOpen && (
            <div className="absolute left-0 right-0 mt-1.5 bg-[#121212] border border-[#2D2D2D] rounded-xl shadow-2xl z-50 overflow-hidden max-h-80 overflow-y-auto">
              {searchLoading ? (
                <div className="p-4 text-center text-xs text-[#858585]">Searching batters...</div>
              ) : searchResults.length > 0 ? (
                <div className="divide-y divide-[#1F1F1F]">
                  {searchResults.map((res) => (
                    <button
                      key={res.player}
                      type="button"
                      onClick={() => handleSelectPlayer(res.player)}
                      className="w-full text-left p-2.5 hover:bg-[#1A1A1A] transition-colors flex items-center justify-between cursor-pointer"
                    >
                      <div>
                        <div className="font-semibold text-xs sm:text-sm text-[#F2F2F2]">{res.player}</div>
                        <div className="text-[11px] text-[#858585] truncate max-w-[240px]">
                          {res.teams?.join(', ') || 'Cricket Batter'}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs font-bold text-[#D4AF57] tabular-nums font-sans">
                          {res.total_runs?.toLocaleString()} runs
                        </div>
                        <div className="text-[10px] text-[#858585]">{res.career_span}</div>
                      </div>
                    </button>
                  ))}
                </div>
              ) : searchInput.trim().length > 0 ? (
                <div className="p-4 text-center text-xs text-[#858585]">No matching batters found.</div>
              ) : null}
            </div>
          )}
        </div>
      </div>

      {/* Featured Quick-Select Batters */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
        <span className="text-[#858585] font-semibold shrink-0 text-[11px]">Featured Batters:</span>
        {FEATURED_BATTERS.map((p) => {
          const isActive = selectedPlayer.toLowerCase() === p.toLowerCase();
          return (
            <button
              key={p}
              type="button"
              onClick={() => handleSelectPlayer(p)}
              className={`px-2.5 py-0.5 rounded-full border transition-all shrink-0 cursor-pointer text-[11px] ${
                isActive
                  ? 'bg-[#D4AF57] text-[#080808] font-bold border-[#D4AF57] shadow-xs'
                  : 'bg-[#101010] text-[#B8B8B8] hover:text-[#F2F2F2] hover:bg-[#181818] border-[#2D2D2D]'
              }`}
            >
              {p}
            </button>
          );
        })}
      </div>

      {/* Competition View Switcher & Data Coverage Indicator */}
      <div className="space-y-1.5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2.5 bg-[#161616] p-2 sm:p-2.5 rounded-lg border border-[#2D2D2D]">
          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              type="button"
              onClick={() => handleSelectCompetition('combined')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                competitionView === 'combined'
                  ? 'bg-[#D4AF57] text-[#080808] font-bold shadow-xs'
                  : 'text-[#858585] hover:text-[#F2F2F2] hover:bg-[#121212]'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Combined Career</span>
            </button>

            <button
              type="button"
              onClick={() => handleSelectCompetition('ipl')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                competitionView === 'ipl'
                  ? 'bg-[#D4AF57] text-[#080808] font-bold shadow-xs'
                  : 'text-[#858585] hover:text-[#F2F2F2] hover:bg-[#121212]'
              } ${!availableComps.ipl ? 'opacity-50' : ''}`}
              title={availableComps.ipl ? 'Indian Premier League records' : 'No IPL matches for this player'}
            >
              <Trophy className="w-3.5 h-3.5" />
              <span>IPL</span>
              {!availableComps.ipl && <span className="text-[10px] text-[#C25454]">(None)</span>}
            </button>

            <button
              type="button"
              onClick={() => handleSelectCompetition('t20i')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                competitionView === 't20i'
                  ? 'bg-[#D4AF57] text-[#080808] font-bold shadow-xs'
                  : 'text-[#858585] hover:text-[#F2F2F2] hover:bg-[#121212]'
              } ${!availableComps.t20i ? 'opacity-50' : ''}`}
              title={availableComps.t20i ? 'Men International T20 records' : 'No International T20 matches for this player'}
            >
              <Globe className="w-3.5 h-3.5" />
              <span>International (INL)</span>
              {!availableComps.t20i && <span className="text-[10px] text-[#C25454]">(None)</span>}
            </button>
          </div>

          {/* Compact Data Coverage Indicator */}
          <div className="flex items-center gap-2 px-2.5 py-1 bg-[#101010] rounded-md border border-[#D4AF57]/40 text-xs shadow-xs max-w-full flex-wrap">
            <Calendar className="w-3.5 h-3.5 text-[#D4AF57] shrink-0" />
            <span className="text-[#858585] text-[10.5px] font-semibold uppercase tracking-wider shrink-0">
              Data Coverage:
            </span>
            {renderCoverageIndicator()}
          </div>
        </div>

        {/* Coverage Context & Integrity Disclosure */}
        <div className="text-[11px] text-[#858585] px-1 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1">
          <span className="flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-[#A8893D] shrink-0" />
            <span>
              * Dataset coverage reflects available match records in CricImpact (
              {competitionView === 'ipl'
                ? `${datasetCoverage?.ipl?.total_matches?.toLocaleString() || '1,243'} IPL matches`
                : competitionView === 't20i'
                ? `${datasetCoverage?.t20i?.total_matches?.toLocaleString() || '665'} T20I matches`
                : `${datasetCoverage?.ipl?.total_matches?.toLocaleString() || '1,243'} IPL & ${datasetCoverage?.t20i?.total_matches?.toLocaleString() || '665'} T20I matches`}
              ); does not imply complete historical coverage of every tournament match.
            </span>
          </span>
          <span className="text-[#666666]">
            {competitionView === 'combined'
              ? 'Aggregated across IPL & International T20 records'
              : competitionView === 'ipl'
              ? 'Official Indian Premier League tournament records'
              : 'Men’s International T20 match records'}
          </span>
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="space-y-6 font-sans">
          <div className="p-6 rounded-xl bg-[#161616] border border-[#2D2D2D] text-center shadow-xs">
            <div className="inline-flex items-center gap-2 text-sm text-[#D4AF57] font-semibold animate-pulse">
              <TrendingUp className="w-4 h-4 animate-spin" />
              <span>Loading career trajectory for {selectedPlayer}...</span>
            </div>
            <p className="text-xs text-[#858585] mt-1.5">
              Synthesizing multi-season contribution scores, strike rates, and participation logs
            </p>
          </div>
          {/* Skeleton Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-24 bg-[#141414] rounded-xl border border-[#262626] p-3.5 animate-pulse" />
            ))}
          </div>
          {/* Skeleton Chart */}
          <div className="h-96 bg-[#141414] rounded-xl border border-[#262626] animate-pulse" />
        </div>
      ) : error ? (
        <div className="bg-[#161616] rounded-xl p-8 border border-[#4D2626] text-center space-y-4 font-sans shadow-xs">
          <div className="inline-flex p-3 rounded-full bg-[#271414] text-[#C25454] border border-[#4D2626]">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[#F2F2F2]">Unable to load career analytics</h2>
            <p className="text-xs sm:text-sm text-[#858585] max-w-md mx-auto mt-1">{error}</p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <button
              type="button"
              onClick={() => {
                setLoading(true);
                setError(null);
                getPlayerCareer(selectedPlayer, competitionView)
                  .then((data) => {
                    setCareerData(data);
                    setLoading(false);
                  })
                  .catch((err) => {
                    setError(err.message || 'Failed to load career data.');
                    setLoading(false);
                  });
              }}
              className="px-4 py-2 bg-[#D4AF57] hover:bg-[#E1C878] text-[#080808] font-bold text-xs rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
            <button
              type="button"
              onClick={() => handleSelectPlayer('V Kohli')}
              className="px-4 py-2 bg-[#1A1A1A] hover:bg-[#222222] border border-[#2D2D2D] hover:border-[#D4AF57] text-[#F2F2F2] text-xs font-semibold rounded-lg transition-colors cursor-pointer"
            >
              Reset to Virat Kohli
            </button>
          </div>
        </div>
      ) : !summary || summary.matches === 0 ? (
        <div className="bg-[#161616] rounded-xl p-8 border border-[#2D2D2D] text-center space-y-3 font-sans shadow-xs">
          <div className="text-[#F2F2F2] font-bold text-lg">No records for {selectedPlayer} in {competitionView.toUpperCase()}</div>
          <p className="text-xs sm:text-sm text-[#858585] max-w-md mx-auto">
            This player does not have recorded appearances in the selected competition scope. Try switching to Combined Career or another competition.
          </p>
          <div className="flex justify-center gap-2 pt-2">
            <button
              type="button"
              onClick={() => handleSelectCompetition('combined')}
              className="px-4 py-2 bg-[#D4AF57] hover:bg-[#E1C878] text-[#080808] font-bold text-xs rounded-lg transition-colors cursor-pointer"
            >
              View Combined Career
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* 1. CAREER SUMMARY BANNER & KPI CARDS */}
          <div className="bg-[#161616] rounded-lg p-3 sm:p-5 border border-[#2D2D2D] space-y-3 sm:space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[#222222] pb-3">
              <div>
                <div className="flex items-center gap-2.5">
                  <h2 className="text-xl sm:text-2xl font-bold text-[#F2F2F2] tracking-tight">
                    {summary.player}
                  </h2>
                  <span className="text-[10.5px] font-semibold px-2 py-0.5 rounded-full bg-[#1A1A1A] text-[#D4AF57] border border-[#A8893D]/40">
                    {summary.career_span}
                  </span>
                </div>
                <div className="text-xs text-[#858585] mt-0.5">
                  Teams: <span className="text-[#B8B8B8]">{summary.teams?.join(' • ') || 'Cricket Batter'}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 self-start md:self-auto">
                <Link
                  to={`/player/${encodeURIComponent(summary.player)}`}
                  className="px-2.5 py-1 bg-[#101010] border border-[#2D2D2D] hover:border-[#D4AF57] text-xs font-semibold rounded-md text-[#F2F2F2] transition-colors flex items-center gap-1.5"
                >
                  <span>Season Profile</span>
                  <ExternalLink className="w-3 h-3 text-[#D4AF57]" />
                </Link>
              </div>
            </div>

            {/* 6 Restrained KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-2.5 font-sans">
              {/* Card 1: Matches & Innings */}
              <div className="bg-[#101010] p-2 sm:p-3 rounded-lg border border-[#2D2D2D] flex flex-col justify-between">
                <div>
                  <span className="text-[10.5px] font-semibold text-[#858585] block">Matches &amp; Innings</span>
                  <div className="text-[18px] sm:text-[20px] font-bold text-[#F2F2F2] tabular-nums font-sans mt-0.5">
                    {summary.matches} <span className="text-[11px] text-[#858585] font-normal">matches</span>
                  </div>
                </div>
                <div className="text-[10.5px] text-[#858585] mt-1.5 pt-1 border-t border-[#222222]">
                  {summary.batting_innings} inn • {summary.dnb_matches} DNB
                </div>
              </div>

              {/* Card 2: Total Runs */}
              <div className="bg-[#101010] p-2 sm:p-3 rounded-lg border border-[#2D2D2D] flex flex-col justify-between">
                <div>
                  <span className="text-[10.5px] font-semibold text-[#858585] block">Career Runs</span>
                  <div className="text-[18px] sm:text-[20px] font-bold text-[#D4AF57] tabular-nums font-sans mt-0.5">
                    {summary.runs?.toLocaleString()}
                  </div>
                </div>
                <div className="text-[10.5px] text-[#858585] mt-1.5 pt-1 border-t border-[#222222]">
                  from {summary.balls_faced?.toLocaleString()} balls
                </div>
              </div>

              {/* Card 3: Strike Rate */}
              <div className="bg-[#101010] p-2 sm:p-3 rounded-lg border border-[#2D2D2D] flex flex-col justify-between">
                <div>
                  <span className="text-[10.5px] font-semibold text-[#858585] block">Career Strike Rate</span>
                  <div className="text-[18px] sm:text-[20px] font-bold text-[#F2F2F2] tabular-nums font-sans mt-0.5">
                    {summary.strike_rate ?? '—'}
                  </div>
                </div>
                <div className="text-[10.5px] text-[#858585] mt-1.5 pt-1 border-t border-[#222222]">
                  (Runs &divide; Balls) &times; 100
                </div>
              </div>

              {/* Card 4: Avg Contribution */}
              <div className="bg-[#101010] p-2 sm:p-3 rounded-lg border border-[#2D2D2D] flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10.5px] font-semibold text-[#858585]">Avg Contribution</span>
                    <span className="text-[10px] text-[#D4AF57] font-semibold">Par 50</span>
                  </div>
                  <div
                    className={`text-[18px] sm:text-[20px] font-bold tabular-nums font-sans mt-0.5 ${
                      summary.average_contribution >= 50.0 ? 'text-[#5A9E60]' : 'text-[#C25454]'
                    }`}
                  >
                    {summary.average_contribution?.toFixed(1) ?? '—'}
                  </div>
                </div>
                <div className="text-[10.5px] text-[#858585] mt-1.5 pt-1 border-t border-[#222222]">
                  {summary.average_contribution >= 50.0
                    ? `+${(summary.average_contribution - 50.0).toFixed(1)} above Par`
                    : `${(summary.average_contribution - 50.0).toFixed(1)} below Par`}
                </div>
              </div>

              {/* Card 5: Positive Contribution Rate */}
              <div className="bg-[#101010] p-2 sm:p-3 rounded-lg border border-[#2D2D2D] flex flex-col justify-between">
                <div>
                  <span className="text-[10.5px] font-semibold text-[#858585] block">Positive Contrib Rate</span>
                  <div className="text-[18px] sm:text-[20px] font-bold text-[#5A9E60] tabular-nums font-sans mt-0.5">
                    {summary.positive_contribution_rate !== null ? `${summary.positive_contribution_rate}%` : '—'}
                  </div>
                </div>
                <div className="text-[10.5px] text-[#858585] mt-1.5 pt-1 border-t border-[#222222]">
                  {summary.positive_appearances} / {summary.eligible_appearances} inn &gt; 50
                </div>
              </div>

              {/* Card 6: Dot-Ball Percentage */}
              <div className="bg-[#101010] p-2 sm:p-3 rounded-lg border border-[#2D2D2D] flex flex-col justify-between">
                <div>
                  <span className="text-[10.5px] font-semibold text-[#858585] block">Dot-Ball %</span>
                  <div className="text-[18px] sm:text-[20px] font-bold text-[#E1C878] tabular-nums font-sans mt-0.5">
                    {summary.dot_ball_percentage !== null ? `${summary.dot_ball_percentage}%` : '—'}
                  </div>
                </div>
                <div className="text-[10.5px] text-[#858585] mt-1.5 pt-1 border-t border-[#222222]">
                  {summary.dot_balls} / {summary.eligible_balls} balls
                </div>
              </div>
            </div>
          </div>

          {/* 2. FIVE INTERACTIVE CAREER GRAPHS SECTION */}
          <div className="space-y-4">
            {/* Graph Filter Tabs */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-[#222222] pb-2.5">
              <div>
                <h3 className="font-heading text-base sm:text-[17px] font-bold text-[#F2F2F2]">
                  Career Performance &amp; Contribution Trajectory
                </h3>
                <p className="text-xs text-[#858585] mt-0.5">
                  5 interactive analytical charts tracing season-by-season execution and impact.
                </p>
              </div>

              <div className="flex items-center gap-1 overflow-x-auto bg-[#161616] p-1 rounded-md border border-[#2D2D2D] text-xs">
                {[
                  { id: 'all', label: 'All Graphs' },
                  { id: 'bowling', label: 'Pace vs Spin' },
                  { id: 'runs', label: 'Runs' },
                  { id: 'sr', label: 'Strike Rate' },
                  { id: 'contrib', label: 'Avg Contribution' },
                  { id: 'pos', label: 'Positive Rate' },
                  { id: 'dots', label: 'Dot-Ball %' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveGraphTab(tab.id)}
                    className={`px-2.5 py-1 rounded transition-all cursor-pointer whitespace-nowrap text-xs ${
                      activeGraphTab === tab.id
                        ? 'bg-[#D4AF57] text-[#080808] font-bold shadow-xs'
                        : 'text-[#858585] hover:text-[#F2F2F2]'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Graphs Grid */}
            <div className="space-y-4 sm:space-y-5">
              {/* GRAPH A: Runs by Season/Year */}
              {(activeGraphTab === 'all' || activeGraphTab === 'runs') && (
                <div className="bg-[#161616] rounded-lg p-2.5 sm:p-4 border border-[#2D2D2D] shadow-xs space-y-2 sm:space-y-2.5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 border-b border-[#222222] pb-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold text-[#D4AF57] tracking-wider uppercase">Graph A</span>
                        <h4 className="font-heading text-sm sm:text-base font-bold text-[#F2F2F2]">
                          Runs by Season / Calendar Year
                        </h4>
                      </div>
                      <p className="text-[11px] text-[#858585] mt-0.5">
                        Volume of total runs scored per season. Hover bars to inspect batting innings and balls faced.
                      </p>
                    </div>
                  </div>
                  <CareerRunsChart timeline={timeline} isCombined={competitionView === 'combined'} />
                </div>
              )}

              {/* GRAPH B: Strike Rate Trend */}
              {(activeGraphTab === 'all' || activeGraphTab === 'sr') && (
                <div className="bg-[#161616] rounded-lg p-2.5 sm:p-4 border border-[#2D2D2D] shadow-xs space-y-2 sm:space-y-2.5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 border-b border-[#222222] pb-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold text-[#D4AF57] tracking-wider uppercase">Graph B</span>
                        <h4 className="font-heading text-sm sm:text-base font-bold text-[#F2F2F2]">
                          Strike Rate Trend
                        </h4>
                      </div>
                      <p className="text-[11px] text-[#858585] mt-0.5">
                        Scoring speed calculated as (Total Runs &divide; Balls Faced) &times; 100. Benchmarked against career SR.
                      </p>
                    </div>
                  </div>
                  <CareerStrikeRateChart timeline={timeline} />
                </div>
              )}

              {/* GRAPH C: Average Contribution Trend */}
              {(activeGraphTab === 'all' || activeGraphTab === 'contrib') && (
                <div className="bg-[#161616] rounded-lg p-2.5 sm:p-4 border border-[#2D2D2D] shadow-xs space-y-2 sm:space-y-2.5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 border-b border-[#222222] pb-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold text-[#D4AF57] tracking-wider uppercase">Graph C</span>
                        <h4 className="font-heading text-sm sm:text-base font-bold text-[#F2F2F2]">
                          Average Contribution Score Trend (Par = 50.0)
                        </h4>
                      </div>
                      <p className="text-[11px] text-[#858585] mt-0.5">
                        Contextual impact from Strategy 4 Hybrid engine. Values &gt; 50.0 indicate above-par team value addition.
                      </p>
                    </div>
                  </div>
                  <CareerContributionChart timeline={timeline} />
                </div>
              )}

              {/* 2-Column Grid for Graph D and Graph E when in 'all' view */}
              <div className={activeGraphTab === 'all' ? 'grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4' : 'space-y-3 sm:space-y-4'}>
                {/* GRAPH D: Positive Contribution Rate */}
                {(activeGraphTab === 'all' || activeGraphTab === 'pos') && (
                  <div className="bg-[#161616] rounded-lg p-2.5 sm:p-4 border border-[#2D2D2D] shadow-xs space-y-2 sm:space-y-2.5">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 border-b border-[#222222] pb-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-bold text-[#5A9E60] tracking-wider uppercase">Graph D</span>
                          <h4 className="font-heading text-sm sm:text-base font-bold text-[#F2F2F2]">
                            Positive Contribution Rate (%)
                          </h4>
                        </div>
                        <p className="text-[11px] text-[#858585] mt-0.5">
                          % of eligible batting innings exceeding Par (&gt; 50.0). DNB matches strictly excluded from denominator.
                        </p>
                      </div>
                    </div>
                    <CareerPositiveRateChart timeline={timeline} />
                  </div>
                )}

                {/* GRAPH E: Dot-Ball Percentage */}
                {(activeGraphTab === 'all' || activeGraphTab === 'dots') && (
                  <div className="bg-[#161616] rounded-lg p-2.5 sm:p-4 border border-[#2D2D2D] shadow-xs space-y-2 sm:space-y-2.5">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 border-b border-[#222222] pb-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-bold text-[#E1C878] tracking-wider uppercase">Graph E</span>
                          <h4 className="font-heading text-sm sm:text-base font-bold text-[#F2F2F2]">
                            Dot-Ball Percentage (%)
                          </h4>
                        </div>
                        <p className="text-[11px] text-[#858585] mt-0.5">
                          Delivery-level dot ball frequency. Lower dot % reflects elite strike rotation and defensive control.
                        </p>
                      </div>
                    </div>
                    <CareerDotBallChart timeline={timeline} />
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 3. BOWLING-TYPE PERFORMANCE TRENDS */}
          {(activeGraphTab === 'all' || activeGraphTab === 'bowling') && (
            <BowlingTypeTrendsChart
              bowlingTrends={careerData?.bowling_type_trends}
              competitionView={competitionView}
            />
          )}

          {/* 4. SEASON-BY-SEASON CAREER ARCHIVE TABLE */}
          <div className="bg-[#161616] rounded-lg border border-[#2D2D2D] shadow-xs overflow-hidden">
            <div className="p-3 sm:p-3.5 border-b border-[#2D2D2D] flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
              <div>
                <h3 className="font-heading text-sm sm:text-base font-bold text-[#F2F2F2]">
                  Season-by-Season Analytical Archive
                </h3>
                <p className="text-xs text-[#858585] mt-0.5">
                  Complete historical ledger of {summary.player}'s career data. Click column headers to sort.
                </p>
              </div>
              <div className="text-xs text-[#858585]">
                {sortedTimeline.length} recorded periods
              </div>
            </div>

            <div className="overflow-x-auto max-w-full">
              <table className="w-full text-left border-collapse font-sans">
                <thead>
                  <tr className="border-b border-[#2D2D2D] bg-[#121212] text-[#858585] text-[11px] font-semibold uppercase tracking-wider">
                    <th
                      className="py-2 px-3 cursor-pointer hover:text-[#F2F2F2]"
                      onClick={() => handleSort('season')}
                    >
                      <div className="flex items-center gap-1">
                        <span>Season / Year</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-2 px-2.5 text-center">Scope</th>
                    <th
                      className="py-2 px-2.5 text-right cursor-pointer hover:text-[#F2F2F2]"
                      onClick={() => handleSort('matches')}
                    >
                      <div className="flex items-center justify-end gap-1">
                        <span>Matches</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th
                      className="py-2 px-2.5 text-right cursor-pointer hover:text-[#F2F2F2]"
                      onClick={() => handleSort('batting_innings')}
                    >
                      <div className="flex items-center justify-end gap-1">
                        <span>Innings</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-2 px-2 text-right text-[#858585]">DNB</th>
                    <th
                      className="py-2 px-2.5 text-right cursor-pointer hover:text-[#F2F2F2]"
                      onClick={() => handleSort('runs')}
                    >
                      <div className="flex items-center justify-end gap-1">
                        <span>Runs</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th
                      className="py-2 px-2.5 text-right cursor-pointer hover:text-[#F2F2F2]"
                      onClick={() => handleSort('balls_faced')}
                    >
                      <div className="flex items-center justify-end gap-1">
                        <span>Balls</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th
                      className="py-2 px-2.5 text-right cursor-pointer hover:text-[#F2F2F2]"
                      onClick={() => handleSort('strike_rate')}
                    >
                      <div className="flex items-center justify-end gap-1">
                        <span>SR</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th
                      className="py-2 px-3 text-center cursor-pointer hover:text-[#F2F2F2]"
                      onClick={() => handleSort('average_contribution')}
                    >
                      <div className="flex items-center justify-center gap-1">
                        <span>Avg Contrib</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th
                      className="py-2 px-2.5 text-right cursor-pointer hover:text-[#F2F2F2]"
                      onClick={() => handleSort('positive_contribution_rate')}
                    >
                      <div className="flex items-center justify-end gap-1">
                        <span>Pos Rate</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-2 px-2.5 text-right text-[#858585]">Dots</th>
                    <th
                      className="py-2 px-2.5 text-right cursor-pointer hover:text-[#F2F2F2]"
                      onClick={() => handleSort('dot_ball_percentage')}
                    >
                      <div className="flex items-center justify-end gap-1">
                        <span>Dot %</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-[#222222] text-[#F2F2F2] text-xs">
                  {sortedTimeline.map((row) => {
                    const score = row.average_contribution;
                    const isAbovePar = score !== null && score >= 50.0;

                    return (
                      <tr
                        key={row.season}
                        id={`season-row-${row.season}`}
                        className="hover:bg-[#1A1A1A] transition-colors"
                      >
                        <td className="py-2 px-3 font-semibold text-[#F2F2F2] whitespace-nowrap">
                          {row.season}
                        </td>
                        <td className="py-2 px-2.5 text-center whitespace-nowrap">
                          <span className="text-[10.5px] font-medium px-1.5 py-0.5 rounded bg-[#101010] border border-[#2D2D2D] text-[#858585]">
                            {row.competition}
                          </span>
                        </td>
                        <td className="py-2 px-2.5 text-right tabular-nums text-[#858585]">
                          {row.matches}
                        </td>
                        <td className="py-2 px-2.5 text-right tabular-nums font-medium text-[#F2F2F2]">
                          {row.batting_innings}
                        </td>
                        <td className="py-2 px-2 text-right tabular-nums text-[#858585]">
                          {row.dnb_matches > 0 ? (
                            <span className="text-[#858585]">{row.dnb_matches}</span>
                          ) : (
                            '0'
                          )}
                        </td>
                        <td className="py-2 px-2.5 text-right tabular-nums font-bold text-[#F2F2F2]">
                          {row.runs}
                        </td>
                        <td className="py-2 px-2.5 text-right tabular-nums text-[#858585]">
                          {row.balls_faced}
                        </td>
                        <td className="py-2 px-2.5 text-right tabular-nums font-semibold text-[#D4AF57]">
                          {row.strike_rate !== null ? row.strike_rate : '—'}
                        </td>
                        <td className="py-2 px-3 text-center whitespace-nowrap">
                          {score !== null ? (
                            <span
                              className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold tabular-nums border ${
                                isAbovePar
                                  ? 'bg-[#152718] text-[#5A9E60] border-[#2A4D30]'
                                  : 'bg-[#271414] text-[#C25454] border-[#4D2626]'
                              }`}
                            >
                              {score.toFixed(1)}
                            </span>
                          ) : (
                            <span className="text-[#858585]">—</span>
                          )}
                        </td>
                        <td className="py-2 px-2.5 text-right tabular-nums font-semibold text-[#5A9E60]">
                          {row.positive_contribution_rate !== null
                            ? `${row.positive_contribution_rate}%`
                            : '—'}
                        </td>
                        <td className="py-2 px-2.5 text-right tabular-nums text-[#858585]">
                          {row.dot_balls}
                        </td>
                        <td className="py-2 px-2.5 text-right tabular-nums text-[#E1C878]">
                          {row.dot_ball_percentage !== null ? `${row.dot_ball_percentage}%` : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="p-3 bg-[#101010] border-t border-[#2D2D2D] text-[11px] text-[#858585] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1">
              <span>* Par Contribution = 50.0. Positive Rate measures % of innings with Contribution &gt; 50.0.</span>
              <span>* DNB matches are strictly excluded from denominators and return N/A.</span>
            </div>
          </div>

          {/* 4. CAREER HIGHS & LOWS SECTION (AT VERY BOTTOM) */}
          <CareerHighsLows
            player={selectedPlayer}
            competitionView={competitionView}
            highsLows={careerData?.career_highs_lows}
            timeline={timeline}
            onSelectSeason={(season) => {
              const el = document.getElementById(`season-row-${season}`);
              if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                el.classList.add('bg-[#2A2415]');
                setTimeout(() => {
                  el.classList.remove('bg-[#2A2415]');
                }, 2000);
              }
            }}
          />
        </>
      )}
      </div>
    </ErrorBoundary>
  );
}
