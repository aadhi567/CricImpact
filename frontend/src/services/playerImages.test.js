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
    assert.strictEqual(slugifyPlayerName('Mitchell Marsh'), 'mitchell-marsh');
    assert.strictEqual(slugifyPlayerName('MR Marsh'), 'mr-marsh');
    assert.strictEqual(slugifyPlayerName(''), '');
    assert.strictEqual(slugifyPlayerName(null), '');
    assert.strictEqual(slugifyPlayerName(undefined), '');
  });

  it('resolves verified open-access player names to local WebP assets', () => {
    const verifiedNames = [
      'JC Buttler',
      'RD Gaikwad',
      'PP Shaw',
      'Mohammed Shami',
      'UT Yadav',
      'V Kohli',
      'RG Sharma',
      'MS Dhoni',
      'RA Jadeja',
      'KD Karthik',
    ];

    for (const name of verifiedNames) {
      const url = getPlayerImageUrl(name);
      assert.ok(url, `${name} must resolve to an image path`);
      assert.ok(url.endsWith('.webp'), `${name} image path must be a WebP asset`);
      assert.ok(url.startsWith('/assets/players/'), `${name} image path must point to /assets/players/`);
    }
  });

  it('resolves full names and canonical aliases to identical verified player assets', () => {
    // Buttler
    assert.strictEqual(
      getPlayerImageUrl('JC Buttler'),
      getPlayerImageUrl('Jos Buttler'),
      'JC Buttler and Jos Buttler must map to identical asset'
    );

    // Gaikwad
    assert.strictEqual(
      getPlayerImageUrl('RD Gaikwad'),
      getPlayerImageUrl('Ruturaj Gaikwad'),
      'RD Gaikwad and Ruturaj Gaikwad must map to identical asset'
    );

    // Kohli
    assert.strictEqual(
      getPlayerImageUrl('V Kohli'),
      getPlayerImageUrl('Virat Kohli'),
      'V Kohli and Virat Kohli must map to identical asset'
    );

    // Rohit Sharma
    assert.strictEqual(
      getPlayerImageUrl('RG Sharma'),
      getPlayerImageUrl('Rohit Sharma'),
      'RG Sharma and Rohit Sharma must map to identical asset'
    );

    // Mitchell Marsh (Phase 5 requirement)
    assert.strictEqual(
      getPlayerImageUrl('MR Marsh'),
      getPlayerImageUrl('Mitchell Marsh'),
      'MR Marsh and Mitchell Marsh must map to identical asset'
    );

    // Rasikh Salam / Rasikh Dar
    assert.strictEqual(
      getPlayerImageUrl('Rasikh Salam'),
      getPlayerImageUrl('Rasikh Dar'),
      'Rasikh Salam and Rasikh Dar must resolve to the same portrait asset'
    );
  });

  it('resolves case-insensitively and slug variants', () => {
    const canonical = getPlayerImageUrl('JC Buttler');
    assert.strictEqual(getPlayerImageUrl('jos buttler'), canonical);
    assert.strictEqual(getPlayerImageUrl('jc buttler'), canonical);
    assert.strictEqual(getPlayerImageUrl('jc-buttler'), canonical);
    assert.strictEqual(getPlayerImageUrl('jcbuttler'), canonical);

    const kohliCanonical = getPlayerImageUrl('V Kohli');
    assert.strictEqual(getPlayerImageUrl('virat kohli'), kohliCanonical);
    assert.strictEqual(getPlayerImageUrl('v kohli'), kohliCanonical);
    assert.strictEqual(getPlayerImageUrl('v-kohli'), kohliCanonical);
    assert.strictEqual(getPlayerImageUrl('vkohli'), kohliCanonical);
  });

  it('returns null for missing, unapproved, or non-existent players', () => {
    assert.strictEqual(getPlayerImageUrl('NonExistent Cricketer 9999'), null);
    assert.strictEqual(getPlayerImageUrl('Unknown Player Xyz 123'), null);
    assert.strictEqual(getPlayerImageUrl(''), null);
    assert.strictEqual(getPlayerImageUrl('   '), null);
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
    assert.strictEqual(getPlayerInitials('Mitchell Marsh'), 'MM');
  });

  it('handles single-name batters cleanly', () => {
    assert.strictEqual(getPlayerInitials('Hardik'), 'HA');
    assert.strictEqual(getPlayerInitials('Rinku'), 'RI');
    assert.strictEqual(getPlayerInitials('Shubman'), 'SH');
  });

  it('handles empty or missing names with clean placeholder', () => {
    assert.strictEqual(getPlayerInitials(''), '?');
    assert.strictEqual(getPlayerInitials('   '), '?');
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
    assert.ok(content.includes('CC BY'), 'Must document Creative Commons licenses');
    assert.ok(content.includes('GODL-India'), 'Must document GODL-India license terms');
    assert.ok(content.includes('CC0'), 'Must document CC0 terms');
  });

  it('verifies all mapped images in playerImages.json exist on disk with valid file size', () => {
    const jsonPath = path.join(projectRoot, 'src/constants/playerImages.json');
    assert.ok(fs.existsSync(jsonPath), 'playerImages.json must exist');

    const mapping = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
    assert.ok(Object.keys(mapping).length > 20, 'Mapping should contain rich player entries');

    const uniqueAssetPaths = [...new Set(Object.values(mapping))];
    assert.ok(uniqueAssetPaths.length >= 25, 'Should have at least 25 unique approved local portraits');

    for (const relPath of uniqueAssetPaths) {
      const cleanPath = relPath.replace(/^\//, '');
      const fullPath = path.join(projectRoot, 'public', cleanPath);
      assert.ok(fs.existsSync(fullPath), `Asset file ${relPath} must exist on disk at ${fullPath}`);

      const stat = fs.statSync(fullPath);
      assert.ok(stat.size > 1000, `Player asset ${relPath} must be > 1KB (got ${stat.size} bytes)`);
      assert.ok(stat.size < 500000, `Player asset ${relPath} must be < 500KB (got ${stat.size} bytes)`);
    }
  });

  it('verifies playerImages.js exports valid manifest matching playerImages.json', async () => {
    const jsPath = path.join(projectRoot, 'src/constants/playerImages.js');
    const jsonPath = path.join(projectRoot, 'src/constants/playerImages.json');
    assert.ok(fs.existsSync(jsPath), 'playerImages.js must exist');

    const jsonMapping = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
    const { default: jsMapping } = await import('../constants/playerImages.js');

    assert.deepStrictEqual(jsMapping, jsonMapping, 'playerImages.js and playerImages.json must be in exact sync');
  });

  it('verifies PlayerPortrait and PlayerAvatar component files exist', () => {
    const portraitPath = path.join(projectRoot, 'src/components/PlayerPortrait.jsx');
    const avatarPath = path.join(projectRoot, 'src/components/PlayerAvatar.jsx');
    assert.ok(fs.existsSync(portraitPath), 'PlayerPortrait.jsx must exist');
    assert.ok(fs.existsSync(avatarPath), 'PlayerAvatar.jsx must exist');
  });

  it('verifies PlayerPortrait implements fallback handling, CLS prevention, and Gold & Onyx styles', () => {
    const portraitPath = path.join(projectRoot, 'src/components/PlayerPortrait.jsx');
    const content = fs.readFileSync(portraitPath, 'utf8');
    assert.ok(content.includes('onError'), 'PlayerPortrait must handle onError for broken images');
    assert.ok(content.includes('player-portrait-fallback'), 'PlayerPortrait must include fallback testid');
    assert.ok(content.includes('#A8893D'), 'PlayerPortrait must include Gold border styling');
    assert.ok(content.includes('#D4AF57'), 'PlayerPortrait must include Gold text styling');
    assert.ok(content.includes('aspect-square'), 'PlayerPortrait must enforce aspect-square to prevent layout shifts (CLS)');
    assert.ok(content.includes('loading'), 'PlayerPortrait must handle loading attribute');
    assert.ok(content.includes('decoding="async"'), 'PlayerPortrait must use decoding="async"');
    assert.ok(content.includes('profile:'), 'PlayerPortrait must support prominent profile size token');
  });

  it('verifies PlayerAnalysis header incorporates prominent profile portrait without layout shifts', () => {
    const analysisPath = path.join(projectRoot, 'src/pages/PlayerAnalysis.jsx');
    const content = fs.readFileSync(analysisPath, 'utf8');
    assert.ok(content.includes('<PlayerPortrait'), 'PlayerAnalysis must render PlayerPortrait component');
    assert.ok(content.includes('size="profile"'), 'PlayerAnalysis header must use size="profile" for prominent display');
  });
});

