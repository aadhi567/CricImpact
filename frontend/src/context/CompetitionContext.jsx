import React, { createContext, useContext, useState, useEffect } from 'react';
import { getCompetitions } from '../services/api';
import { resolveDefaultSeason, isSeasonValid } from '../utils/seasonUtils';

export { resolveDefaultSeason, isSeasonValid };

export const DEFAULT_COMPETITIONS = [
  {
    id: 'ipl',
    name: 'Indian Premier League',
    short_name: 'IPL',
    badge: 'IPL',
    format: 'T20',
    description: 'Complete ball-by-ball dataset (2008–2024)',
    coverage: 'Complete (1,243 matches)',
  },
  {
    id: 't20i',
    name: "Men's International T20I",
    short_name: 'T20I',
    badge: 'T20I',
    format: 'T20',
    description: "Global Men's International T20s from 2022 onwards",
    coverage: '2022+ (2,264 matches)',
  },
];

export const TOURNAMENT_TYPES = [
  { id: 'all', label: 'All International T20Is' },
  { id: 'world_cup', label: "ICC Men's T20 World Cup" },
  { id: 'asia_cup', label: "Men's Asia Cup (T20)" },
  { id: 'bilateral', label: 'Bilateral / Tri-Series' },
];

const CompetitionContext = createContext({
  competition: 'ipl',
  setCompetition: () => {},
  tournamentType: 'all',
  setTournamentType: () => {},
  selectedSeason: '',
  setSelectedSeason: () => {},
  competitions: DEFAULT_COMPETITIONS,
  activeMeta: DEFAULT_COMPETITIONS[0],
});

export function CompetitionProvider({ children }) {
  const [competition, setCompetitionState] = useState(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const urlComp = params.get('competition');
      if (urlComp && ['ipl', 't20i'].includes(urlComp.toLowerCase())) {
        return urlComp.toLowerCase();
      }
      const saved = localStorage.getItem('cricket_competition');
      if (saved && ['ipl', 't20i'].includes(saved.toLowerCase())) {
        return saved.toLowerCase();
      }
    } catch {
      // ignore
    }
    return 'ipl';
  });

  const [tournamentType, setTournamentTypeState] = useState(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const urlTourn = params.get('tournament_type');
      if (urlTourn && TOURNAMENT_TYPES.some((t) => t.id === urlTourn)) {
        return urlTourn;
      }
      const saved = localStorage.getItem('cricket_tournament_type');
      if (saved && TOURNAMENT_TYPES.some((t) => t.id === saved)) {
        return saved;
      }
    } catch {
      // ignore
    }
    return 'all';
  });

  const [selectedSeason, setSelectedSeasonState] = useState(() => {
    try {
      return sessionStorage.getItem('cricket_selected_season') || '';
    } catch {
      return '';
    }
  });

  const [competitions, setCompetitions] = useState(DEFAULT_COMPETITIONS);

  useEffect(() => {
    async function loadComps() {
      try {
        const res = await getCompetitions();
        if (res && res.competitions && res.competitions.length > 0) {
          setCompetitions(res.competitions);
        }
      } catch {
        // Fallback to static defaults
      }
    }
    loadComps();
  }, []);

  const setCompetition = (compId) => {
    const id = compId.toLowerCase();
    setCompetitionState(id);
    if (id !== 't20i') {
      setTournamentTypeState('all');
    }
    try {
      localStorage.setItem('cricket_competition', id);
    } catch {
      // ignore
    }
  };

  const setTournamentType = (tType) => {
    const valid = TOURNAMENT_TYPES.some((t) => t.id === tType);
    const chosen = valid ? tType : 'all';
    setTournamentTypeState(chosen);
    try {
      localStorage.setItem('cricket_tournament_type', chosen);
    } catch {
      // ignore
    }
  };

  const setSelectedSeason = (seasonOrFn) => {
    setSelectedSeasonState((prev) => {
      const next = typeof seasonOrFn === 'function' ? seasonOrFn(prev) : seasonOrFn;
      try {
        if (next) {
          sessionStorage.setItem('cricket_selected_season', String(next));
        } else {
          sessionStorage.removeItem('cricket_selected_season');
        }
      } catch {
        // ignore
      }
      return next;
    });
  };

  const activeMeta = competitions.find((c) => c.id === competition) || competitions[0];

  return (
    <CompetitionContext.Provider
      value={{
        competition,
        setCompetition,
        tournamentType,
        setTournamentType,
        selectedSeason,
        setSelectedSeason,
        competitions,
        activeMeta,
      }}
    >
      {children}
    </CompetitionContext.Provider>
  );
}

export function useCompetition() {
  const context = useContext(CompetitionContext);
  if (!context) {
    throw new Error('useCompetition must be used within a CompetitionProvider');
  }
  return context;
}
