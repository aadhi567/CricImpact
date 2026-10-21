import { describe, it } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  getPlayerImageUrl,
  getPlayerInitials,
  slugifyPlayerName,
} from '../utils/playerImageMap.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '../../');

describe('Player Image Mapping & Slugification', () => {
  it('slugifyPlayerName normalizes names cleanly', () => {
    assert.strictEqual(slugifyPlayerName('Jos Buttler'), 'jos-buttler');
    assert.strictEqual(slugifyPlayerName('JC Buttler'), 'jc-buttler');
    assert.strictEqual(slugifyPlayerName('  Ruturaj Gaikwad  '), 'ruturaj-gaikwad');
    assert.strictEqual(slugifyPlayerName(''), '');
    assert.strictEqual(slugifyPlayerName(null), '');
  });

  it('resolves verified open-access player names to local WebP assets', () => {
    const buttler = getPlayerImageUrl('JC Buttler');
    assert.ok(buttler, 'JC Buttler must resolve to an image path');
    assert.ok(buttler.endsWith('.webp'), 'Image path must be a WebP asset');

    const gaikwad = getPlayerImageUrl('RD Gaikwad');
    assert.ok(gaikwad, 'RD Gaikwad must resolve to an image path');

    const shaw = getPlayerImageUrl('PP Shaw');
    assert.ok(shaw, 'PP Shaw must resolve to an image path');

    const shami = getPlayerImageUrl('Mohammed Shami');
    assert.ok(shami, 'Mohammed Shami must resolve to an image path');

    const yadav = getPlayerImageUrl('UT Yadav');
    assert.ok(yadav, 'UT Yadav must resolve to an image path');
  });

  it('resolves full names and canonical aliases to identical verified player assets', () => {
    const buttlerCanonical = getPlayerImageUrl('JC Buttler');
    const buttlerFull = getPlayerImageUrl('Jos Buttler');
    assert.strictEqual(buttlerCanonical, buttlerFull, 'JC Buttler and Jos Buttler must map to the same image');

    const gaikwadCanonical = getPlayerImageUrl('RD Gaikwad');
    const gaikwadFull = getPlayerImageUrl('Ruturaj Gaikwad');
    assert.strictEqual(gaikwadCanonical, gaikwadFull, 'RD Gaikwad and Ruturaj Gaikwad must map to the same image');

    const shawCanonical = getPlayerImageUrl('PP Shaw');
    const shawFull = getPlayerImageUrl('Prithvi Shaw');
    assert.strictEqual(shawCanonical, shawFull, 'PP Shaw and Prithvi Shaw must map to the same image');
  });

  it('resolves case-insensitively and slug variants', () => {
    assert.strictEqual(getPlayerImageUrl('jos buttler'), getPlayerImageUrl('Jos Buttler'));
    assert.strictEqual(getPlayerImageUrl('jc buttler'), getPlayerImageUrl('JC Buttler'));
    assert.strictEqual(getPlayerImageUrl('jc-buttler'), getPlayerImageUrl('JC Buttler'));
  });

  it('returns null for proprietary or unmapped players so clean fallback is used', () => {
    // Proprietary media removed for licensing compliance
    assert.strictEqual(getPlayerImageUrl('Virat Kohli'), null);
    assert.strictEqual(getPlayerImageUrl('V Kohli'), null);
    assert.strictEqual(getPlayerImageUrl('Rohit Sharma'), null);
    assert.strictEqual(getPlayerImageUrl('RG Sharma'), null);
    assert.strictEqual(getPlayerImageUrl('David Warner'), null);
    assert.strictEqual(getPlayerImageUrl('DA Warner'), null);
    assert.strictEqual(getPlayerImageUrl('NonExistent Cricketer 9999'), null);
    assert.strictEqual(getPlayerImageUrl(''), null);
    assert.strictEqual(getPlayerImageUrl(null), null);
    assert.strictEqual(getPlayerImageUrl(undefined), null);
  });
});

