import playerImages from '../constants/playerImages.js';

/**
 * Normalizes a player name or identifier string to a clean alphanumeric slug.
 * Example: 'V Kohli' -> 'v-kohli', 'Virat Kohli' -> 'virat-kohli'
 *
 * @param {string} name - Raw player name or ID
 * @returns {string} Normalized slug
 */
export function slugifyPlayerName(name) {
  if (!name || typeof name !== 'string') return '';
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/**
 * Resolves a local or fallback image asset path for a given player identifier.
 * Checks multiple variations:
 * 1. Exact string key
 * 2. Lowercase key
 * 3. Kebab-cased slug (e.g. 'v-kohli')
 * 4. Stripped alphanumeric slug (e.g. 'vkohli')
 * 5. Player ID slug if distinct from player name
 *
 * @param {string} playerName - Player name (e.g. 'V Kohli', 'Virat Kohli')
 * @param {string} [playerId] - Optional player identifier
 * @returns {string|null} Resolved image path relative to public dir (e.g. '/assets/players/v-kohli.webp') or null if not available
 */
export function getPlayerImageUrl(playerName, playerId = null) {
  if (!playerName && !playerId) return null;

  const candidates = [playerName, playerId].filter(Boolean);

  for (const raw of candidates) {
    const trimmed = raw.trim();
    if (!trimmed) continue;

    // 1. Direct match
    if (playerImages[trimmed]) {
      return playerImages[trimmed];
    }

    // 2. Lowercase match
    const lower = trimmed.toLowerCase();
    if (playerImages[lower]) {
      return playerImages[lower];
    }

    // 3. Kebab-cased slug
    const slug = slugifyPlayerName(trimmed);
    if (slug && playerImages[slug]) {
      return playerImages[slug];
    }

    // 4. Compact alphanumeric slug (e.g. 'vkohli')
    const compact = slug.replace(/-/g, '');
    if (compact && playerImages[compact]) {
      return playerImages[compact];
    }
  }

  return null;
}

/**
 * Extracts a clean 1 or 2 letter monogram from a player name for fallback avatars.
 *
 * @param {string} name - Player name (e.g. 'V Kohli', 'Rohit Sharma', 'Hardik')
 * @returns {string} 1-2 uppercase letters
 */
export function getPlayerInitials(name) {
  if (!name || typeof name !== 'string') return '?';
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  const first = parts[0][0];
  const last = parts[parts.length - 1][0];
  return (first + last).toUpperCase();
}
