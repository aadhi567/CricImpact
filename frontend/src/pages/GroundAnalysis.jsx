import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  MapPin,
  Calendar,
  Shield,
  Zap,
  Trophy,
  RotateCcw,
  AlertTriangle,
  Info,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Search,
  TrendingUp,
  Layers,
  Globe,
  Clock,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { useWindowWidth } from '../hooks/useWindowWidth';
import Breadcrumbs from '../components/Breadcrumbs';
import { getGroundVenues, getGroundAnalysis } from '../services/api';

// Helper to get condition disclosure badge (only for non-standard / special conditions)
function getMatchConditionBadge(m) {
  // 1. Normal matches should not display a condition badge
  if (m.is_standard_20ov && !m.is_dls) {
    return null;
  }

  // 2. DLS / Rain-shortened
  if (
    m.is_dls ||
    (m.condition_label &&
      (m.condition_label.includes('DLS') ||
        m.condition_label.toLowerCase().includes('rain')))
  ) {
    return {
      label: 'DLS / Rain-shortened',
      className: 'bg-[#261B2E] text-[#D896FF] border border-[#4D2A61]',
    };
  }

  // 3. Unknown conditions disclosure
  if (m.condition_label && m.condition_label.toLowerCase().includes('unknown')) {
    return {
      label: 'Unknown Conditions',
      className: 'bg-[#222222] text-[#A3A3A3] border border-[#3E3E3E]',
    };
  }

  // 4. Reduced overs
  if (!m.is_standard_20ov && !m.is_no_result) {
    return {
      label: 'Reduced Overs',
      className: 'bg-[#2E1818] text-[#FFA85C] border border-[#522929]',
    };
  }

  return null;
}

