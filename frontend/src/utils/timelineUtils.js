/**
 * Utility functions for Match-by-match Contribution Timeline visualization.
 * Handles chronological sorting, date formatting, DNB exclusions,
 * par benchmark calculations, and summary statistics.
 */

const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTHS_FULL = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

/**
 * Formats ISO date string (YYYY-MM-DD) into concise day and month format (e.g. "18 May").
 * Prevents timezone offset bugs by splitting string directly.
 */
export function formatMatchDateShort(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return '';
  const parts = dateStr.trim().split('-');
  if (parts.length === 3) {
    const monthIdx = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    if (monthIdx >= 0 && monthIdx < 12 && !isNaN(day)) {
      return `${day} ${MONTHS_SHORT[monthIdx]}`;
    }
  }
  return dateStr;
}

/**
 * Formats ISO date string (YYYY-MM-DD) into full human-readable format (e.g. "18 May 2024").
 */
export function formatMatchDateFull(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return '';
  const parts = dateStr.trim().split('-');
  if (parts.length === 3) {
    const year = parts[0];
    const monthIdx = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    if (monthIdx >= 0 && monthIdx < 12 && !isNaN(day)) {
      return `${day} ${MONTHS_FULL[monthIdx]} ${year}`;
    }
  }
  return dateStr;
}

/**
 * Calculates responsive XAxis tick intervals to completely eliminate label overlaps.
 * Uses available viewport width and data density.
 */
export function calculateTickInterval(dataLength, width = 1024) {
  if (!dataLength || dataLength <= 0) return 0;
  
  let maxTicks = 12;
  if (width < 400) {
    maxTicks = 4;
  } else if (width < 640) {
    maxTicks = 6;
  } else if (width < 1024) {
    maxTicks = 9;
  }

  if (dataLength <= maxTicks) {
    return 0; // Show all ticks
  }

  return Math.ceil(dataLength / maxTicks) - 1;
}

/**
 * Calculates summary metrics across match performances.
 * Strictly excludes Did Not Bat (DNB) appearances and unrated matches
 * so that non-batting matches never deflate performance averages.
 */
export function computeTimelineSummary(matches = []) {
  if (!Array.isArray(matches)) {
    return {
      totalMatches: 0,
      ratedCount: 0,
      dnbCount: 0,
      aboveParCount: 0,
      belowParCount: 0,
      atParCount: 0,
      aboveParPct: null,
      bestScore: null,
      bestMatch: null,
      recentFormAvg: null,
      recentFormCount: 0,
    };
  }

  const totalMatches = matches.length;

  // Chronologically sort first to guarantee proper timeline order
  const sorted = [...matches].sort((a, b) => {
    const dateA = a.date || '';
    const dateB = b.date || '';
    if (dateA !== dateB) return dateA.localeCompare(dateB);
    return (Number(a.match_id) || 0) - (Number(b.match_id) || 0);
  });

  // Filter for valid, rated batting innings
  const ratedMatches = sorted.filter((m) => {
    if (m.is_dnb === true) return false;
    if (m.contribution_score === null || m.contribution_score === undefined) return false;
    const num = Number(m.contribution_score);
    return !isNaN(num) && isFinite(num);
  });

  const ratedCount = ratedMatches.length;
  const dnbCount = totalMatches - ratedCount;

  if (ratedCount === 0) {
    return {
      totalMatches,
      ratedCount,
      dnbCount,
      aboveParCount: 0,
      belowParCount: 0,
      atParCount: 0,
      aboveParPct: null,
      bestScore: null,
      bestMatch: null,
      recentFormAvg: null,
      recentFormCount: 0,
    };
  }

  let aboveParCount = 0;
  let belowParCount = 0;
  let atParCount = 0;
  let bestScore = -Infinity;
  let bestMatch = null;

  ratedMatches.forEach((m) => {
    const score = Number(m.contribution_score);
    if (score > 50.0) {
      aboveParCount++;
    } else if (score < 50.0) {
      belowParCount++;
    } else {
      atParCount++;
    }

    if (score > bestScore) {
      bestScore = score;
      bestMatch = m;
    }
  });

  const aboveParPct = (aboveParCount / ratedCount) * 100;

  // Recent form average: latest 5 rated batting innings (or all available if < 5)
  const last5 = ratedMatches.slice(-5);
  const sumLast5 = last5.reduce((acc, m) => acc + Number(m.contribution_score), 0);
  const recentFormAvg = last5.length > 0 ? sumLast5 / last5.length : null;

  return {
    totalMatches,
    ratedCount,
    dnbCount,
    aboveParCount,
    belowParCount,
    atParCount,
    aboveParPct: Math.round(aboveParPct * 10) / 10,
    bestScore: Math.round(bestScore * 10) / 10,
    bestMatch,
    recentFormAvg: recentFormAvg !== null ? Math.round(recentFormAvg * 10) / 10 : null,
    recentFormCount: last5.length,
  };
}

/**
 * Prepares and normalizes chart dataset from match records.
 * Sorts chronologically, excludes DNB, computes deviation from par (score - 50),
 * and assigns status styling tokens.
 */
export function prepareTimelineChartData(matches = [], viewMode = 'score') {
  if (!Array.isArray(matches)) return [];

  // Sort strictly in chronological order
  const sorted = [...matches].sort((a, b) => {
    const dateA = a.date || '';
    const dateB = b.date || '';
    if (dateA !== dateB) return dateA.localeCompare(dateB);
    return (Number(a.match_id) || 0) - (Number(b.match_id) || 0);
  });

  // Filter out DNB and unrated records
  const rated = sorted.filter((m) => {
    if (m.is_dnb === true) return false;
    if (m.contribution_score === null || m.contribution_score === undefined) return false;
    const num = Number(m.contribution_score);
    return !isNaN(num) && isFinite(num);
  });

  return rated.map((m, idx) => {
    const score = Math.round(Number(m.contribution_score) * 10) / 10;
    const deviation = Math.round((score - 50.0) * 10) / 10;
    const plotValue = viewMode === 'deviation' ? deviation : score;

    let status = 'par';
    if (score > 50.0) status = 'above';
    else if (score < 50.0) status = 'below';

    return {
      index: idx + 1,
      match_id: m.match_id,
      match_number: idx + 1,
      date: m.date || '',
      display_date: formatMatchDateShort(m.date) || `M${idx + 1}`,
      full_date: formatMatchDateFull(m.date) || `Match #${m.match_id}`,
      opponent: m.opponent || 'Opposition',
      venue: m.venue || '',
      event_name: m.event_name || '',
      stage: m.stage || '',
      runs: m.runs ?? 0,
      balls: m.balls ?? 0,
      strike_rate: m.strike_rate !== null && m.strike_rate !== undefined ? m.strike_rate : null,
      is_not_out: Boolean(m.is_not_out),
      raw_contribution: m.raw_contribution !== null && m.raw_contribution !== undefined ? Number(m.raw_contribution) : null,
      contribution_score: score,
      deviation,
      plot_value: plotValue,
      status,
    };
  });
}
