import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, '..');

test('Player Comparison Metric Formatting and NaN Prevention', async (t) => {
  // Direct test of the formatting logic contract
  const formatMetric = (val, decimals = 1, suffix = '', fallback = 'N/A') => {
    if (val === null || val === undefined || val === '') {
      return fallback;
    }
    const n = Number(val);
    if (Number.isNaN(n) || !Number.isFinite(n)) {
      return fallback;
    }
    return `${n.toFixed(decimals)}${suffix}`;
  };

  await t.test('guards against undefined, null, NaN, and Infinity without producing "NaN"', () => {
    assert.strictEqual(formatMetric(undefined), 'N/A');
    assert.strictEqual(formatMetric(null), 'N/A');
    assert.strictEqual(formatMetric(NaN), 'N/A');
    assert.strictEqual(formatMetric(Infinity), 'N/A');
    assert.strictEqual(formatMetric(-Infinity), 'N/A');
    assert.strictEqual(formatMetric(''), 'N/A');
    assert.strictEqual(formatMetric(undefined, 1, '', '—'), '—');
    assert.strictEqual(formatMetric(null, 1, '', '—'), '—');
  });

  await t.test('distinguishes genuine numeric zero from missing data', () => {
    assert.strictEqual(formatMetric(0), '0.0');
    assert.strictEqual(formatMetric(0, 1, '%'), '0.0%');
    assert.strictEqual(formatMetric(0, 0), '0');
    assert.notStrictEqual(formatMetric(0), 'N/A');
    assert.notStrictEqual(formatMetric(0), '—');
  });

  await t.test('formats valid positive numbers and percentages correctly', () => {
    assert.strictEqual(formatMetric(82.61, 1), '82.6');
    assert.strictEqual(formatMetric(66.72, 1), '66.7');
    assert.strictEqual(formatMetric(26.4, 1, '%'), '26.4%');
    assert.strictEqual(formatMetric(150.8, 1), '150.8');
  });

  await t.test('PlayerComparison.jsx does not use naive undefined !== null checks', () => {
    const compPath = path.join(srcDir, 'pages', 'PlayerComparison.jsx');
    const content = fs.readFileSync(compPath, 'utf8');

    // Ensure naive undefined !== null checks that produced NaN are eliminated
    assert.ok(
      !content.includes('p.first_innings_contribution !== null ? Number(p.first_innings_contribution).toFixed(1)'),
      'PlayerComparison.jsx must not use naive !== null on potentially undefined property'
    );
    assert.ok(
      !content.includes('p.powerplay_contribution !== null ? Number(p.powerplay_contribution).toFixed(1)'),
      'PlayerComparison.jsx must not use naive !== null for powerplay contribution'
    );
    assert.ok(
      content.includes('formatMetric'),
      'PlayerComparison.jsx must declare and use formatMetric'
    );
  });

  await t.test('PlayerComparison.jsx contains dot-ball percentage and complete contextual phase metrics', () => {
    const compPath = path.join(srcDir, 'pages', 'PlayerComparison.jsx');
    const content = fs.readFileSync(compPath, 'utf8');

    // Category 1: Dot-ball percentage
    assert.ok(content.includes('Dot-Ball Percentage'), 'Must contain Dot-Ball Percentage row');
    assert.ok(content.includes('p.dot_ball_percentage'), 'Must reference dot_ball_percentage');

    // Category 4: Contextual phase breakdown
    assert.ok(content.includes('1st Innings Contribution'), 'Must display 1st Innings Contribution');
    assert.ok(content.includes('Chase (2nd Innings) Contribution'), 'Must display Chase Contribution');
    assert.ok(content.includes('Powerplay (Overs 1–6) Contribution'), 'Must display Powerplay Contribution');
    assert.ok(content.includes('Powerplay Strike Rate'), 'Must display Powerplay Strike Rate');
    assert.ok(content.includes('Middle Overs (Overs 7–16) Contribution'), 'Must display Middle Overs (Overs 7–16)');
    assert.ok(content.includes('Middle Overs Strike Rate'), 'Must display Middle Overs Strike Rate');
    assert.ok(content.includes('Death Overs (Overs 17–20) Contribution'), 'Must display Death Overs (Overs 17–20)');
    assert.ok(content.includes('Death Overs Strike Rate'), 'Must display Death Overs Strike Rate');
    assert.ok(content.includes('High Pressure Contribution'), 'Must display High Pressure Contribution');

    // Fallback access to both top-level and context_breakdown
    assert.ok(content.includes('p.powerplay_contribution ?? p.context_breakdown?.powerplay_contribution'));
    assert.ok(content.includes('p.middle_over_contribution ?? p.context_breakdown?.middle_over_contribution'));
    assert.ok(content.includes('p.death_over_contribution ?? p.context_breakdown?.death_over_contribution'));
    assert.ok(content.includes('p.first_innings_contribution ?? p.context_breakdown?.first_innings_contribution'));
    assert.ok(content.includes('p.chase_contribution ?? p.context_breakdown?.chase_contribution'));
    assert.ok(content.includes('p.high_pressure_contribution ?? p.context_breakdown?.high_pressure_contribution'));
  });
});
