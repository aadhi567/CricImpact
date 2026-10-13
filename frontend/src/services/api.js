/**
 * API Service for Cricket Batter Contribution Analytics.
 * Connects to the FastAPI backend (Single Source of Truth).
 * All scores and metrics are fetched pre-computed; no contribution formulas in JS.
 */

const API_BASE = import.meta.env?.VITE_API_BASE_URL || '/api';

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) {
    let msg = `API Error ${res.status}: ${res.statusText}`;
    try {
      const err = await res.json();
      if (err.detail) msg = err.detail;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }
  return res.json();
}

export async function getCompetitions() {
  return fetchJson(`${API_BASE}/competitions`);
}

export async function getSeasons(competition = 'ipl', tournamentType = null) {
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  return fetchJson(`${API_BASE}/seasons?${params.toString()}`);
}

export async function getTeams(season, competition = 'ipl', tournamentType = null) {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  return fetchJson(`${API_BASE}/teams?${params.toString()}`);
}

export async function getDashboardSummary({ season, team, minRuns = 0, competition = 'ipl', tournamentType = null } = {}) {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (team) params.append('team', team);
  if (minRuns) params.append('min_runs', minRuns);
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  return fetchJson(`${API_BASE}/dashboard/summary?${params.toString()}`);
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
  return fetchJson(`${API_BASE}/players?${params.toString()}`);
}

export async function getPlayerSeason(playerId, season, competition = 'ipl', tournamentType = null) {
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  return fetchJson(`${API_BASE}/player/${encodeURIComponent(playerId)}/season/${encodeURIComponent(season)}?${params.toString()}`);
}

export async function getPlayerMatches(playerId, season, competition = 'ipl', tournamentType = null) {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  return fetchJson(`${API_BASE}/player/${encodeURIComponent(playerId)}/matches?${params.toString()}`);
}

export async function getMatchDetail(matchId, playerId, competition = 'ipl') {
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  return fetchJson(`${API_BASE}/match/${encodeURIComponent(matchId)}/player/${encodeURIComponent(playerId)}?${params.toString()}`);
}

export async function getAnchorAnalysis(matchId, playerId, competition = 'ipl') {
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  return fetchJson(`${API_BASE}/match/${encodeURIComponent(matchId)}/player/${encodeURIComponent(playerId)}/anchor-analysis?${params.toString()}`);
}

export async function getScatterData({ season, team, player, limit = 1500, competition = 'ipl', tournamentType = null } = {}) {
  const params = new URLSearchParams();
  if (season) params.append('season', season);
  if (team) params.append('team', team);
  if (player) params.append('player', player);
  if (limit) params.append('limit', limit);
  if (competition) params.append('competition', competition);
  if (tournamentType && tournamentType !== 'all') params.append('tournament_type', tournamentType);
  return fetchJson(`${API_BASE}/charts/scatter?${params.toString()}`);
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
  return fetchJson(`${API_BASE}/contribution/compare?${params.toString()}`);
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
  return fetchJson(`${API_BASE}/matchups/rankings?${params.toString()}`);
}

export async function getBatterMatchupDetail(playerId, { season, team, competition = 'ipl' } = {}) {
  const params = new URLSearchParams();
  if (season && season !== 'All Seasons') params.append('season', season);
  if (team && team !== 'All Teams') params.append('team', team);
  if (competition) params.append('competition', competition);
  const query = params.toString() ? `?${params.toString()}` : '';
  return fetchJson(`${API_BASE}/matchups/player/${encodeURIComponent(playerId)}${query}`);
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
  return fetchJson(`${API_BASE}/matches?${params.toString()}`);
}

export async function getTournaments(competition = 't20i') {
  return fetchJson(`${API_BASE}/tournaments?competition=${encodeURIComponent(competition)}`);
}

export async function getMatchOverview(matchId, competition = 'ipl') {
  const params = new URLSearchParams();
  if (competition) params.append('competition', competition);
  return fetchJson(`${API_BASE}/match/${encodeURIComponent(matchId)}?${params.toString()}`);
}