describe('Player Initials Monogram Generation', () => {
  it('generates two-letter monograms from multi-word names', () => {
    assert.strictEqual(getPlayerInitials('Virat Kohli'), 'VK');
    assert.strictEqual(getPlayerInitials('V Kohli'), 'VK');
    assert.strictEqual(getPlayerInitials('Rohit Sharma'), 'RS');
    assert.strictEqual(getPlayerInitials('Jos Buttler'), 'JB');
    assert.strictEqual(getPlayerInitials('AB de Villiers'), 'AV');
  });

  it('handles single-name batters cleanly', () => {
    assert.strictEqual(getPlayerInitials('Hardik'), 'HA');
    assert.strictEqual(getPlayerInitials('Rinku'), 'RI');
  });

  it('handles empty or missing names with clean placeholder', () => {
    assert.strictEqual(getPlayerInitials(''), '?');
    assert.strictEqual(getPlayerInitials(null), '?');
    assert.strictEqual(getPlayerInitials(undefined), '?');
  });
});

describe('Asset Storage & Attribution Integrity', () => {
  it('preserves attribution notice in public assets directory with verified terms', () => {
    const attributionPath = path.join(projectRoot, 'public/assets/players/ATTRIBUTION.md');
    assert.ok(fs.existsSync(attributionPath), 'ATTRIBUTION.md must exist in public/assets/players/');

    const content = fs.readFileSync(attributionPath, 'utf8');
    assert.ok(content.includes('Wikimedia Commons'), 'Must reference Wikimedia Commons');
    assert.ok(content.includes('Jos Buttler'), 'Must reference Jos Buttler entry');
    assert.ok(content.includes('CC BY 2.0'), 'Must document CC BY 2.0');
    assert.ok(content.includes('GODL-India'), 'Must document GODL-India');
  });

  it('verifies verified Wikimedia player WebP image files exist on disk', () => {
    const verifiedSlugs = ['jc-buttler.webp', 'rd-gaikwad.webp', 'pp-shaw.webp', 'mohommed-shami.webp', 'ut-yadav.webp'];
    for (const slug of ['jc-buttler.webp', 'rd-gaikwad.webp', 'pp-shaw.webp', 'mohammed-shami.webp', 'ut-yadav.webp']) {
      const filePath = path.join(projectRoot, 'public/assets/players', slug);
      assert.ok(fs.existsSync(filePath), `Verified player asset ${slug} must exist on disk`);
      const stat = fs.statSync(filePath);
      assert.ok(stat.size > 1000, `Player asset ${slug} should have valid byte size (>1KB)`);
      assert.ok(stat.size < 500000, `Player asset ${slug} should be optimized (<500KB)`);
    }
  });

  it('verifies PlayerPortrait and PlayerAvatar component files exist', () => {
    const portraitPath = path.join(projectRoot, 'src/components/PlayerPortrait.jsx');
    const avatarPath = path.join(projectRoot, 'src/components/PlayerAvatar.jsx');
    assert.ok(fs.existsSync(portraitPath), 'PlayerPortrait.jsx must exist');
    assert.ok(fs.existsSync(avatarPath), 'PlayerAvatar.jsx must exist');
  });

  it('verifies PlayerPortrait implements fallback handling and Gold & Onyx styles', () => {
    const portraitPath = path.join(projectRoot, 'src/components/PlayerPortrait.jsx');
    const content = fs.readFileSync(portraitPath, 'utf8');
    assert.ok(content.includes('onError'), 'PlayerPortrait must handle onError for broken images');
    assert.ok(content.includes('player-portrait-fallback'), 'PlayerPortrait must include fallback testid');
    assert.ok(content.includes('#A8893D'), 'PlayerPortrait must include Gold border styling');
    assert.ok(content.includes('#D4AF57'), 'PlayerPortrait must include Gold text styling');
    assert.ok(content.includes('loading="lazy"'), 'PlayerPortrait must support lazy loading');
  });
});
