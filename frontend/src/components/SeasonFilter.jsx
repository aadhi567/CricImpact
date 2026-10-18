import React, { useMemo } from 'react';
import { Filter, Search, Trophy, Calendar, Users } from 'lucide-react';
import { TOURNAMENT_TYPES } from '../context/CompetitionContext';

const RUN_THRESHOLDS = [
  { label: 'All', value: 0 },
  { label: '100+', value: 100 },
  { label: '200+', value: 200 },
  { label: '300+', value: 300 },
  { label: '400+', value: 400 },
  { label: '500+', value: 500 },
];

export default function SeasonFilter({
  tournamentType = 'all',
  onTournamentTypeChange,
  tournamentTypes = TOURNAMENT_TYPES,
  showTournamentType = false,
  seasons = [],
  seasonOptions = null,
  selectedSeason,
  onSeasonChange,
  teams = [],
  selectedTeam,
  onTeamChange,
  minRuns,
  onMinRunsChange,
  searchQuery,
  onSearchChange,
}) {
  // Normalize season options with correct display labels
  const resolvedSeasonOptions = useMemo(() => {
    if (seasonOptions && Array.isArray(seasonOptions) && seasonOptions.length > 0) {
      return seasonOptions;
    }
    return seasons.map((s) => ({
      value: s,
      label: s,
    }));
  }, [seasonOptions, seasons]);

  return (
    <div className="bg-[#161616] rounded-lg p-3 sm:p-3.5 border border-[#2D2D2D] font-sans shadow-xs">
      <div className="flex flex-col lg:flex-row items-stretch lg:items-end justify-between gap-3 sm:gap-4">
        {/* Dropdowns and Search Input */}
        <div className="flex flex-wrap xl:flex-nowrap items-end gap-2.5 sm:gap-3 flex-1 min-w-0">
          {/* Tournament Type Selector (Shown on T20I pages) */}
          {showTournamentType && onTournamentTypeChange && (
            <div className="w-full sm:w-auto sm:flex-1 min-w-0 sm:min-w-[130px]">
              <div className="flex items-center gap-1.5 text-[11px] sm:text-[11.5px] font-semibold text-[#D4AF57] uppercase tracking-wider mb-1">
                <Trophy className="w-3 h-3 text-[#D4AF57]" />
                <span>Tournament Type</span>
              </div>
              <select
                id="tournament-type-select"
                value={tournamentType || 'all'}
                onChange={(e) => onTournamentTypeChange(e.target.value)}
                className="w-full h-9 bg-[#101010] border border-[#2D2D2D] rounded-md px-2.5 py-1 text-[12.5px] sm:text-[13px] font-medium text-[#F2F2F2] focus:outline-none focus:border-[#D4AF57] cursor-pointer"
              >
                {tournamentTypes.map((t) => (
                  <option key={t.id} value={t.id} className="bg-[#161616] text-[#F2F2F2]">
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Season Selector */}
          <div className="w-full sm:w-auto sm:flex-1 min-w-0 sm:min-w-[120px]">
            <div className="flex items-center gap-1.5 text-[11px] sm:text-[11.5px] font-semibold text-[#858585] uppercase tracking-wider mb-1">
              <Calendar className="w-3 h-3 text-[#858585]" />
              <span>Season / Year</span>
            </div>
            <select
              id="season-select"
              value={selectedSeason || ''}
              onChange={(e) => onSeasonChange(e.target.value)}
              className="w-full h-9 bg-[#101010] border border-[#2D2D2D] rounded-md px-2.5 py-1 text-[12.5px] sm:text-[13px] font-medium text-[#F2F2F2] focus:outline-none focus:border-[#D4AF57] cursor-pointer"
            >
              {resolvedSeasonOptions.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-[#161616] text-[#F2F2F2]">
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Team Selector */}
          <div className="w-full sm:w-auto sm:flex-1 min-w-0 sm:min-w-[120px]">
            <div className="flex items-center gap-1.5 text-[11px] sm:text-[11.5px] font-semibold text-[#858585] uppercase tracking-wider mb-1">
              <Users className="w-3 h-3 text-[#858585]" />
              <span>Team</span>
            </div>
            <select
              id="team-select"
              value={selectedTeam || ''}
              onChange={(e) => onTeamChange(e.target.value)}
              className="w-full h-9 bg-[#101010] border border-[#2D2D2D] rounded-md px-2.5 py-1 text-[12.5px] sm:text-[13px] font-medium text-[#F2F2F2] focus:outline-none focus:border-[#D4AF57] cursor-pointer"
            >
              <option value="" className="bg-[#161616] text-[#F2F2F2]">All Teams</option>
              {teams.map((t) => (
                <option key={t} value={t} className="bg-[#161616] text-[#F2F2F2]">
                  {t}
                </option>
              ))}
            </select>
          </div>

          {/* Search Player */}
          {onSearchChange && (
            <div className="w-full relative flex-1 min-w-0 sm:min-w-[170px]">
              <div className="flex items-center gap-1.5 text-[11px] sm:text-[11.5px] font-semibold text-[#858585] uppercase tracking-wider mb-1">
                <Search className="w-3 h-3 text-[#858585]" />
                <span>Batter Search</span>
              </div>
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-[#858585] absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  id="batter-search-input"
                  type="text"
                  placeholder="Search batter by name..."
                  value={searchQuery || ''}
                  onChange={(e) => onSearchChange(e.target.value)}
                  className="w-full h-9 bg-[#101010] border border-[#2D2D2D] rounded-md pl-8 pr-2.5 text-[12.5px] sm:text-[13px] font-normal text-[#F2F2F2] placeholder-[#777777] focus:outline-none focus:border-[#D4AF57]"
                />
              </div>
            </div>
          )}
        </div>

        {/* Minimum Runs Filter Pills */}
        {onMinRunsChange && (
          <div className="flex flex-col gap-1 pt-2.5 lg:pt-0 border-t lg:border-t-0 border-[#222222] shrink-0 max-w-full">
            <span className="text-[11px] sm:text-[11.5px] font-semibold text-[#858585] flex items-center gap-1 uppercase tracking-wider">
              <Filter className="w-3 h-3 text-[#D4AF57]" />
              Min Runs:
            </span>
            <div className="flex flex-wrap sm:inline-flex rounded-md bg-[#101010] p-0.5 border border-[#2D2D2D] gap-0.5 max-w-full">
              {RUN_THRESHOLDS.map((thresh) => {
                const active = minRuns === thresh.value;
                return (
                  <button
                    key={thresh.value}
                    type="button"
                    onClick={() => onMinRunsChange(thresh.value)}
                    className={`px-2 sm:px-2.5 py-1 rounded text-[11px] sm:text-[11.5px] font-medium transition-colors cursor-pointer flex-1 sm:flex-initial text-center ${
                      active
                        ? 'bg-[#D4AF57] text-[#080808] font-semibold'
                        : 'text-[#858585] hover:text-[#F2F2F2]'
                    }`}
                  >
                    {thresh.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
