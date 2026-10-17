/**
 * API Service for Cricket Batter Contribution Analytics.
 * Connects to the FastAPI backend (Single Source of Truth).
 * All scores and metrics are fetched pre-computed; no contribution formulas in JS.
 */

const RAW_API_BASE = import.meta.env?.VITE_API_BASE_URL;

/**
 * Resolves the API base URL ensuring it always ends with '/api' (without trailing slash).
 * Handles:
 * - Empty / undefined / whitespace -> '/api'
 * - Origin / domain without '/api' (e.g. 'https://cricimpact.onrender.com') -> 'https://cricimpact.onrender.com/api'
 * - Already ends with '/api' (e.g. 'https://cricimpact.onrender.com/api' or '/api') -> kept intact
 * - Trailing slashes stripped cleanly
 *
 * @param {string} [rawEnv] - Optional raw environment variable string (defaults to VITE_API_BASE_URL)
 * @returns {string} The normalized API base URL
 */
export function getApiBaseUrl(rawEnv = RAW_API_BASE) {
  const trimmed = (rawEnv || '').trim().replace(/\/+$/, '');
  if (!trimmed || trimmed === '/') {
    return '/api';
  }
  if (trimmed.endsWith('/api')) {
    return trimmed;
  }
  return `${trimmed}/api`;
}

/**
 * Constructs a fully qualified or proxy-relative API URL.
 * Guarantees that the resulting URL path always routes through '/api/...'.
 * Prevents double '/api/api' segments if the path already starts with '/api'.
 *
 * @param {string} path - Target endpoint path (e.g. '/competitions' or '/api/competitions')
 * @param {string} [rawEnv] - Optional raw environment variable override
 * @returns {string} The resolved API URL
 */
export function buildApiUrl(path = '', rawEnv = RAW_API_BASE) {
  const base = getApiBaseUrl(rawEnv);
  if (!path || path === '/') {
    return base;
  }
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (normalizedPath === '/api' || normalizedPath.startsWith('/api/') || normalizedPath.startsWith('/api?')) {
    const cleanPath = normalizedPath.slice(4);
    return `${base}${cleanPath}`;
  }
  return `${base}${normalizedPath}`;
}

export const API_BASE = getApiBaseUrl();

export async function fetchJson(url) {
  const res = await fetch(url);
  const contentType = res.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');

  if (!res.ok) {
    let msg = `API Error ${res.status}: ${res.statusText}`;
    if (isJson) {
      try {
        const err = await res.json();
        if (err.detail) msg = err.detail;
      } catch {
        // ignore
      }
    } else {
      try {
        const text = await res.text();
        if (text && text.trim().startsWith('<')) {
          msg = `API Error ${res.status}: Server returned an HTML response instead of JSON (${res.statusText || 'Error'}).`;
        }
      } catch {
        // ignore
      }
    }
    throw new Error(msg);
  }

  if (res.status === 204) {
    return null;
  }

  if (!isJson) {
    const text = await res.text();
    if (text && text.trim().startsWith('<')) {
      throw new Error(
        `API returned HTML instead of JSON from ${url}. Check API routing, base URL, and ensure the backend is reachable.`
      );
    }
    throw new Error(`Expected JSON from API but received '${contentType || 'non-JSON'}' from ${url}.`);
  }

  return res.json();
}

export async function getCompetitions() {
  return fetchJson(buildApiUrl('/competitions'));
}

export async function getSeasons(competition = 'ipl', tournamentType = null) {
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/seasons${query}`));
}

export async function getTeams(season, competition = 'ipl', tournamentType = null) {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/teams${query}`));
}

export async function getDashboardSummary({ season, team, minRuns = 0, competition = 'ipl', tournamentType = null } = {}) {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (team) params.append('team', team);
  if (minRuns) params.append('min_runs', minRuns);
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/dashboard/summary${query}`));
}

export async function getPlayers({
  season,
  team,
  minRuns = 0,
  minInnings = 0,
  minBalls = 0,
  search,
  limit = 500,
  competition = 'ipl',
  tournamentType = null,
} = {}) {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (team) params.append('team', team);
  if (minRuns) params.append('min_runs', minRuns);
  if (minInnings) params.append('min_innings', minInnings);
  if (minBalls) params.append('min_balls', minBalls);
  if (search) params.append('search', search);
  if (limit) params.append('limit', limit);
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/players${query}`));
}