export default function GroundAnalysis() {
  const { isMobile } = useWindowWidth();
  const [searchParams, setSearchParams] = useSearchParams();

  // URL state synchronization
  const venueFromUrl = searchParams.get('venue') || '';
  const compFromUrl = searchParams.get('competition') || 'combined';
  const countryFromUrl = searchParams.get('country') || 'All';
  const periodFromUrl = searchParams.get('period') || 'rolling_5yr';

  // Filter States
  const [selectedCompetition, setSelectedCompetition] = useState(compFromUrl);
  const [selectedCountry, setSelectedCountry] = useState(countryFromUrl);
  const [selectedVenueId, setSelectedVenueId] = useState(venueFromUrl);
  const [selectedPeriod, setSelectedPeriod] = useState(periodFromUrl);

  // Data States
  const [venuesData, setVenuesData] = useState(null);
  const [venuesLoading, setVenuesLoading] = useState(true);
  const [venuesError, setVenuesError] = useState(null);

  const [groundData, setGroundData] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);

  // Match History Table UI States
  const [matchSearch, setMatchSearch] = useState('');
  const [historyPage, setHistoryPage] = useState(1);
  const pageSize = 10;

  // Active trend chart view: 'scores' | 'chase_defend'
  const [trendView, setTrendView] = useState('scores');

  // Phase-wise Scoring Profile UI states
  const [phaseInningsView, setPhaseInningsView] = useState('combined'); // 'first_innings' | 'second_innings' | 'combined'
  const [phaseMetricView, setPhaseMetricView] = useState('runs'); // 'runs' | 'run_rate'
  const [phaseChartMode, setPhaseChartMode] = useState('compare'); // 'compare' | 'trends'

  // 1. Fetch available countries & venues whenever competition or country filter changes
  useEffect(() => {
    let cancelled = false;

    async function loadVenuesList() {
      setVenuesLoading(true);
      setVenuesError(null);
      try {
        const res = await getGroundVenues({
          competition: selectedCompetition,
          country: selectedCountry,
        });
        if (cancelled) return;
        setVenuesData(res);

        // If the current selected country is not in the returned countries list, reset to 'All'
        if (selectedCountry && selectedCountry !== 'All' && Array.isArray(res?.countries)) {
          const countryExists = res.countries.some(
            (c) => c.name.toLowerCase() === selectedCountry.toLowerCase()
          );
          if (!countryExists) {
            setSelectedCountry('All');
          }
        }

        // If currently selected venue is not in the new filtered venues, update it
        setSelectedVenueId((curr) => {
          const venueIds = (res.venues || []).map((v) => v.id);
          if (!curr || !venueIds.includes(curr)) {
            return res.default_venue || (res.venues && res.venues[0]?.id) || '';
          }
          return curr;
        });
      } catch (err) {
        if (!cancelled) {
          setVenuesError(err.message || 'Failed to load venues list.');
        }
      } finally {
        if (!cancelled) setVenuesLoading(false);
      }
    }

    loadVenuesList();
    return () => {
      cancelled = true;
    };
  }, [selectedCompetition, selectedCountry]);

  // 2. Fetch Ground Analysis details whenever selectedVenueId, selectedCompetition, or selectedPeriod changes
  useEffect(() => {
    let cancelled = false;

    async function loadAnalysis() {
      if (!selectedVenueId) return;

      setAnalysisLoading(true);
      setAnalysisError(null);
      try {
        const res = await getGroundAnalysis(selectedVenueId, {
          competition: selectedCompetition,
          period: selectedPeriod,
        });
        if (cancelled) return;
        setGroundData(res);
        setHistoryPage(1); // Reset match history table to page 1
      } catch (err) {
        if (!cancelled) {
          setAnalysisError(err.message || 'Failed to load ground analysis data.');
        }
      } finally {
        if (!cancelled) setAnalysisLoading(false);
      }
    }

    loadAnalysis();
    return () => {
      cancelled = true;
    };
  }, [selectedVenueId, selectedCompetition, selectedPeriod]);

  // 3. Keep URL search parameters updated
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedVenueId) params.set('venue', selectedVenueId);
    if (selectedCompetition && selectedCompetition !== 'combined') params.set('competition', selectedCompetition);
    if (selectedCountry && selectedCountry !== 'All') params.set('country', selectedCountry);
    if (selectedPeriod && selectedPeriod !== 'rolling_5yr') params.set('period', selectedPeriod);
    setSearchParams(params, { replace: true });
  }, [selectedVenueId, selectedCompetition, selectedCountry, selectedPeriod, setSearchParams]);

  // Handle Reset Filters
  const handleResetFilters = () => {
    setSelectedCompetition('combined');
    setSelectedCountry('All');
    setSelectedPeriod('rolling_5yr');
    if (venuesData?.default_venue) {
      setSelectedVenueId(venuesData.default_venue);
    } else {
      setSelectedVenueId('Wankhede Stadium, Mumbai');
    }
  };

  // Filtered Recent Matches for Table
  const filteredMatches = useMemo(() => {
    if (!groundData?.recent_matches) return [];
    if (!matchSearch.trim()) return groundData.recent_matches;
    const q = matchSearch.toLowerCase().trim();
    return groundData.recent_matches.filter(
      (m) =>
        m.team1.toLowerCase().includes(q) ||
        m.team2.toLowerCase().includes(q) ||
        m.winner.toLowerCase().includes(q) ||
        (m.result_description && m.result_description.toLowerCase().includes(q)) ||
        m.match_id.includes(q)
    );
  }, [groundData, matchSearch]);

  const totalPages = Math.ceil(filteredMatches.length / pageSize) || 1;
  const currentMatchesPage = useMemo(() => {
    const start = (historyPage - 1) * pageSize;
    return filteredMatches.slice(start, start + pageSize);
  }, [filteredMatches, historyPage, pageSize]);

  // Year trends data prepared for Recharts
  const trendChartData = useMemo(() => {
    if (!groundData?.year_trends) return [];
    return groundData.year_trends.map((t) => ({
      year: t.year.toString(),
      matches: t.matches,
      decided_matches: t.decided_matches,
      avg_first_innings: t.avg_first_innings ?? null,
      avg_second_innings: t.avg_second_innings ?? null,
      defend_pct: t.defend_pct ?? null,
      chase_pct: t.chase_pct ?? null,
      defend_wins: t.defend_wins,
      chase_wins: t.chase_wins,
    }));
  }, [groundData]);

  return (
    <div className="space-y-4 sm:space-y-6 pb-8">
      {/* 1. Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: 'Home', to: '/' },
          { label: 'Ground Analysis' },
        ]}
      />

      {/* 2. Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-[#2D2D2D] pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wider bg-[#D4AF57]/15 text-[#D4AF57] border border-[#D4AF57]/30 flex items-center gap-1.5">
              <MapPin className="w-3 h-3" />
              Venue Intelligence
            </span>
            <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#161616] text-[#A3A3A3] border border-[#2D2D2D]">
              T20 Cricket
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl lg:text-[26px] font-extrabold tracking-tight text-[#F2F2F2]">
            Ground Analysis
          </h1>
          <p className="text-xs sm:text-[13.5px] text-[#858585] mt-1 max-w-3xl leading-relaxed">
            Historical scoring profiles, chase versus defend rates, and winning score benchmarks across verified IPL and International T20 match records.
          </p>
        </div>

        <button
          type="button"
          onClick={handleResetFilters}
          className="self-start lg:self-center inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#B8B8B8] hover:text-[#F2F2F2] bg-[#161616] hover:bg-[#202020] border border-[#2D2D2D] rounded-md transition-colors cursor-pointer shadow-xs"
          title="Reset to default filters"
        >
          <RotateCcw className="w-3.5 h-3.5 text-[#D4AF57]" />
          <span>Reset Filters</span>
        </button>
      </div>

      {/* 3. Filter Controls: Competition, Country, Venue, Period */}
      <div className="bg-[#121212] border border-[#2D2D2D] rounded-lg p-3.5 sm:p-4 shadow-lg space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {/* A. Competition Scope */}
          <div>
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#A3A3A3] mb-1 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-[#D4AF57]" />
              Competition Scope
            </label>
            <div className="grid grid-cols-3 gap-1 bg-[#080808] p-1 rounded-md border border-[#2D2D2D] h-9 items-center">
              {[
                { id: 'combined', label: 'Combined' },
                { id: 'ipl', label: 'IPL' },
                { id: 't20i', label: 'T20I' },
              ].map((comp) => (
                <button
                  key={comp.id}
                  type="button"
                  onClick={() => setSelectedCompetition(comp.id)}
                  className={`h-7 px-1.5 text-[11px] sm:text-xs font-medium rounded transition-all text-center cursor-pointer flex items-center justify-center ${
                    selectedCompetition === comp.id
                      ? 'bg-[#1C1C1C] text-[#D4AF57] border border-[#D4AF57]/40 shadow-xs font-semibold'
                      : 'text-[#858585] hover:text-[#F2F2F2] hover:bg-[#141414]'
                  }`}
                >
                  {comp.label}
                </button>
              ))}
            </div>
          </div>

          {/* B. Country Selector */}
          <div>
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#A3A3A3] mb-1 flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-[#D4AF57]" />
              Country
            </label>
            <select
              value={selectedCountry}
              onChange={(e) => setSelectedCountry(e.target.value)}
              disabled={venuesLoading || !venuesData?.countries?.length}
              className="w-full bg-[#080808] h-9 text-[#F2F2F2] border border-[#2D2D2D] hover:border-[#404040] focus:border-[#D4AF57] focus:outline-hidden rounded-md px-2.5 py-1 text-xs sm:text-[13px] font-sans transition-colors cursor-pointer disabled:opacity-50"
            >
              {venuesLoading && !venuesData?.countries?.length ? (
                <option value="All">Loading countries...</option>
              ) : (
                <>
                  <option value="All">
                    All Countries ({venuesData?.countries?.reduce((acc, c) => acc + (c.match_count || 0), 0) || 0} matches)
                  </option>
                  {venuesData?.countries?.map((c) => (
                    <option key={c.name} value={c.name} label={`${c.name} (${c.match_count} matches)`}>
                      {c.name} ({c.match_count} matches)
                    </option>
                  ))}
                </>
              )}
            </select>
          </div>

          {/* C. Venue Selector */}
          <div>
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#A3A3A3] mb-1 flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-[#D4AF57]" />
              Selected Venue
            </label>
            <select
              value={selectedVenueId}
              onChange={(e) => setSelectedVenueId(e.target.value)}
              disabled={venuesLoading || !venuesData?.venues?.length}
              className="w-full bg-[#080808] h-9 text-[#F2F2F2] border border-[#2D2D2D] hover:border-[#404040] focus:border-[#D4AF57] focus:outline-hidden rounded-md px-2.5 py-1 text-xs sm:text-[13px] font-sans transition-colors cursor-pointer disabled:opacity-50"
            >
              {venuesLoading && !venuesData?.venues?.length ? (
                <option value="">Loading venues...</option>
              ) : !venuesData?.venues?.length ? (
                <option value="">No venues available</option>
              ) : (
                venuesData.venues.map((v) => (
                  <option key={v.id} value={v.id} label={v.name}>
                    {v.name}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* D. Period Selector */}
          <div>
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#A3A3A3] mb-1 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-[#D4AF57]" />
              Analysis Period
            </label>
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              className="w-full bg-[#080808] h-9 text-[#F2F2F2] border border-[#2D2D2D] hover:border-[#404040] focus:border-[#D4AF57] focus:outline-hidden rounded-md px-2.5 py-1 text-xs sm:text-[13px] font-sans transition-colors cursor-pointer"
            >
              <option value="rolling_5yr">Rolling 5-Year Window (Default)</option>
              <option value="rolling_3yr">Rolling 3-Year Window</option>
              <option value="all_time">All Time History (Full Dataset)</option>
            </select>
          </div>
        </div>

        {/* Dynamic Period Dates Notice */}
        {groundData?.filters && (
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#1F1F1F] text-xs text-[#858585]">
            <div className="flex items-center gap-2">
              <span className="text-[#A3A3A3] font-medium">Window Bounds:</span>
              <span className="text-[#D4AF57] font-semibold font-mono">
                {groundData.filters.start_date}
              </span>
              <span>to</span>
              <span className="text-[#D4AF57] font-semibold font-mono">
                {groundData.filters.end_date}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span>Scope:</span>
              <span className="text-[#F2F2F2] font-semibold capitalize">
                {groundData.filters.competition === 't20i'
                  ? 'International T20I'
                  : groundData.filters.competition === 'ipl'
                  ? 'Indian Premier League'
                  : 'Combined (IPL & T20I)'}
              </span>
              <span>•</span>
              <span>{groundData.summary.total_matches_in_period} matches in period</span>
            </div>
          </div>
        )}
      </div>

      {/* Venues Error State */}
      {venuesError && (
        <div className="bg-[#1A0A0A] border border-[#551E1E] rounded-xl p-5 text-sm text-[#FF7070] flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-[#FF5050] shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-semibold text-base text-[#F2F2F2]">Unable to load venues list</h4>
            <p className="text-[#C28585]">{venuesError}</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {analysisError && (
        <div className="bg-[#1A0A0A] border border-[#551E1E] rounded-xl p-5 text-sm text-[#FF7070] flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-[#FF5050] shrink-0 mt-0.5" />
          <div className="space-y-2">
            <h4 className="font-semibold text-base text-[#F2F2F2]">Unable to load ground analysis data</h4>
            <p className="text-[#C28585]">{analysisError}</p>
            <button
              type="button"
              onClick={() => {
                const nextVenue = selectedVenueId || 'Wankhede Stadium, Mumbai';
                setSelectedVenueId(nextVenue);
              }}
              className="px-3 py-1.5 text-xs bg-[#2B1010] hover:bg-[#3D1818] text-[#F2F2F2] border border-[#551E1E] rounded-md transition-colors cursor-pointer"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {analysisLoading && !groundData && (
        <div className="space-y-6 animate-pulse">
          <div className="h-28 bg-[#141414] border border-[#2D2D2D] rounded-xl" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-64 bg-[#141414] border border-[#2D2D2D] rounded-xl" />
            <div className="h-64 bg-[#141414] border border-[#2D2D2D] rounded-xl" />
          </div>
          <div className="h-44 bg-[#141414] border border-[#2D2D2D] rounded-xl" />
          <div className="h-80 bg-[#141414] border border-[#2D2D2D] rounded-xl" />
        </div>
      )}

      {/* Main Ground Analysis Content */}
      {groundData && (
        <div className="space-y-5 sm:space-y-6">
          {/* 4. Venue Metadata Banner & Data Coverage Disclosure */}
          <div className="bg-gradient-to-r from-[#141414] via-[#101010] to-[#141414] border border-[#2D2D2D] rounded-lg p-4 sm:p-5 shadow-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 w-96 h-96 bg-[#D4AF57]/5 rounded-full blur-3xl pointer-events-none" />

            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 relative z-10">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg sm:text-xl font-bold text-[#F2F2F2]">
                    {groundData.venue_info.name}
                  </h2>
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#1C1C1C] border border-[#383838] text-[#D4AF57]">
                    {groundData.venue_info.city}, {groundData.venue_info.country}
                  </span>
                </div>
                {groundData.venue_info.aliases?.length > 1 && (
                  <p className="text-xs text-[#707070]">
                    Known Aliases: {groundData.venue_info.aliases.join(' • ')}
                  </p>
                )}
              </div>

              {/* Match Totals Quick Pill */}
              <div className="flex items-center gap-2.5 bg-[#080808]/90 border border-[#2D2D2D] rounded-md px-3 py-1.5 self-start md:self-auto shrink-0 font-sans">
                <div className="text-center pr-2.5 border-r border-[#262626]">
                  <div className="text-base font-bold text-[#D4AF57] tabular-nums">
                    {groundData.summary.total_matches_in_period}
                  </div>
                  <div className="text-[10.5px] text-[#858585]">Matches in Period</div>
                </div>
                <div className="text-center pl-1">
                  <div className="text-base font-bold text-[#F2F2F2] tabular-nums">
                    {groundData.summary.total_matches_all_time}
                  </div>
                  <div className="text-[10.5px] text-[#858585]">All-Time Recorded</div>
                </div>
              </div>
            </div>

            {/* Coverage Disclosure Box */}
            <div className="mt-3 pt-3 border-t border-[#262626] flex flex-col sm:flex-row sm:items-start gap-2 text-xs text-[#858585] relative z-10">
              <Info className="w-3.5 h-3.5 text-[#D4AF57] shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="text-[#A3A3A3] leading-relaxed text-[11.5px]">
                  <strong className="text-[#F2F2F2]">Dataset Coverage Notice: </strong>
                  {groundData.summary.data_coverage_notice}
                </p>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[#707070]">
                  <span>
                    Scope Match Dates: <strong className="text-[#B8B8B8] font-mono">{groundData.summary.earliest_date_in_scope}</strong> to <strong className="text-[#B8B8B8] font-mono">{groundData.summary.latest_date_in_scope}</strong>
                  </span>
                  <span>•</span>
                  <span>
                    All-Time Venue Records: <strong className="text-[#B8B8B8] font-mono">{groundData.summary.dataset_earliest_date}</strong> to <strong className="text-[#B8B8B8] font-mono">{groundData.summary.dataset_latest_date}</strong>
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* 5. Venue Scoring Profile: 1st Innings vs 2nd Innings */}
          <section className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
              <div>
                <h3 className="text-base sm:text-[17px] font-bold text-[#F2F2F2] flex items-center gap-2">
                  <Zap className="w-4 h-4 text-[#D4AF57]" />
                  Venue Scoring Profile
                </h3>
                <p className="text-xs text-[#858585]">
                  Regulation completed innings only (20 overs or all-out). Rain-shortened and DLS adjusted innings are excluded.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">
              {/* 1st Innings Profile Card */}
              <div className="bg-[#121212] border border-[#2D2D2D] rounded-lg p-3.5 sm:p-4 shadow-md space-y-3">
                <div className="flex items-center justify-between border-b border-[#222222] pb-2.5">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-[#D4AF57]" />
                    <h4 className="font-semibold text-xs sm:text-sm text-[#F2F2F2]">
                      1st Innings Scoring
                    </h4>
                  </div>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-[#1C1C1C] border border-[#2D2D2D] text-[#A3A3A3] tabular-nums">
                    {groundData.scoring_profile.first_innings.sample_count} eligible innings
                  </span>
                </div>

                {/* Avg & Median Top Metrics */}
                <div className="grid grid-cols-2 gap-2.5">
                  <div className="bg-[#0A0A0A] border border-[#262626] rounded-md p-2.5 text-center">
                    <span className="text-[10px] uppercase font-semibold text-[#858585] tracking-wider block">
                      Average Score
                    </span>
                    <span className="text-xl sm:text-2xl font-extrabold text-[#D4AF57] tabular-nums mt-0.5 block">
                      {groundData.scoring_profile.first_innings.avg_score ?? '—'}
                    </span>
                  </div>
                  <div className="bg-[#0A0A0A] border border-[#262626] rounded-md p-2.5 text-center">
                    <span className="text-[10px] uppercase font-semibold text-[#858585] tracking-wider block">
                      Median Score
                    </span>
                    <span className="text-xl sm:text-2xl font-extrabold text-[#F2F2F2] tabular-nums mt-0.5 block">
                      {groundData.scoring_profile.first_innings.median_score ?? '—'}
                    </span>
                  </div>
                </div>

                {/* Highest & Lowest 1st Innings Totals */}
                <div className="space-y-1.5 pt-1 font-sans text-xs">
                  {/* Highest 1st Innings */}
                  {groundData.scoring_profile.first_innings.highest ? (
                    <div className="bg-[#0D0D0D] border border-[#222222] rounded-md p-2.5 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[#858585] font-semibold uppercase text-[10px] tracking-wider">
                          Highest 1st Innings Score
                        </span>
                        <Link
                          to={`/match/${groundData.scoring_profile.first_innings.highest.match_id}`}
                          className="text-[#D4AF57] hover:underline inline-flex items-center gap-1 text-[11px]"
                        >
                          View Match <ExternalLink className="w-2.5 h-2.5" />
                        </Link>
                      </div>
                      <div className="flex items-baseline justify-between pt-0.5">
                        <span className="text-base font-bold text-[#F2F2F2] tabular-nums">
                          {groundData.scoring_profile.first_innings.highest.score_str}
                        </span>
                        <span className="text-[#A3A3A3] font-medium text-right text-xs">
                          {groundData.scoring_profile.first_innings.highest.team} vs {groundData.scoring_profile.first_innings.highest.opponent}
                        </span>
                      </div>
                      <div className="text-[10.5px] text-[#707070] flex items-center justify-between pt-0.5">
                        <span>{groundData.scoring_profile.first_innings.highest.result_description}</span>
                        <span className="font-mono">{groundData.scoring_profile.first_innings.highest.date}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-[#707070] py-2">No eligible innings recorded.</div>
                  )}

                  {/* Lowest 1st Innings */}
                  {groundData.scoring_profile.first_innings.lowest && (
                    <div className="bg-[#0D0D0D] border border-[#222222] rounded-md p-2.5 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[#858585] font-semibold uppercase text-[10px] tracking-wider">
                          Lowest 1st Innings Score
                        </span>
                        <Link
                          to={`/match/${groundData.scoring_profile.first_innings.lowest.match_id}`}
                          className="text-[#D4AF57] hover:underline inline-flex items-center gap-1 text-[11px]"
                        >
                          View Match <ExternalLink className="w-2.5 h-2.5" />
                        </Link>
                      </div>
                      <div className="flex items-baseline justify-between pt-0.5">
                        <span className="text-base font-bold text-[#F2F2F2] tabular-nums">
                          {groundData.scoring_profile.first_innings.lowest.score_str}
                        </span>
                        <span className="text-[#A3A3A3] font-medium text-right text-xs">
                          {groundData.scoring_profile.first_innings.lowest.team} vs {groundData.scoring_profile.first_innings.lowest.opponent}
                        </span>
                      </div>
                      <div className="text-[10.5px] text-[#707070] flex items-center justify-between pt-0.5">
                        <span>{groundData.scoring_profile.first_innings.lowest.result_description}</span>
                        <span className="font-mono">{groundData.scoring_profile.first_innings.lowest.date}</span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="text-[10.5px] text-[#707070] pt-0.5">
                  *{groundData.scoring_profile.first_innings.eligibility_note}
                </div>
              </div>

              {/* 2nd Innings Profile Card */}
              <div className="bg-[#121212] border border-[#2D2D2D] rounded-lg p-3.5 sm:p-4 shadow-md space-y-3">
                <div className="flex items-center justify-between border-b border-[#222222] pb-2.5">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-[#5A9E60]" />
                    <h4 className="font-semibold text-xs sm:text-sm text-[#F2F2F2]">
                      2nd Innings (Chasing) Scoring
                    </h4>
                  </div>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-[#1C1C1C] border border-[#2D2D2D] text-[#A3A3A3] tabular-nums">
                    {groundData.scoring_profile.second_innings.sample_count} eligible innings
                  </span>
                </div>

                {/* Avg & Median Top Metrics */}
                <div className="grid grid-cols-2 gap-2.5">
                  <div className="bg-[#0A0A0A] border border-[#262626] rounded-md p-2.5 text-center">
                    <span className="text-[10px] uppercase font-semibold text-[#858585] tracking-wider block">
                      Average Score
                    </span>
                    <span className="text-xl sm:text-2xl font-extrabold text-[#5A9E60] tabular-nums mt-0.5 block">
                      {groundData.scoring_profile.second_innings.avg_score ?? '—'}
                    </span>
                  </div>
                  <div className="bg-[#0A0A0A] border border-[#262626] rounded-md p-2.5 text-center">
                    <span className="text-[10px] uppercase font-semibold text-[#858585] tracking-wider block">
                      Median Score
                    </span>
                    <span className="text-xl sm:text-2xl font-extrabold text-[#F2F2F2] tabular-nums mt-0.5 block">
                      {groundData.scoring_profile.second_innings.median_score ?? '—'}
                    </span>
                  </div>
                </div>

                {/* Highest & Lowest 2nd Innings Totals */}
                <div className="space-y-1.5 pt-1 font-sans text-xs">
                  {/* Highest 2nd Innings */}
                  {groundData.scoring_profile.second_innings.highest ? (
                    <div className="bg-[#0D0D0D] border border-[#222222] rounded-md p-2.5 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[#858585] font-semibold uppercase text-[10px] tracking-wider">
                          Highest 2nd Innings Total
                        </span>
                        <Link
                          to={`/match/${groundData.scoring_profile.second_innings.highest.match_id}`}
                          className="text-[#D4AF57] hover:underline inline-flex items-center gap-1 text-[11px]"
                        >
                          View Match <ExternalLink className="w-2.5 h-2.5" />
                        </Link>
                      </div>
                      <div className="flex items-baseline justify-between pt-0.5">
                        <span className="text-base font-bold text-[#F2F2F2] tabular-nums">
                          {groundData.scoring_profile.second_innings.highest.score_str}
                        </span>
                        <span className="text-[#A3A3A3] font-medium text-right text-xs">
                          {groundData.scoring_profile.second_innings.highest.team} vs {groundData.scoring_profile.second_innings.highest.opponent}
                        </span>
                      </div>
                      <div className="text-[10.5px] text-[#707070] flex items-center justify-between pt-0.5">
                        <span>{groundData.scoring_profile.second_innings.highest.result_description}</span>
                        <span className="font-mono">{groundData.scoring_profile.second_innings.highest.date}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-[#707070] py-2">No eligible innings recorded.</div>
                  )}

                  {/* Lowest 2nd Innings */}
                  {groundData.scoring_profile.second_innings.lowest && (
                    <div className="bg-[#0D0D0D] border border-[#222222] rounded-md p-2.5 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[#858585] font-semibold uppercase text-[10px] tracking-wider">
                          Lowest 2nd Innings Total
                        </span>
                        <Link
                          to={`/match/${groundData.scoring_profile.second_innings.lowest.match_id}`}
                          className="text-[#D4AF57] hover:underline inline-flex items-center gap-1 text-[11px]"
                        >
                          View Match <ExternalLink className="w-2.5 h-2.5" />
                        </Link>
                      </div>
                      <div className="flex items-baseline justify-between pt-0.5">
                        <span className="text-base font-bold text-[#F2F2F2] tabular-nums">
                          {groundData.scoring_profile.second_innings.lowest.score_str}
                        </span>
                        <span className="text-[#A3A3A3] font-medium text-right text-xs">
                          {groundData.scoring_profile.second_innings.lowest.team} vs {groundData.scoring_profile.second_innings.lowest.opponent}
                        </span>
                      </div>
                      <div className="text-[10.5px] text-[#707070] flex items-center justify-between pt-0.5">
                        <span>{groundData.scoring_profile.second_innings.lowest.result_description}</span>
                        <span className="font-mono">{groundData.scoring_profile.second_innings.lowest.date}</span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="text-[10.5px] text-[#707070] pt-0.5">
                  *{groundData.scoring_profile.second_innings.eligibility_note}
                </div>
              </div>
            </div>
          </section>

          {/* 6. Phase-Wise Scoring Profile (Powerplay, Middle Overs & Death Overs) */}
          <section className="bg-[#121212] border border-[#2D2D2D] rounded-lg p-4 sm:p-5 shadow-lg space-y-4">
            {/* Header & Innings Selector */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-[#222222] pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-[#D4AF57]" />
                  <h3 className="text-base sm:text-[17px] font-bold text-[#F2F2F2]">
                    Phase-Wise Scoring Profile
                  </h3>
                </div>
                <p className="text-xs text-[#858585] mt-0.5">
                  Actual ball-by-ball analysis across Powerplay (Overs 1–6), Middle Overs (Overs 7–15), and Death Overs (Overs 16–20).
                </p>
              </div>

              {/* Innings Selector Pills */}
              <div className="flex items-center gap-1.5 bg-[#080808] border border-[#262626] rounded-lg p-1 self-start sm:self-auto">
                <button
                  type="button"
                  onClick={() => setPhaseInningsView('first_innings')}
                  className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
                    phaseInningsView === 'first_innings'
                      ? 'bg-[#D4AF57] text-[#080808] shadow-sm'
                      : 'text-[#858585] hover:text-[#F2F2F2] hover:bg-[#1A1A1A]'
                  }`}
                >
                  1st Innings
                </button>
                <button
                  type="button"
                  onClick={() => setPhaseInningsView('second_innings')}
                  className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
                    phaseInningsView === 'second_innings'
                      ? 'bg-[#5A9E60] text-[#080808] shadow-sm'
                      : 'text-[#858585] hover:text-[#F2F2F2] hover:bg-[#1A1A1A]'
                  }`}
                >
                  2nd Innings
                </button>
                <button
                  type="button"
                  onClick={() => setPhaseInningsView('combined')}
                  className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
                    phaseInningsView === 'combined'
                      ? 'bg-[#3A6B9E] text-[#F2F2F2] shadow-sm'
                      : 'text-[#858585] hover:text-[#F2F2F2] hover:bg-[#1A1A1A]'
                  }`}
                >
                  Combined
                </button>
              </div>
            </div>

            {/* Scope Disclosure Banner */}
            {groundData.phase_analysis?.scope_summary && (
              <div className="bg-[#0A0A0A] border border-[#262626] rounded-xl p-3.5 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="flex items-start sm:items-center gap-2.5">
                  <Info className="w-4 h-4 text-[#D4AF57] shrink-0 mt-0.5 sm:mt-0" />
                  <span className="text-[#C4C4C4] leading-relaxed">
                    {groundData.phase_analysis.scope_summary.disclosure_text}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="px-2.5 py-0.5 rounded-full bg-[#142617] border border-[#234728] text-[#7AC57A] font-semibold tabular-nums text-[11px]">
                    {groundData.phase_analysis.scope_summary.eligible_standard_matches} Standard 20ov
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full bg-[#261B2E] border border-[#4D2A61] text-[#D896FF] font-semibold tabular-nums text-[11px]">
                    {groundData.phase_analysis.scope_summary.excluded_matches} Excluded
                  </span>
                </div>
              </div>
            )}

            {/* Current View Indicator & Full-Phase Eligibility Note */}
            <div className="text-xs text-[#858585] flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <span>
                Showing metrics for:{' '}
                <strong className="text-[#F2F2F2]">
                  {phaseInningsView === 'first_innings'
                    ? '1st Innings (Setting Target)'
                    : phaseInningsView === 'second_innings'
                    ? '2nd Innings (Chasing Target)'
                    : 'Combined (All Eligible Regulation Innings)'}
                </strong>
              </span>
              <span className="text-[11px] text-[#A3A3A3] italic" title="Phase statistics include only fully completed phases from eligible standard 20-over matches.">
                *Phase statistics include only fully completed phases from eligible standard 20-over matches.
              </span>
            </div>

            {/* 3 Phase Cards Grid */}
            {groundData.phase_analysis?.[phaseInningsView] && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                {['powerplay', 'middle', 'death'].map((phaseKey) => {
                  const pData = groundData.phase_analysis[phaseInningsView][phaseKey];
                  const phaseDotBg =
                    phaseKey === 'powerplay'
                      ? 'bg-[#D4AF57]'
                      : phaseKey === 'middle'
                      ? 'bg-[#3A6B9E]'
                      : 'bg-[#E5484D]';

                  return (
                    <div
                      key={phaseKey}
                      className="bg-[#0A0A0A] border border-[#262626] rounded-lg p-3.5 sm:p-4 flex flex-col justify-between space-y-3 shadow-md hover:border-[#383838] transition-colors"
                    >
                      {/* Card Header */}
                      <div className="flex items-start justify-between border-b border-[#1C1C1C] pb-2.5">
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className={`w-2 h-2 rounded-full ${phaseDotBg}`} />
                            <h4 className="font-bold text-[14.5px] text-[#F2F2F2]">
                              {pData.phase_name}
                            </h4>
                          </div>
                          <span className="text-[10.5px] font-mono text-[#858585] block">
                            {pData.overs_range}
                          </span>
                        </div>
                        <span
                          className="text-[10.5px] px-2 py-0.5 rounded-full bg-[#161616] border border-[#2D2D2D] text-[#A3A3A3] tabular-nums cursor-help"
                          title="Phase statistics include only fully completed phases from eligible standard 20-over matches."
                        >
                          {pData.sample_innings} eligible innings
                        </span>
                      </div>

                      {/* Card Content or Empty State */}
                      {pData.sample_innings === 0 ? (
                        <div className="py-8 px-4 text-center space-y-1 my-auto">
                          <p className="text-xs font-medium text-[#858585]">
                            No fully completed {pData.phase_name.toLowerCase()} recorded for this selection.
                          </p>
                          <p className="text-[10.5px] text-[#555555]">
                            Incomplete or unplayed phases are excluded from statistics.
                          </p>
                        </div>
                      ) : (
                        <>
                          {/* Primary Metrics: Avg & Median */}
                          <div className="grid grid-cols-2 gap-2.5">
                            <div className="bg-[#121212] border border-[#222222] rounded-md p-2.5 text-center">
                              <span className="text-[10px] uppercase font-semibold text-[#858585] tracking-wider block">
                                Average Runs
                              </span>
                              <span className="text-xl sm:text-2xl font-extrabold text-[#F2F2F2] tabular-nums mt-0.5 block">
                                {pData.avg_runs ?? '—'}
                              </span>
                            </div>
                            <div className="bg-[#121212] border border-[#222222] rounded-md p-2.5 text-center">
                              <span className="text-[10px] uppercase font-semibold text-[#858585] tracking-wider block">
                                Median Runs
                              </span>
                              <span className="text-xl sm:text-2xl font-extrabold text-[#F2F2F2] tabular-nums mt-0.5 block">
                                {pData.median_runs ?? '—'}
                              </span>
                            </div>
                          </div>

                          {/* Rate & Wickets Row */}
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="bg-[#121212] border border-[#222222] rounded-md px-2.5 py-1.5 flex items-center justify-between">
                              <span className="text-[#858585]">Run Rate:</span>
                              <span className="font-bold text-[#F2F2F2] tabular-nums font-mono text-[11.5px]">
                                {pData.run_rate !== null ? `${pData.run_rate} rpo` : '—'}
                              </span>
                            </div>
                            <div className="bg-[#121212] border border-[#222222] rounded-md px-2.5 py-1.5 flex items-center justify-between">
                              <span className="text-[#858585]">Avg Wickets:</span>
                              <span className="font-bold text-[#F2F2F2] tabular-nums font-mono text-[11.5px]">
                                {pData.avg_wickets !== null ? `${pData.avg_wickets} wkts` : '—'}
                              </span>
                            </div>
                          </div>

                          {/* Ball-by-ball Dot & Boundary Percentages */}
                          <div className="bg-[#121212] border border-[#222222] rounded-md p-2.5 space-y-1.5">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-[#858585]">Dot-Ball %</span>
                              <span className="font-mono font-semibold text-[#F2F2F2] tabular-nums text-[11.5px]">
                                {pData.dot_percentage !== null ? `${pData.dot_percentage}%` : '—'}
                              </span>
                            </div>
                            <div className="w-full bg-[#1E1E1E] h-1.5 rounded-full overflow-hidden">
                              <div
                                className="bg-[#A3A3A3] h-full rounded-full"
                                style={{ width: `${Math.min(pData.dot_percentage || 0, 100)}%` }}
                              />
                            </div>

                            <div className="flex items-center justify-between text-xs pt-0.5">
                              <span className="text-[#858585]">Boundary %</span>
                              <span className="font-mono font-semibold text-[#D4AF57] tabular-nums text-[11.5px]">
                                {pData.boundary_percentage !== null ? `${pData.boundary_percentage}%` : '—'}
                              </span>
                            </div>
                            <div className="w-full bg-[#1E1E1E] h-1.5 rounded-full overflow-hidden">
                              <div
                                className="bg-[#D4AF57] h-full rounded-full"
                                style={{ width: `${Math.min(pData.boundary_percentage || 0, 100)}%` }}
                              />
                            </div>
                          </div>

                          {/* Observed Extremes: Highest & Lowest Phase Scores */}
                          <div className="space-y-1.5 text-xs">
                            {pData.highest && (
                              <div className="bg-[#121212] border border-[#222222] rounded-md p-2 space-y-0.5">
                                <div className="flex items-center justify-between text-[10px]">
                                  <span className="uppercase font-semibold text-[#707070] tracking-wider">
                                    Highest Phase Score
                                  </span>
                                  <Link
                                    to={`/match/${pData.highest.match_id}`}
                                    className="text-[#D4AF57] hover:underline inline-flex items-center gap-1 text-[10.5px]"
                                  >
                                    View <ExternalLink className="w-2.5 h-2.5" />
                                  </Link>
                                </div>
                                <div className="flex items-baseline justify-between">
                                  <span className="font-bold text-xs sm:text-sm text-[#F2F2F2] tabular-nums font-mono">
                                    {pData.highest.score_str}
                                  </span>
                                  <span className="text-[10.5px] text-[#A3A3A3] truncate max-w-[140px]">
                                    {pData.highest.team} vs {pData.highest.opponent}
                                  </span>
                                </div>
                                <div className="text-[10px] text-[#707070] flex justify-between">
                                  <span className="truncate max-w-[130px]">{pData.highest.result_description}</span>
                                  <span className="font-mono">{pData.highest.date}</span>
                                </div>
                              </div>
                            )}

                            {pData.lowest && (
                              <div className="bg-[#121212] border border-[#222222] rounded-md p-2 space-y-0.5">
                                <div className="flex items-center justify-between text-[10px]">
                                  <span className="uppercase font-semibold text-[#707070] tracking-wider">
                                    Lowest Phase Score
                                  </span>
                                  <Link
                                    to={`/match/${pData.lowest.match_id}`}
                                    className="text-[#D4AF57] hover:underline inline-flex items-center gap-1 text-[10.5px]"
                                  >
                                    View <ExternalLink className="w-2.5 h-2.5" />
                                  </Link>
                                </div>
                                <div className="flex items-baseline justify-between">
                                  <span className="font-bold text-xs sm:text-sm text-[#F2F2F2] tabular-nums font-mono">
                                    {pData.lowest.score_str}
                                  </span>
                                  <span className="text-[10.5px] text-[#A3A3A3] truncate max-w-[140px]">
                                    {pData.lowest.team} vs {pData.lowest.opponent}
                                  </span>
                                </div>
                                <div className="text-[10px] text-[#707070] flex justify-between">
                                  <span className="truncate max-w-[130px]">{pData.lowest.result_description}</span>
                                  <span className="font-mono">{pData.lowest.date}</span>
                                </div>
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Venue Scoring Progression & Acceleration Insight Card */}
            {groundData.phase_analysis?.progression_insights && (
              <div className="bg-[#0A0A0A] border border-[#262626] rounded-lg p-3.5 sm:p-4 shadow-md space-y-3">
                <div className="flex items-center justify-between border-b border-[#1C1C1C] pb-2.5">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-[#D4AF57]" />
                    <h4 className="font-semibold text-xs sm:text-sm text-[#F2F2F2]">
                      Venue Scoring Progression & Acceleration
                    </h4>
                  </div>
                  <span className="text-[10.5px] px-2 py-0.5 rounded-full bg-[#1C1C1C] border border-[#2D2D2D] text-[#A3A3A3]">
                    Historical Pattern
                  </span>
                </div>

                {/* Progression Bar Comparison */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <div className="bg-[#121212] border border-[#222222] rounded-md p-2.5">
                    <span className="text-[10px] uppercase font-semibold text-[#858585] tracking-wider block">
                      Powerplay Run Rate
                    </span>
                    <span className="text-lg font-bold text-[#F2F2F2] tabular-nums font-mono mt-0.5 block">
                      {groundData.phase_analysis.progression_insights.powerplay_run_rate !== null
                        ? `${groundData.phase_analysis.progression_insights.powerplay_run_rate} rpo`
                        : '—'}
                    </span>
                    <span className="text-[10.5px] text-[#707070] mt-0.5 block">
                      Avg wickets: {groundData.phase_analysis.progression_insights.pp_avg_wickets ?? '—'}
                    </span>
                  </div>

                  <div className="bg-[#121212] border border-[#222222] rounded-md p-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-semibold text-[#858585] tracking-wider">
                        Middle Overs Run Rate
                      </span>
                      {groundData.phase_analysis.progression_insights.pp_to_middle_diff !== null && (
                        <span
                          className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                            groundData.phase_analysis.progression_insights.pp_to_middle_diff >= 0
                              ? 'bg-[#142617] text-[#7AC57A]'
                              : 'bg-[#2E1818] text-[#FF8587]'
                          }`}
                        >
                          {groundData.phase_analysis.progression_insights.pp_to_middle_diff >= 0 ? '+' : ''}
                          {groundData.phase_analysis.progression_insights.pp_to_middle_diff}
                        </span>
                      )}
                    </div>
                    <span className="text-lg font-bold text-[#6BA8E5] tabular-nums font-mono mt-0.5 block">
                      {groundData.phase_analysis.progression_insights.middle_run_rate !== null
                        ? `${groundData.phase_analysis.progression_insights.middle_run_rate} rpo`
                        : '—'}
                    </span>
                    <span className="text-[10.5px] text-[#707070] mt-0.5 block">
                      Avg wickets: {groundData.phase_analysis.progression_insights.middle_avg_wickets ?? '—'}
                    </span>
                  </div>

                  <div className="bg-[#121212] border border-[#222222] rounded-md p-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-semibold text-[#858585] tracking-wider">
                        Death Overs Run Rate
                      </span>
                      {groundData.phase_analysis.progression_insights.middle_to_death_diff !== null && (
                        <span
                          className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                            groundData.phase_analysis.progression_insights.middle_to_death_diff >= 0
                              ? 'bg-[#142617] text-[#7AC57A]'
                              : 'bg-[#2E1818] text-[#FF8587]'
                          }`}
                        >
                          {groundData.phase_analysis.progression_insights.middle_to_death_diff >= 0 ? '+' : ''}
                          {groundData.phase_analysis.progression_insights.middle_to_death_diff}
                        </span>
                      )}
                    </div>
                    <span className="text-lg font-bold text-[#D4AF57] tabular-nums font-mono mt-0.5 block">
                      {groundData.phase_analysis.progression_insights.death_run_rate !== null
                        ? `${groundData.phase_analysis.progression_insights.death_run_rate} rpo`
                        : '—'}
                    </span>
                    <span className="text-[10.5px] text-[#707070] mt-0.5 block">
                      Avg wickets: {groundData.phase_analysis.progression_insights.death_avg_wickets ?? '—'}
                    </span>
                  </div>
                </div>

                {/* Analytical Narrative */}
                <div className="bg-[#121212] border border-[#1F1F1F] rounded-md p-3 space-y-1.5 text-xs">
                  <p className="text-[#E0E0E0] leading-relaxed text-[11.5px]">
                    {groundData.phase_analysis.progression_insights.rate_insight}
                  </p>
                  <p className="text-[#A3A3A3] leading-relaxed">
                    {groundData.phase_analysis.progression_insights.wicket_insight}
                  </p>
                  <p className="text-[11px] text-[#707070] italic pt-1 border-t border-[#1A1A1A]">
                    {groundData.phase_analysis.progression_insights.context_note}
                  </p>
                </div>
              </div>
            )}

            {/* Visualizations: Phase Comparison & Year-wise Trends */}
            <div className="space-y-4 pt-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#222222] pb-3">
                <div className="flex items-center gap-2">
                  <BarChart className="w-4 h-4 text-[#D4AF57]" />
                  <h4 className="font-semibold text-sm text-[#F2F2F2]">
                    Phase Scoring Visualizations
                  </h4>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {/* Mode Selector: Compare Phases vs Annual Trends */}
                  <div className="flex items-center gap-1 bg-[#080808] border border-[#262626] rounded-lg p-1 text-xs">
                    <button
                      type="button"
                      onClick={() => setPhaseChartMode('compare')}
                      className={`px-2.5 py-1 rounded font-medium transition-all ${
                        phaseChartMode === 'compare'
                          ? 'bg-[#1C1C1C] text-[#F2F2F2] border border-[#333333]'
                          : 'text-[#858585] hover:text-[#F2F2F2]'
                      }`}
                    >
                      Phase Comparison
                    </button>
                    <button
                      type="button"
                      onClick={() => setPhaseChartMode('trends')}
                      className={`px-2.5 py-1 rounded font-medium transition-all ${
                        phaseChartMode === 'trends'
                          ? 'bg-[#1C1C1C] text-[#F2F2F2] border border-[#333333]'
                          : 'text-[#858585] hover:text-[#F2F2F2]'
                      }`}
                    >
                      Year-Wise Trends
                    </button>
                  </div>

                  {/* Metric Toggle: Runs vs Run Rate */}
                  <div className="flex items-center gap-1 bg-[#080808] border border-[#262626] rounded-lg p-1 text-xs">
                    <button
                      type="button"
                      onClick={() => setPhaseMetricView('runs')}
                      className={`px-2.5 py-1 rounded font-medium transition-all ${
                        phaseMetricView === 'runs'
                          ? 'bg-[#D4AF57] text-[#080808]'
                          : 'text-[#858585] hover:text-[#F2F2F2]'
                      }`}
                    >
                      Average Runs
                    </button>
                    <button
                      type="button"
                      onClick={() => setPhaseMetricView('run_rate')}
                      className={`px-2.5 py-1 rounded font-medium transition-all ${
                        phaseMetricView === 'run_rate'
                          ? 'bg-[#D4AF57] text-[#080808]'
                          : 'text-[#858585] hover:text-[#F2F2F2]'
                      }`}
                    >
                      Run Rate (rpo)
                    </button>
                  </div>
                </div>
              </div>

              {/* Chart Canvas */}
              {phaseChartMode === 'compare' ? (
                <div className="bg-[#0A0A0A] border border-[#262626] rounded-xl p-3 sm:p-5 h-[260px] sm:h-[340px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={groundData.phase_analysis?.comparison_chart || []}
                      margin={
                        isMobile
                          ? { top: 15, right: 10, left: -20, bottom: 5 }
                          : { top: 15, right: 20, left: 0, bottom: 5 }
                      }
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
                      <XAxis
                        dataKey="phase_name"
                        stroke="#707070"
                        fontSize={isMobile ? 10 : 11}
                        tickLine={false}
                      />
                      <YAxis
                        stroke="#707070"
                        fontSize={isMobile ? 10 : 11}
                        tickLine={false}
                        axisLine={false}
                        domain={[0, 'auto']}
                        unit={phaseMetricView === 'run_rate' ? ' rpo' : ''}
                      />
                      <Tooltip
                        content={({ active, payload, label }) => {
                          if (active && payload && payload.length) {
                            const d = payload[0].payload;
                            const isRr = phaseMetricView === 'run_rate';
                            return (
                              <div className="bg-[#121212] border border-[#2D2D2D] rounded-lg p-2.5 sm:p-3 text-xs shadow-xl space-y-1.5 max-w-[calc(100vw-32px)] sm:max-w-xs pointer-events-none select-none backdrop-blur-xs">
                                <div className="font-bold text-[#F2F2F2] border-b border-[#222222] pb-1">
                                  {d.phase_name || label}
                                </div>
                                <div className="space-y-1 pt-0.5">
                                  {payload.map((entry, index) => (
                                    <div key={index} className="flex items-center justify-between gap-3">
                                      <span className="flex items-center gap-1.5 text-[#A3A3A3]">
                                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                                        <span>{entry.name}:</span>
                                      </span>
                                      <span className="font-bold text-[#F2F2F2] tabular-nums font-mono">
                                        {entry.value !== null && entry.value !== undefined
                                          ? isRr
                                            ? `${entry.value} rpo`
                                            : `${entry.value} runs`
                                          : '—'}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                                <div className="border-t border-[#1C1C1C] pt-1.5 text-[10px] text-[#707070] space-y-0.5">
                                  <div className="flex justify-between">
                                    <span>Sample Innings:</span>
                                    <span className="text-[#A3A3A3] tabular-nums font-mono">
                                      {d.combined_sample} inn ({d.combined_matches} matches)
                                    </span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span>Scope:</span>
                                    <span className="text-[#A3A3A3]">
                                      {selectedCompetition === 'ipl' ? 'IPL' : selectedCompetition === 't20i' ? 'T20I' : 'Combined'} • {groundData?.filters?.period_label?.split(' ')[0] || 'Period'}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Legend
                        verticalAlign="top"
                        align={isMobile ? 'center' : 'right'}
                        iconType="circle"
                        wrapperStyle={{ fontSize: isMobile ? '10px' : '11px', paddingBottom: '12px' }}
                      />
                      <Bar
                        dataKey={phaseMetricView === 'run_rate' ? 'first_innings_run_rate' : 'first_innings_avg_runs'}
                        name="1st Innings"
                        fill="#D4AF57"
                        radius={[4, 4, 0, 0]}
                        maxBarSize={48}
                      />
                      <Bar
                        dataKey={phaseMetricView === 'run_rate' ? 'second_innings_run_rate' : 'second_innings_avg_runs'}
                        name="2nd Innings"
                        fill="#5A9E60"
                        radius={[4, 4, 0, 0]}
                        maxBarSize={48}
                      />
                      <Bar
                        dataKey={phaseMetricView === 'run_rate' ? 'combined_run_rate' : 'combined_avg_runs'}
                        name="Combined"
                        fill="#3A6B9E"
                        radius={[4, 4, 0, 0]}
                        maxBarSize={48}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="bg-[#0A0A0A] border border-[#262626] rounded-xl p-3 sm:p-5 h-[260px] sm:h-[340px]">
                  {groundData.phase_analysis?.year_trends?.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={groundData.phase_analysis.year_trends}
                        margin={
                          isMobile
                            ? { top: 15, right: 10, left: -20, bottom: 5 }
                            : { top: 15, right: 20, left: 0, bottom: 5 }
                        }
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
                        <XAxis
                          dataKey="year"
                          stroke="#707070"
                          fontSize={isMobile ? 10 : 11}
                          tickLine={false}
                          interval={isMobile ? 'preserveStartEnd' : 0}
                        />
                        <YAxis
                          stroke="#707070"
                          fontSize={isMobile ? 10 : 11}
                          tickLine={false}
                          axisLine={false}
                          domain={[0, 'auto']}
                          unit={phaseMetricView === 'run_rate' ? ' rpo' : ''}
                        />
                        <Tooltip
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const d = payload[0].payload;
                              const isRr = phaseMetricView === 'run_rate';
                              return (
                                <div className="bg-[#121212] border border-[#2D2D2D] rounded-lg p-2.5 sm:p-3 text-xs shadow-xl space-y-1.5 max-w-[calc(100vw-32px)] sm:max-w-xs pointer-events-none select-none backdrop-blur-xs">
                                  <div className="font-bold text-[#F2F2F2] border-b border-[#222222] pb-1">
                                    Year {d.year} ({d.matches} matches)
                                  </div>
                                  <div className="space-y-1 pt-0.5">
                                    {payload.map((entry, index) => (
                                      <div key={index} className="flex items-center justify-between gap-3">
                                        <span className="flex items-center gap-1.5 text-[#A3A3A3]">
                                          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                                          <span>{entry.name}:</span>
                                        </span>
                                        <span className="font-bold text-[#F2F2F2] tabular-nums font-mono">
                                          {entry.value !== null && entry.value !== undefined
                                            ? isRr
                                              ? `${entry.value} rpo`
                                              : `${entry.value} runs`
                                            : '—'}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                  <div className="border-t border-[#1C1C1C] pt-1.5 text-[10px] text-[#707070]">
                                    <span>Scope: Standard 20-over matches</span>
                                  </div>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <Legend
                          verticalAlign="top"
                          align={isMobile ? 'center' : 'right'}
                          iconType="circle"
                          wrapperStyle={{ fontSize: isMobile ? '10px' : '11px', paddingBottom: '12px' }}
                        />
                        <Bar
                          dataKey={phaseMetricView === 'run_rate' ? 'powerplay_run_rate' : 'powerplay_avg_runs'}
                          name="Powerplay"
                          fill="#D4AF57"
                          radius={[3, 3, 0, 0]}
                          maxBarSize={28}
                        />
                        <Bar
                          dataKey={phaseMetricView === 'run_rate' ? 'middle_run_rate' : 'middle_avg_runs'}
                          name="Middle Overs"
                          fill="#3A6B9E"
                          radius={[3, 3, 0, 0]}
                          maxBarSize={28}
                        />
                        <Bar
                          dataKey={phaseMetricView === 'run_rate' ? 'death_run_rate' : 'death_avg_runs'}
                          name="Death Overs"
                          fill="#E5484D"
                          radius={[3, 3, 0, 0]}
                          maxBarSize={28}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-xs text-[#707070]">
                      No multi-year standard match trends recorded for selected filters.
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>

          {/* 7. Successful Defending vs Successful Chasing (Chase vs Defend) */}
          <section className="bg-[#121212] border border-[#2D2D2D] rounded-lg p-4 sm:p-5 shadow-lg space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#222222] pb-3">
              <div>
                <h3 className="text-base sm:text-[17px] font-bold text-[#F2F2F2] flex items-center gap-2">
                  <Shield className="w-4 h-4 text-[#D4AF57]" />
                  Chase vs Defend Breakdown
                </h3>
                <p className="text-xs text-[#858585] mt-0.5">
                  Decided matches with verified innings outcomes. Denominator excludes ties, super overs, and abandoned matches.
                </p>
              </div>

              <div className="flex items-center gap-2 text-xs">
                <span className="text-[#858585]">Decided Matches:</span>
                <span className="px-2.5 py-0.5 rounded-full bg-[#1C1C1C] border border-[#2D2D2D] text-[#F2F2F2] font-semibold tabular-nums text-[11px]">
                  {groundData.chase_vs_defend.decided_matches} of {groundData.chase_vs_defend.total_matches}
                </span>
              </div>
            </div>

            {/* KPI Cards & Outcomes Summary */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {/* Defending Wins */}
              <div className="bg-[#0A0A0A] border border-[#262626] rounded-lg p-3 sm:p-3.5 flex flex-col justify-between">
                <div>
                  <span className="text-[11px] uppercase font-semibold text-[#858585] tracking-wider flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-[#D4AF57]" />
                    Defending Wins (Bat 1st)
                  </span>
                  <div className="mt-1.5 flex items-baseline gap-2">
                    <span className="text-2xl sm:text-[26px] font-extrabold text-[#D4AF57] tabular-nums">
                      {groundData.chase_vs_defend.defend_pct !== null ? `${groundData.chase_vs_defend.defend_pct}%` : 'N/A'}
                    </span>
                    <span className="text-xs text-[#858585] font-semibold tabular-nums">
                      ({groundData.chase_vs_defend.defend_wins} wins)
                    </span>
                  </div>
                </div>
                <div className="text-[10.5px] text-[#707070] mt-1.5 pt-1.5 border-t border-[#1C1C1C]">
                  Won defending 1st innings total
                </div>
              </div>

              {/* Chasing Wins */}
              <div className="bg-[#0A0A0A] border border-[#262626] rounded-lg p-3 sm:p-3.5 flex flex-col justify-between">
                <div>
                  <span className="text-[11px] uppercase font-semibold text-[#858585] tracking-wider flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-[#5A9E60]" />
                    Chasing Wins (Bat 2nd)
                  </span>
                  <div className="mt-1.5 flex items-baseline gap-2">
                    <span className="text-2xl sm:text-[26px] font-extrabold text-[#5A9E60] tabular-nums">
                      {groundData.chase_vs_defend.chase_pct !== null ? `${groundData.chase_vs_defend.chase_pct}%` : 'N/A'}
                    </span>
                    <span className="text-xs text-[#858585] font-semibold tabular-nums">
                      ({groundData.chase_vs_defend.chase_wins} wins)
                    </span>
                  </div>
                </div>
                <div className="text-[10.5px] text-[#707070] mt-1.5 pt-1.5 border-t border-[#1C1C1C]">
                  Won chasing in 2nd innings
                </div>
              </div>

              {/* Ties & Super Overs */}
              <div className="bg-[#0A0A0A] border border-[#262626] rounded-lg p-3 sm:p-3.5 flex flex-col justify-between">
                <div>
                  <span className="text-[11px] uppercase font-semibold text-[#858585] tracking-wider">
                    Ties & Super Overs
                  </span>
                  <div className="mt-1.5 flex items-baseline gap-2">
                    <span className="text-2xl sm:text-[26px] font-extrabold text-[#F2F2F2] tabular-nums">
                      {groundData.chase_vs_defend.ties_super_overs}
                    </span>
                    <span className="text-xs text-[#858585]">
                      {groundData.chase_vs_defend.ties_super_overs === 1 ? 'match' : 'matches'}
                    </span>
                  </div>
                </div>
                <div className="text-[10.5px] text-[#707070] mt-1.5 pt-1.5 border-t border-[#1C1C1C]">
                  Decided via super over or tied
                </div>
              </div>

              {/* No Results & Abandoned */}
              <div className="bg-[#0A0A0A] border border-[#262626] rounded-lg p-3 sm:p-3.5 flex flex-col justify-between">
                <div>
                  <span className="text-[11px] uppercase font-semibold text-[#858585] tracking-wider">
                    No Results / Abandoned
                  </span>
                  <div className="mt-1.5 flex items-baseline gap-2">
                    <span className="text-2xl sm:text-[26px] font-extrabold text-[#707070] tabular-nums">
                      {groundData.chase_vs_defend.no_results_abandoned}
                    </span>
                    <span className="text-xs text-[#858585]">
                      {groundData.chase_vs_defend.no_results_abandoned === 1 ? 'match' : 'matches'}
                    </span>
                  </div>
                </div>
                <div className="text-[10.5px] text-[#707070] mt-1.5 pt-1.5 border-t border-[#1C1C1C]">
                  Rain washed out or abandoned
                </div>
              </div>
            </div>

            {/* Visual Split Bar */}
            {groundData.chase_vs_defend.decided_matches > 0 && (
              <div className="space-y-1.5 pt-1">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-[#D4AF57] flex items-center gap-1.5">
                    <span>Defending Won</span>
                    <span className="font-mono text-[#F2F2F2]">
                      {groundData.chase_vs_defend.defend_pct}% ({groundData.chase_vs_defend.defend_wins})
                    </span>
                  </span>
                  <span className="text-[#5A9E60] flex items-center gap-1.5">
                    <span className="font-mono text-[#F2F2F2]">
                      {groundData.chase_vs_defend.chase_pct}% ({groundData.chase_vs_defend.chase_wins})
                    </span>
                    <span>Chasing Won</span>
                  </span>
                </div>

                <div className="h-3.5 w-full bg-[#1A1A1A] rounded-full overflow-hidden flex border border-[#2D2D2D]">
                  <div
                    style={{ width: `${groundData.chase_vs_defend.defend_pct || 0}%` }}
                    className="h-full bg-gradient-to-r from-[#B8963D] to-[#D4AF57] transition-all duration-500"
                    title={`Defend Wins: ${groundData.chase_vs_defend.defend_pct}%`}
                  />
                  <div
                    style={{ width: `${groundData.chase_vs_defend.chase_pct || 0}%` }}
                    className="h-full bg-gradient-to-r from-[#44804A] to-[#5A9E60] transition-all duration-500"
                    title={`Chase Wins: ${groundData.chase_vs_defend.chase_pct}%`}
                  />
                </div>

                <div className="text-[10.5px] text-[#707070] text-center pt-0.5">
                  *{groundData.chase_vs_defend.calculation_note}
                </div>
              </div>
            )}
          </section>

          {/* 7. Historical Winning Scores & Benchmarks */}
          <section className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
              <div>
                <h3 className="text-base sm:text-[17px] font-bold text-[#F2F2F2] flex items-center gap-2">
                  <Trophy className="w-4 h-4 text-[#D4AF57]" />
                  Historical Winning Score Benchmarks
                </h3>
                <p className="text-xs text-[#858585]">
                  Observations from regulation matches; excludes shortened/DLS targets.
                </p>
              </div>

              {groundData.historical_winning_scores.warning && (
                <div className="flex items-center gap-1.5 text-xs text-[#E5A84B] bg-[#221808] border border-[#4D3612] px-2.5 py-0.5 rounded">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span>{groundData.historical_winning_scores.warning}</span>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {/* Benchmark 1: Lowest Successful Defense */}
              <div className="bg-[#121212] border border-[#2D2D2D] rounded-lg p-3.5 shadow-sm flex flex-col justify-between">
                <div>
                  <span className="text-[10.5px] uppercase font-semibold text-[#858585] tracking-wider block">
                    Lowest Successful Defense
                  </span>
                  {groundData.historical_winning_scores.lowest_successful_defense ? (
                    <div className="mt-1.5 space-y-1">
                      <div className="flex items-baseline justify-between">
                        <span className="text-xl sm:text-2xl font-extrabold text-[#D4AF57] tabular-nums">
                          {groundData.historical_winning_scores.lowest_successful_defense.first_innings_score}
                        </span>
                        <span className="text-xs text-[#858585] font-mono">
                          {groundData.historical_winning_scores.lowest_successful_defense.score_str}
                        </span>
                      </div>
                      <div className="text-xs text-[#F2F2F2] font-semibold">
                        {groundData.historical_winning_scores.lowest_successful_defense.defending_team}
                      </div>
                      <div className="text-[11px] text-[#A3A3A3]">
                        defended vs {groundData.historical_winning_scores.lowest_successful_defense.chasing_team}
                      </div>
                      <div className="text-[10.5px] text-[#707070]">
                        Chased: {groundData.historical_winning_scores.lowest_successful_defense.chasing_score_str}
                      </div>
                      <div className="text-[10.5px] text-[#858585] font-mono">
                        {groundData.historical_winning_scores.lowest_successful_defense.date}
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-[#707070] py-3">No defending wins in period</div>
                  )}
                </div>

                {groundData.historical_winning_scores.lowest_successful_defense && (
                  <div className="mt-2.5 pt-2 border-t border-[#1F1F1F]">
                    <Link
                      to={`/match/${groundData.historical_winning_scores.lowest_successful_defense.match_id}`}
                      className="text-xs text-[#D4AF57] hover:underline inline-flex items-center gap-1"
                    >
                      Inspect Match <ExternalLink className="w-3 h-3" />
                    </Link>
                  </div>
                )}
              </div>

              {/* Benchmark 2: Highest Successful Chase */}
              <div className="bg-[#121212] border border-[#2D2D2D] rounded-lg p-3.5 shadow-sm flex flex-col justify-between">
                <div>
                  <span className="text-[10.5px] uppercase font-semibold text-[#858585] tracking-wider block">
                    Highest Successful Chase
                  </span>
                  {groundData.historical_winning_scores.highest_successful_chase ? (
                    <div className="mt-1.5 space-y-1">
                      <div className="flex items-baseline justify-between">
                        <span className="text-xl sm:text-2xl font-extrabold text-[#5A9E60] tabular-nums">
                          {groundData.historical_winning_scores.highest_successful_chase.chase_score}
                        </span>
                        <span className="text-xs text-[#858585] font-mono">
                          {groundData.historical_winning_scores.highest_successful_chase.score_str}
                        </span>
                      </div>
                      <div className="text-xs text-[#F2F2F2] font-semibold">
                        {groundData.historical_winning_scores.highest_successful_chase.chasing_team}
                      </div>
                      <div className="text-[11px] text-[#A3A3A3]">
                        Target hunted: {groundData.historical_winning_scores.highest_successful_chase.first_innings_score_str}
                      </div>
                      <div className="text-[10.5px] text-[#707070]">
                        {groundData.historical_winning_scores.highest_successful_chase.result_description}
                      </div>
                      <div className="text-[10.5px] text-[#858585] font-mono">
                        {groundData.historical_winning_scores.highest_successful_chase.date}
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-[#707070] py-3">No chasing wins in period</div>
                  )}
                </div>

                {groundData.historical_winning_scores.highest_successful_chase && (
                  <div className="mt-2.5 pt-2 border-t border-[#1F1F1F]">
                    <Link
                      to={`/match/${groundData.historical_winning_scores.highest_successful_chase.match_id}`}
                      className="text-xs text-[#D4AF57] hover:underline inline-flex items-center gap-1"
                    >
                      Inspect Match <ExternalLink className="w-3 h-3" />
                    </Link>
                  </div>
                )}
              </div>

              {/* Benchmark 4: Typical Winning Score (Median) */}
              <div className="bg-[#121212] border border-[#2D2D2D] rounded-lg p-3.5 shadow-sm flex flex-col justify-between">
                <div>
                  <span className="text-[10.5px] uppercase font-semibold text-[#858585] tracking-wider block">
                    Typical Winning Total
                  </span>
                  <div className="mt-1.5 space-y-1">
                    <div className="flex items-baseline justify-between">
                      <span className="text-xl sm:text-2xl font-extrabold text-[#F2F2F2] tabular-nums">
                        {groundData.historical_winning_scores.typical_winning_score.overall_median ?? '—'}
                      </span>
                      <span className="text-[11px] text-[#858585]">
                        Overall Median
                      </span>
                    </div>

                    <div className="space-y-0.5 pt-1 border-t border-[#1F1F1F] text-xs">
                      <div className="flex items-center justify-between text-[#D4AF57]">
                        <span>• Defending Median:</span>
                        <span className="font-bold tabular-nums">
                          {groundData.historical_winning_scores.typical_winning_score.defending_median ?? '—'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[#5A9E60]">
                        <span>• Chasing Median:</span>
                        <span className="font-bold tabular-nums">
                          {groundData.historical_winning_scores.typical_winning_score.chasing_median ?? '—'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-2.5 pt-2 border-t border-[#1F1F1F] text-[10.5px] text-[#707070]">
                  Based on {groundData.historical_winning_scores.typical_winning_score.sample_count} winning match scores
                </div>
              </div>
            </div>
          </section>

          {/* 8. Season and Year Trends */}
          <section className="bg-[#121212] border border-[#2D2D2D] rounded-lg p-4 sm:p-5 shadow-lg space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#222222] pb-3">
              <div>
                <h3 className="text-base sm:text-[17px] font-bold text-[#F2F2F2] flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-[#D4AF57]" />
                  Season & Year-by-Year Trends
                </h3>
                <p className="text-xs text-[#858585] mt-0.5">
                  Historical progression of scoring standards and chase vs defend win rates at this venue over time.
                </p>
              </div>

              {/* Chart Mode Toggle */}
              <div className="flex items-center bg-[#080808] p-1 rounded-lg border border-[#2D2D2D] self-start sm:self-auto">
                <button
                  type="button"
                  onClick={() => setTrendView('scores')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer ${
                    trendView === 'scores'
                      ? 'bg-[#1C1C1C] text-[#D4AF57] border border-[#D4AF57]/40 shadow-xs font-semibold'
                      : 'text-[#858585] hover:text-[#F2F2F2]'
                  }`}
                >
                  Innings Scoring Trends
                </button>
                <button
                  type="button"
                  onClick={() => setTrendView('chase_defend')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer ${
                    trendView === 'chase_defend'
                      ? 'bg-[#1C1C1C] text-[#D4AF57] border border-[#D4AF57]/40 shadow-xs font-semibold'
                      : 'text-[#858585] hover:text-[#F2F2F2]'
                  }`}
                >
                  Defend vs Chase Win %
                </button>
              </div>
            </div>

            {/* Trends Chart */}
            {trendChartData.length > 0 ? (
              <div className="h-56 sm:h-72 md:h-80 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  {trendView === 'scores' ? (
                    <BarChart
                      data={trendChartData}
                      margin={
                        isMobile
                          ? { top: 15, right: 10, left: -20, bottom: 5 }
                          : { top: 15, right: 20, left: -10, bottom: 10 }
                      }
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
                      <XAxis
                        dataKey="year"
                        stroke="#606060"
                        fontSize={isMobile ? 10 : 12}
                        tickLine={false}
                        axisLine={{ stroke: '#2D2D2D' }}
                        interval={isMobile ? 'preserveStartEnd' : 0}
                      />
                      <YAxis
                        stroke="#606060"
                        fontSize={isMobile ? 10 : 12}
                        domain={[100, 'auto']}
                        tickLine={false}
                        axisLine={{ stroke: '#2D2D2D' }}
                        unit=" r"
                      />
                      <Tooltip
                        content={({ active, payload, label }) => {
                          if (!active || !payload?.length) return null;
                          const d = payload[0].payload;
                          return (
                            <div className="bg-[#101010] border border-[#2D2D2D] rounded-lg p-2.5 sm:p-3 text-xs shadow-2xl text-[#F2F2F2] max-w-[calc(100vw-32px)] sm:max-w-xs pointer-events-none select-none backdrop-blur-xs">
                              <div className="font-bold border-b border-[#222222] pb-1.5 mb-1.5 flex items-center justify-between">
                                <span className="text-[#D4AF57]">Season {label}</span>
                                <span className="text-[#858585] text-[11px]">{d.matches} matches</span>
                              </div>
                              <div className="space-y-1 font-sans">
                                <div className="flex items-center justify-between text-[#D4AF57]">
                                  <span>Avg 1st Innings:</span>
                                  <span className="font-bold tabular-nums">
                                    {d.avg_first_innings ?? '—'}
                                  </span>
                                </div>
                                <div className="flex items-center justify-between text-[#5A9E60]">
                                  <span>Avg 2nd Innings:</span>
                                  <span className="font-bold tabular-nums">
                                    {d.avg_second_innings ?? '—'}
                                  </span>
                                </div>
                              </div>
                            </div>
                          );
                        }}
                      />
                      <Legend
                        verticalAlign="top"
                        align={isMobile ? 'center' : 'right'}
                        height={36}
                        payload={[
                          { value: 'Avg 1st Innings', type: 'rect', id: 'avg_first_innings', color: '#D4AF57' },
                          { value: 'Avg 2nd Innings', type: 'rect', id: 'avg_second_innings', color: '#5A9E60' },
                        ]}
                        formatter={(val) => (
                          <span className="text-[10px] sm:text-xs text-[#B8B8B8] font-medium mr-2 sm:mr-4">
                            {val}
                          </span>
                        )}
                      />
                      <Bar
                        dataKey="avg_first_innings"
                        name="Avg 1st Innings"
                        fill="#D4AF57"
                        radius={[4, 4, 0, 0]}
                        maxBarSize={isMobile ? 28 : 45}
                      />
                      <Bar
                        dataKey="avg_second_innings"
                        name="Avg 2nd Innings"
                        fill="#5A9E60"
                        radius={[4, 4, 0, 0]}
                        maxBarSize={isMobile ? 28 : 45}
                      />
                    </BarChart>
                  ) : (
                    <BarChart
                      data={trendChartData}
                      margin={
                        isMobile
                          ? { top: 15, right: 10, left: -20, bottom: 5 }
                          : { top: 15, right: 20, left: -10, bottom: 10 }
                      }
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#222222" vertical={false} />
                      <XAxis
                        dataKey="year"
                        stroke="#606060"
                        fontSize={isMobile ? 10 : 12}
                        tickLine={false}
                        axisLine={{ stroke: '#2D2D2D' }}
                        interval={isMobile ? 'preserveStartEnd' : 0}
                      />
                      <YAxis
                        stroke="#606060"
                        fontSize={isMobile ? 10 : 12}
                        domain={[0, 100]}
                        tickLine={false}
                        axisLine={{ stroke: '#2D2D2D' }}
                        unit="%"
                      />
                      <Tooltip
                        content={({ active, payload, label }) => {
                          if (!active || !payload?.length) return null;
                          const d = payload[0].payload;
                          return (
                            <div className="bg-[#101010] border border-[#2D2D2D] rounded-lg p-2.5 sm:p-3 text-xs shadow-2xl text-[#F2F2F2] max-w-[calc(100vw-32px)] sm:max-w-xs pointer-events-none select-none backdrop-blur-xs">
                              <div className="font-bold border-b border-[#222222] pb-1.5 mb-1.5 flex items-center justify-between">
                                <span className="text-[#D4AF57]">Season {label}</span>
                                <span className="text-[#858585] text-[11px]">
                                  {d.decided_matches} decided matches
                                </span>
                              </div>
                              <div className="space-y-1 font-sans">
                                <div className="flex items-center justify-between text-[#D4AF57]">
                                  <span>Defend Win %:</span>
                                  <span className="font-bold tabular-nums">
                                    {d.defend_pct !== null ? `${d.defend_pct}%` : 'N/A'} ({d.defend_wins} wins)
                                  </span>
                                </div>
                                <div className="flex items-center justify-between text-[#5A9E60]">
                                  <span>Chase Win %:</span>
                                  <span className="font-bold tabular-nums">
                                    {d.chase_pct !== null ? `${d.chase_pct}%` : 'N/A'} ({d.chase_wins} wins)
                                  </span>
                                </div>
                              </div>
                            </div>
                          );
                        }}
                      />
                      <Legend
                        verticalAlign="top"
                        align={isMobile ? 'center' : 'right'}
                        height={36}
                        payload={[
                          { value: 'Defend Win %', type: 'rect', id: 'defend_pct', color: '#D4AF57' },
                          { value: 'Chase Win %', type: 'rect', id: 'chase_pct', color: '#5A9E60' },
                        ]}
                        formatter={(val) => (
                          <span className="text-[10px] sm:text-xs text-[#B8B8B8] font-medium mr-2 sm:mr-4">
                            {val}
                          </span>
                        )}
                      />
                      <Bar
                        dataKey="defend_pct"
                        name="Defend Win %"
                        fill="#D4AF57"
                        radius={[4, 4, 0, 0]}
                        maxBarSize={isMobile ? 28 : 45}
                      />
                      <Bar
                        dataKey="chase_pct"
                        name="Chase Win %"
                        fill="#5A9E60"
                        radius={[4, 4, 0, 0]}
                        maxBarSize={isMobile ? 28 : 45}
                      />
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="text-center py-10 text-xs text-[#858585]">
                No annual trend records available for this selection.
              </div>
            )}

            {/* Annual Summary Table */}
            <div className="overflow-x-auto pt-2 border-t border-[#1F1F1F]">
              <table className="w-full text-xs text-left">
                <thead className="bg-[#0A0A0A] text-[#858585] font-semibold border-b border-[#222222]">
                  <tr>
                    <th className="py-2.5 px-3">Year</th>
                    <th className="py-2.5 px-3 text-right">Matches</th>
                    <th className="py-2.5 px-3 text-right">Decided</th>
                    <th className="py-2.5 px-3 text-right">Avg 1st Inn</th>
                    <th className="py-2.5 px-3 text-right">Avg 2nd Inn</th>
                    <th className="py-2.5 px-3 text-right">Defend Wins (%)</th>
                    <th className="py-2.5 px-3 text-right">Chase Wins (%)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1A1A1A] text-[#F2F2F2]">
                  {trendChartData.map((row) => (
                    <tr key={row.year} className="hover:bg-[#161616]/60 transition-colors">
                      <td className="py-2 px-3 font-semibold text-[#D4AF57]">{row.year}</td>
                      <td className="py-2 px-3 text-right tabular-nums text-[#A3A3A3]">{row.matches}</td>
                      <td className="py-2 px-3 text-right tabular-nums text-[#A3A3A3]">{row.decided_matches}</td>
                      <td className="py-2 px-3 text-right tabular-nums font-medium text-[#F2F2F2]">
                        {row.avg_first_innings ?? '—'}
                      </td>
                      <td className="py-2 px-3 text-right tabular-nums font-medium text-[#F2F2F2]">
                        {row.avg_second_innings ?? '—'}
                      </td>
                      <td className="py-2 px-3 text-right tabular-nums text-[#D4AF57]">
                        {row.defend_pct !== null ? `${row.defend_pct}%` : '—'}
                      </td>
                      <td className="py-2 px-3 text-right tabular-nums text-[#5A9E60]">
                        {row.chase_pct !== null ? `${row.chase_pct}%` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* 9. Recent Match History Table */}
          <section className="bg-[#121212] border border-[#2D2D2D] rounded-lg p-4 sm:p-5 shadow-lg space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-[#222222] pb-3">
              <div>
                <h3 className="text-base sm:text-[17px] font-bold text-[#F2F2F2] flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-[#D4AF57]" />
                  Match History at Venue ({filteredMatches.length})
                </h3>
                <p className="text-xs text-[#858585] mt-0.5">
                  Chronological match outcomes from the selected analysis period (newest matches first).
                </p>
              </div>

              {/* Match Search Input */}
              <div className="relative w-full sm:w-64">
                <Search className="w-3.5 h-3.5 text-[#707070] absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  placeholder="Filter by team or match ID..."
                  value={matchSearch}
                  onChange={(e) => {
                    setMatchSearch(e.target.value);
                    setHistoryPage(1);
                  }}
                  className="w-full h-8 bg-[#080808] text-[#F2F2F2] border border-[#2D2D2D] hover:border-[#404040] focus:border-[#D4AF57] focus:outline-hidden rounded-md pl-8 pr-2.5 py-1 text-xs transition-colors"
                />
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-[#0A0A0A] text-[#858585] font-semibold border-b border-[#222222]">
                  <tr>
                    <th className="py-2 px-2.5 sm:px-3 text-[11px] uppercase tracking-wider">Date</th>
                    <th className="py-2 px-2.5 sm:px-3 text-[11px] uppercase tracking-wider">Tournament</th>
                    <th className="py-2 px-2.5 sm:px-3 text-[11px] uppercase tracking-wider">Matchup</th>
                    <th className="py-2 px-2.5 sm:px-3 text-[11px] uppercase tracking-wider">1st Innings</th>
                    <th className="py-2 px-2.5 sm:px-3 text-[11px] uppercase tracking-wider">2nd Innings</th>
                    <th className="py-2 px-2.5 sm:px-3 text-[11px] uppercase tracking-wider">Result / Margin</th>
                    <th className="py-2 px-2.5 sm:px-3 text-[11px] uppercase tracking-wider text-center">Status</th>
                    <th className="py-2 px-2.5 sm:px-3 text-[11px] uppercase tracking-wider text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1A1A1A] text-[#F2F2F2]">
                  {currentMatchesPage.length > 0 ? (
                    currentMatchesPage.map((m) => (
                      <tr key={m.match_id} className="hover:bg-[#181818]/80 transition-colors">
                        <td className="py-2 px-2.5 sm:px-3 font-mono text-[#A3A3A3] whitespace-nowrap text-xs">
                          {m.date}
                        </td>
                        <td className="py-2 px-2.5 sm:px-3 whitespace-nowrap">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                              m.competition_code === 'ipl'
                                ? 'bg-[#D4AF57]/15 text-[#D4AF57] border border-[#D4AF57]/30'
                                : 'bg-[#3A6B9E]/20 text-[#6BA8E5] border border-[#3A6B9E]/30'
                            }`}
                          >
                            {m.competition}
                          </span>
                        </td>
                        <td className="py-2 px-2.5 sm:px-3">
                          <div className="font-medium text-[#F2F2F2] whitespace-nowrap text-xs">
                            <span>{m.team1}</span>
                            <span className="text-[#707070] mx-1">vs</span>
                            <span>{m.team2}</span>
                          </div>
                        </td>
                        <td className="py-2 px-2.5 sm:px-3 whitespace-nowrap">
                          <div className="font-mono text-[#E0E0E0] text-xs">{m.innings1_score}</div>
                          <div className="text-[10px] text-[#707070] truncate max-w-[120px]">
                            {m.innings1_team}
                          </div>
                        </td>
                        <td className="py-2 px-2.5 sm:px-3 whitespace-nowrap">
                          <div className="font-mono text-[#E0E0E0] text-xs">{m.innings2_score}</div>
                          <div className="text-[10px] text-[#707070] truncate max-w-[120px]">
                            {m.innings2_team}
                          </div>
                        </td>
                        <td className="py-2 px-2.5 sm:px-3">
                          <div className="font-medium text-[#D4AF57] text-xs">
                            {m.winner !== 'N/A' && m.winner ? `${m.winner}` : 'No Winner'}
                          </div>
                          <div className="text-[10.5px] text-[#858585] truncate max-w-[170px]">
                            {m.result_description}
                          </div>
                        </td>
                        <td className="py-2 px-2.5 sm:px-3 text-center whitespace-nowrap">
                          {/* Outcome / Result Badge */}
                          {m.is_no_result ? (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-[#2E2E2E] text-[#9E9E9E] border border-[#444444]">
                              No Result
                            </span>
                          ) : m.is_super_over ? (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-[#422B10] text-[#FFB347] border border-[#7A4E1B]">
                              Super Over
                            </span>
                          ) : (
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                m.result_type === 'defend_win'
                                  ? 'bg-[#1E190A] text-[#D4AF57] border border-[#3E3414]'
                                  : 'bg-[#0E2012] text-[#5A9E60] border border-[#1A3D22]'
                              }`}
                            >
                              {m.result_type === 'defend_win' ? 'Defend Win' : 'Chase Win'}
                            </span>
                          )}

                          {/* Condition Badge: Only rendered when match is non-standard or requires disclosure */}
                          {(() => {
                            const badge = getMatchConditionBadge(m);
                            if (!badge) return null;
                            return (
                              <span
                                className={`px-1.5 py-0.5 rounded text-[9px] font-semibold block mt-0.5 ${badge.className}`}
                              >
                                {badge.label}
                              </span>
                            );
                          })()}
                        </td>
                        <td className="py-2 px-2.5 sm:px-3 text-right whitespace-nowrap">
                          <Link
                            to={m.match_url}
                            className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] text-[#D4AF57] hover:text-[#F2F2F2] bg-[#1A1A1A] hover:bg-[#252525] border border-[#2D2D2D] rounded transition-colors"
                          >
                            <span>Details</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </Link>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={8} className="py-6 text-center text-[#858585]">
                        No matches found matching "{matchSearch}".
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-3 border-t border-[#1F1F1F] text-xs text-[#858585]">
                <div>
                  Showing page <span className="text-[#F2F2F2] font-semibold">{historyPage}</span> of{' '}
                  <span className="text-[#F2F2F2] font-semibold">{totalPages}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setHistoryPage((p) => Math.max(1, p - 1))}
                    disabled={historyPage <= 1}
                    className="p-1.5 rounded bg-[#161616] hover:bg-[#222222] border border-[#2D2D2D] text-[#B8B8B8] hover:text-[#F2F2F2] disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-colors"
                    aria-label="Previous page"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setHistoryPage((p) => Math.min(totalPages, p + 1))}
                    disabled={historyPage >= totalPages}
                    className="p-1.5 rounded bg-[#161616] hover:bg-[#222222] border border-[#2D2D2D] text-[#B8B8B8] hover:text-[#F2F2F2] disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-colors"
                    aria-label="Next page"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
