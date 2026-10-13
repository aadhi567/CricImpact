// Temporarily deactivated due to incomplete match coverage (preserved for future reactivation)
export const DEACTIVATED_COMPETITIONS = [
  {
    id: 'smat',
    name: 'Syed Mushtaq Ali Trophy',
    short_name: 'SMAT',
    badge: 'SMAT',
    format: 'T20',
    description: 'Indian Domestic T20 Tournament (2022+)',
    coverage: '2022+ • Knockouts & Televised (91 matches)',
    status: 'temporarily_deactivated',
  },
];

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

export const CRICKET_FORMATS = [
  {
    id: 'T20',
    label: 'T20',
    fullName: 'Twenty20 (20 Overs)',
    description: 'Production calibrated situational expected runs & leverage model',
    status: 'active',
    activeBadge: 'Calibrated',
  },
  {
    id: 'ODI',
    label: 'ODI',
    fullName: 'One Day International (50 Overs)',
    description: '50-over situational model under development',
    status: 'coming_soon',
    activeBadge: 'Coming Soon',
  },
  {
    id: 'Test',
    label: 'Test',
    fullName: 'Test Match Cricket (Multi-Day)',
    description: 'Multi-day session decay model under development',
    status: 'coming_soon',
    activeBadge: 'Coming Soon',
  },
];