export async function getPlayerSeason(playerId, season, competition = 'ipl', tournamentType = null) {
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/player/${encodeURIComponent(playerId)}/season/${encodeURIComponent(season)}${query}`));
}

export async function getPlayerMatches(playerId, season, competition = 'ipl', tournamentType = null) {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/player/${encodeURIComponent(playerId)}/matches${query}`));
}

export async function getMatchDetail(matchId, playerId, competition = 'ipl') {
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/match/${encodeURIComponent(matchId)}/player/${encodeURIComponent(playerId)}${query}`));
}

export async function getAnchorAnalysis(matchId, playerId, competition = 'ipl') {
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/match/${encodeURIComponent(matchId)}/player/${encodeURIComponent(playerId)}/anchor-analysis${query}`));
}

export async function getScatterData({ season, team, player, limit = 1500, competition = 'ipl', tournamentType = null } = {}) {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (team) params.append('team', team);
  if (player) params.append('player', player);
  if (limit) params.append('limit', limit);
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/charts/scatter${query}`));
}

export async function comparePlayers({ season, players = [], view = 'view_a', competition = 'ipl', tournamentType = null } = {}) {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (Array.isArray(players)) {
    params.append('players', players.join(','));
  } else if (players) {
    params.append('players', players);
  }
  if (view) params.append('view', view);
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/contribution/compare${query}`));
}

export async function getMatchupRankings({
  season,
  team,
  bowlingType,
  minBalls = 100,
  minRuns = 80,
  competition = 'ipl',
} = {}) {
  const params = new URLSearchParams();
  if (season && season !== 'All Seasons') params.append('season', season);
  if (team && team !== 'All Teams') params.append('team', team);
  if (bowlingType && bowlingType !== 'all') params.append('bowling_type', bowlingType);
  if (minBalls !== undefined) params.append('min_balls', minBalls);
  if (minRuns !== undefined) params.append('min_runs', minRuns);
  if (competition) params.append('competition', competition);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/matchups/rankings${query}`));
}

export async function getBatterMatchupDetail(playerId, { season, team, competition = 'ipl' } = {}) {
  const params = new URLSearchParams();
  if (season && season !== 'All Seasons') params.append('season', season);
  if (team && team !== 'All Teams') params.append('team', team);
  if (competition) params.append('competition', competition);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/matchups/player/${encodeURIComponent(playerId)}${query}`));
}

export async function getMatches({ season, team, opponent, tournament, search, limit = 200, competition = 'ipl', tournamentType = null } = {}) {
  const params = new URLSearchParams();
  if (season && season !== 'All Seasons') params.append('season', season);
  if (team && team !== 'All Teams') params.append('team', team);
  if (opponent && opponent !== 'All Opponents') params.append('opponent', opponent);
  if (tournament && tournament !== 'All Tournaments') params.append('tournament', tournament);
  if (search) params.append('search', search);
  if (limit) params.append('limit', limit);
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/matches${query}`));
}

export async function getTournaments(competition = 't20i') {
  return fetchJson(buildApiUrl(`/tournaments?competition=${encodeURIComponent(competition)}`));
}

export async function getMatchOverview(matchId, competition = 'ipl') {
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/match/${encodeURIComponent(matchId)}${query}`));
}

export async function getPlayerCareer(playerId, competition = 'combined') {
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/player/${encodeURIComponent(playerId)}/career${query}`));
}

export async function searchCareerPlayers(query, { competition, limit = 20 } = {}) {
  const params = new URLSearchParams();
  if (query) params.append('q', query);
  if (competition) params.append('competition', competition);
  if (limit) params.append('limit', limit);
  const queryString = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/players/search${queryString}`));
}

export async function getDatasetCoverage(competition = null) {
  const params = new URLSearchParams();
  if (competition && competition !== 'combined') params.append('competition', competition);
  const q = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/competitions/coverage${q}`));
}

export async function getGroundVenues({ competition = 'combined', country = null } = {}) {
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  if (country && country !== 'All') params.append('country', country);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/ground-analysis/venues${query}`));
}

export async function getGroundAnalysis(venueId, { competition = 'combined', period = 'rolling_5yr', startDate = null, endDate = null } = {}) {
  if (!venueId) {
    throw new Error('venueId is required for getGroundAnalysis');
  }
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  if (period) params.append('period', period);
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(buildApiUrl(`/ground-analysis/venue/${encodeURIComponent(venueId)}${query}`));
}