describe('License Approval & Attribution Standards', () => {
  it('verifies attribution entries map to valid canonical identities', () => {
    const attributionPath = path.join(projectRoot, 'public/assets/players/ATTRIBUTION.md');
    const content = fs.readFileSync(attributionPath, 'utf8');
    const lines = content.split('\n').filter((l) => l.trim().startsWith('|') && !l.includes('---'));

    // Skip header row
    const dataRows = lines.slice(1);
    assert.ok(dataRows.length >= 25, 'Should have at least 25 attribution records');

    for (const row of dataRows) {
      const parts = row.split('|').map((s) => s.trim()).filter(Boolean);
      if (parts.length >= 5) {
        const canonicalId = parts[1].replace(/`/g, '');
        const license = parts[3];
        const source = parts[4];

        assert.ok(canonicalId.length > 0, 'Canonical ID must not be empty');
        assert.ok(license.length > 0, `License must be specified for ${canonicalId}`);
        assert.ok(source.length > 0, `Original source must be documented for ${canonicalId}`);

        // Must be open access
        const licLower = license.toLowerCase();
        const isApprovedLicense =
          license.includes('CC BY') ||
          license.includes('CC0') ||
          license.includes('GODL') ||
          licLower.includes('public domain') ||
          licLower.includes('open government') ||
          licLower.includes('cc-zero') ||
          licLower.includes('pd');
        assert.ok(
          isApprovedLicense,
          `License for ${canonicalId} must be an approved open-access license (found ${license})`
        );
      }
    }
  });
});
