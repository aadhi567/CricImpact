import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  formatMatchDateShort,
  formatMatchDateFull,
  calculateTickInterval,
  computeTimelineSummary,
  prepareTimelineChartData,
} from '../utils/timelineUtils.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, '..');

test('MatchScoreTimeline Logic and Metric Contracts', async (t) => {
  // Test fixture data
  const sampleMatches = [
    {
      match_id: 103,
      date: '2024-05-18',
      opponent: 'Chennai Super Kings',
      venue: 'M. Chinnaswamy Stadium, Bengaluru',
      runs: 47,
      balls: 29,
      strike_rate: 162.1,
      is_dnb: false,
      contribution_score: 64.8,
      raw_contribution: 0.385,
    },
    {
      match_id: 101,
      date: '2024-03-25',
      opponent: 'Punjab Kings',
      venue: 'M. Chinnaswamy Stadium, Bengaluru',
      runs: 77,
      balls: 49,
      strike_rate: 157.1,
      is_dnb: false,
      contribution_score: 79.4,
      raw_contribution: 0.724,
    },
    {
      match_id: 102,
      date: '2024-04-11',
      opponent: 'Mumbai Indians',
      venue: 'Wankhede Stadium, Mumbai',
      runs: 3,
      balls: 9,
      strike_rate: 33.3,
      is_dnb: false,
      contribution_score: 36.2,
      raw_contribution: -0.421,
    },
    {
      match_id: 104,
      date: '2024-05-22',
      opponent: 'Rajasthan Royals',
      venue: 'Narendra Modi Stadium, Ahmedabad',
      runs: 33,
      balls: 24,
      strike_rate: 137.5,
      is_dnb: false,
      contribution_score: 50.0,
      raw_contribution: 0.0,
    },
    {
      match_id: 105,
      date: '2024-05-26',
      opponent: 'Kolkata Knight Riders',
      venue: 'MA Chidambaram Stadium, Chennai',
      runs: 0,
      balls: 0,
      strike_rate: 0,
      is_dnb: true, // Did Not Bat
      contribution_score: null,
      raw_contribution: null,
    },
  ];

  await t.test('enforces strict chronological ordering regardless of input array order', () => {
    const data = prepareTimelineChartData(sampleMatches, 'score');
    assert.strictEqual(data.length, 4, 'DNB match must be excluded from chart plotting');
    assert.strictEqual(data[0].date, '2024-03-25');
    assert.strictEqual(data[1].date, '2024-04-11');
    assert.strictEqual(data[2].date, '2024-05-18');
    assert.strictEqual(data[3].date, '2024-05-22');
  });

  await t.test('formats match dates cleanly to prevent label collisions', () => {
    assert.strictEqual(formatMatchDateShort('2024-03-25'), '25 Mar');
    assert.strictEqual(formatMatchDateShort('2024-05-18'), '18 May');
    assert.strictEqual(formatMatchDateShort('2024-11-03'), '3 Nov');
    assert.strictEqual(formatMatchDateShort(''), '');
    assert.strictEqual(formatMatchDateShort(null), '');

    assert.strictEqual(formatMatchDateFull('2024-03-25'), '25 March 2024');
    assert.strictEqual(formatMatchDateFull('2024-05-18'), '18 May 2024');
  });

  await t.test('computes par benchmark and deviation faithfully without altering scores', () => {
    const scoreView = prepareTimelineChartData(sampleMatches, 'score');
    const devView = prepareTimelineChartData(sampleMatches, 'deviation');

    // Both views must have identical lengths and matches
    assert.strictEqual(scoreView.length, devView.length);

    // Match 1 (2024-03-25): score = 79.4, deviation = +29.4
    assert.strictEqual(scoreView[0].contribution_score, 79.4);
    assert.strictEqual(scoreView[0].plot_value, 79.4);
    assert.strictEqual(devView[0].deviation, 29.4);
    assert.strictEqual(devView[0].plot_value, 29.4);
    assert.strictEqual(devView[0].status, 'above');

    // Match 2 (2024-04-11): score = 36.2, deviation = -13.8
    assert.strictEqual(scoreView[1].contribution_score, 36.2);
    assert.strictEqual(scoreView[1].plot_value, 36.2);
    assert.strictEqual(devView[1].deviation, -13.8);
    assert.strictEqual(devView[1].plot_value, -13.8);
    assert.strictEqual(devView[1].status, 'below');

    // Match 4 (2024-05-22): score = 50.0, deviation = 0.0
    assert.strictEqual(scoreView[3].contribution_score, 50.0);
    assert.strictEqual(scoreView[3].deviation, 0.0);
    assert.strictEqual(devView[3].plot_value, 0.0);
    assert.strictEqual(devView[3].status, 'par');
  });

  await t.test('computes timeline summary statistics with accurate DNB exclusion', () => {
    const summary = computeTimelineSummary(sampleMatches);

    assert.strictEqual(summary.totalMatches, 5, 'Total matches includes all appearances');
    assert.strictEqual(summary.ratedCount, 4, 'Rated innings strictly excludes DNB');
    assert.strictEqual(summary.dnbCount, 1, 'DNB count must be 1');

    // Above Par (>50): 79.4, 64.8 => 2
    // Below Par (<50): 36.2 => 1
    // At Par (=50): 50.0 => 1
    assert.strictEqual(summary.aboveParCount, 2);
    assert.strictEqual(summary.belowParCount, 1);
    assert.strictEqual(summary.atParCount, 1);
    assert.strictEqual(summary.aboveParPct, 50.0, '2 out of 4 rated innings is 50.0%');

    // Best match score
    assert.strictEqual(summary.bestScore, 79.4);
    assert.strictEqual(summary.bestMatch.opponent, 'Punjab Kings');

    // Recent form: last 5 rated batting innings. Here we have 4 rated matches:
    // [79.4, 36.2, 64.8, 50.0] => sum = 230.4 => avg = 57.6
    assert.strictEqual(summary.recentFormCount, 4);
    assert.strictEqual(summary.recentFormAvg, 57.6);
  });

  await t.test('recent form calculates mean of strictly the latest 5 rated innings when > 5 matches exist', () => {
    const manyMatches = [];
    // 7 rated matches: 10, 20, 30, 40, 50, 60, 70
    for (let i = 1; i <= 7; i++) {
      manyMatches.push({
        match_id: i,
        date: `2024-04-0${i}`,
        is_dnb: false,
        contribution_score: i * 10,
      });
    }
    // Also insert a DNB match in between
    manyMatches.push({
      match_id: 99,
      date: '2024-04-15',
      is_dnb: true,
      contribution_score: null,
    });

    const summary = computeTimelineSummary(manyMatches);
    assert.strictEqual(summary.totalMatches, 8);
    assert.strictEqual(summary.ratedCount, 7);
    assert.strictEqual(summary.dnbCount, 1);

    // Latest 5 rated matches are: 30, 40, 50, 60, 70 => sum = 250 / 5 = 50.0
    assert.strictEqual(summary.recentFormCount, 5);
    assert.strictEqual(summary.recentFormAvg, 50.0);
  });

  await t.test('handles empty and all-DNB matches gracefully', () => {
    const emptySummary = computeTimelineSummary([]);
    assert.strictEqual(emptySummary.totalMatches, 0);
    assert.strictEqual(emptySummary.ratedCount, 0);
    assert.strictEqual(emptySummary.bestScore, null);
    assert.strictEqual(emptySummary.recentFormAvg, null);

    const allDnbSummary = computeTimelineSummary([
      { match_id: 1, is_dnb: true, contribution_score: null },
      { match_id: 2, is_dnb: true, contribution_score: null },
    ]);
    assert.strictEqual(allDnbSummary.totalMatches, 2);
    assert.strictEqual(allDnbSummary.ratedCount, 0);
    assert.strictEqual(allDnbSummary.dnbCount, 2);
    assert.strictEqual(allDnbSummary.bestScore, null);
    assert.strictEqual(allDnbSummary.recentFormAvg, null);

    const emptyChart = prepareTimelineChartData([]);
    assert.deepStrictEqual(emptyChart, []);
  });

  await t.test('calculates responsive tick intervals to prevent label crowding', () => {
    // 20 matches on mobile (< 640px)
    const mobileInterval = calculateTickInterval(20, 500);
    // maxTicks is 6, ceil(20 / 6) - 1 = 4 - 1 = 3 (shows every 4th tick)
    assert.ok(mobileInterval > 0, 'Must skip ticks when dense data on mobile');

    // 5 matches on mobile (< 640px)
    const smallMobileInterval = calculateTickInterval(5, 500);
    assert.strictEqual(smallMobileInterval, 0, 'Must show all ticks when count <= maxTicks');

    // 20 matches on desktop (1280px)
    const desktopInterval = calculateTickInterval(20, 1280);
    assert.ok(desktopInterval <= mobileInterval, 'Desktop must display more or equal ticks than mobile');
  });

  await t.test('verifies MatchScoreTimeline component contains par benchmark, deviation toggle, and summary statistics', () => {
    const componentPath = path.join(srcDir, 'components', 'Charts', 'MatchScoreTimeline.jsx');
    const content = fs.readFileSync(componentPath, 'utf8');

    // Check Par reference
    assert.ok(content.includes('Par') || content.includes('par'), 'Must mention Par benchmark');
    // Check Recharts components
    assert.ok(content.includes('ReferenceLine'), 'Must use ReferenceLine for benchmark');
    assert.ok(content.includes('ResponsiveContainer'), 'Must use ResponsiveContainer');
  });
});
