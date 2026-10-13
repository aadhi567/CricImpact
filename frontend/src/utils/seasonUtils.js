/**
 * Utility functions for dynamic season resolution and cricket year management.
 * Strictly adheres to dynamic calendar year resolution without hardcoding any specific year.
 */

/**
 * Resolves the default season dynamically based on the current calendar year.
 * 1. Matches exact current year if available in supported seasons (e.g. '2026').
 * 2. Matches overlapping split-season if available (e.g. '2025/26' or '2026/27').
 * 3. Falls back to API default_season if provided and valid.
 * 4. Otherwise selects the latest available season (first element in chronologically descending list).
 *
 * @param {Array<string|Object>} availSeasons - List of season strings or option objects with .value
 * @param {string|null} fallbackDefault - Optional fallback default provided by API
 * @returns {string} The resolved default season
 */
export function resolveDefaultSeason(availSeasons, fallbackDefault = null) {
  if (!availSeasons || !Array.isArray(availSeasons) || availSeasons.length === 0) {
    return '';
  }

  const currentYear = new Date().getFullYear().toString();

  // Normalize array to strings
  const seasonValues = availSeasons
    .map((s) => (typeof s === 'string' ? s.trim() : s?.value ? String(s.value).trim() : ''))
    .filter(Boolean);

  if (seasonValues.length === 0) {
    return '';
  }

  // 1. Exact match with current calendar year (e.g. '2026')
  if (seasonValues.includes(currentYear)) {
    return currentYear;
  }

  // 2. Overlapping split-season match (e.g. '2025/26' or '2026/27' for 2026)
  const shortYear = currentYear.slice(2);
  const splitMatch = seasonValues.find(
    (s) => s.endsWith(`/${shortYear}`) || s.startsWith(`${currentYear}/`)
  );
  if (splitMatch) {
    return splitMatch;
  }

  // 3. Fallback to API default_season if provided and present in options
  if (fallbackDefault && seasonValues.includes(String(fallbackDefault).trim())) {
    return String(fallbackDefault).trim();
  }

  // 4. Latest available season (first element in sorted list)
  return seasonValues[0];
}

/**
 * Determines whether a given season value is valid for a given list of available seasons.
 *
 * @param {string} season - The season value to test
 * @param {Array<string|Object>} availSeasons - Available seasons
 * @returns {boolean}
 */
export function isSeasonValid(season, availSeasons) {
  if (!season || !availSeasons || !Array.isArray(availSeasons)) return false;
  const sStr = String(season).trim();
  return availSeasons.some((s) => {
    const val = typeof s === 'string' ? s.trim() : s?.value ? String(s.value).trim() : '';
    return val === sStr;
  });
}
