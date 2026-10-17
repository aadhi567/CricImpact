import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { getApiBaseUrl, buildApiUrl, API_BASE } from './api.js';

describe('API URL Strategy and Base URL Resolution', () => {
  const PROD_RENDER_ORIGIN = 'https://cricimpact.onrender.com';
  const PROD_RENDER_WITH_API = 'https://cricimpact.onrender.com/api';

  describe('getApiBaseUrl', () => {
    test('defaults to /api when env is undefined', () => {
      assert.equal(getApiBaseUrl(undefined), '/api');
    });

    test('defaults to /api when env is empty or whitespace', () => {
      assert.equal(getApiBaseUrl(''), '/api');
      assert.equal(getApiBaseUrl('   '), '/api');
    });

    test('defaults to /api when env is root slash', () => {
      assert.equal(getApiBaseUrl('/'), '/api');
      assert.equal(getApiBaseUrl('///'), '/api');
    });

    test('preserves relative /api without doubling', () => {
      assert.equal(getApiBaseUrl('/api'), '/api');
      assert.equal(getApiBaseUrl('/api/'), '/api');
      assert.equal(getApiBaseUrl('  /api///  '), '/api');
    });

    test('appends /api to domain origin without /api prefix', () => {
      assert.equal(getApiBaseUrl(PROD_RENDER_ORIGIN), 'https://cricimpact.onrender.com/api');
      assert.equal(getApiBaseUrl('https://cricimpact.onrender.com/'), 'https://cricimpact.onrender.com/api');
      assert.equal(getApiBaseUrl('https://cricimpact.onrender.com///'), 'https://cricimpact.onrender.com/api');
    });

    test('preserves domain that already includes /api without doubling', () => {
      assert.equal(getApiBaseUrl(PROD_RENDER_WITH_API), 'https://cricimpact.onrender.com/api');
      assert.equal(getApiBaseUrl('https://cricimpact.onrender.com/api/'), 'https://cricimpact.onrender.com/api');
      assert.equal(getApiBaseUrl('https://cricimpact.onrender.com/api///'), 'https://cricimpact.onrender.com/api');
    });

    test('works with custom subpaths ending with api', () => {
      assert.equal(getApiBaseUrl('https://api.cricimpact.com/v1/api'), 'https://api.cricimpact.com/v1/api');
      assert.equal(getApiBaseUrl('https://api.cricimpact.com/v1'), 'https://api.cricimpact.com/v1/api');
    });
  });

  describe('buildApiUrl with production origin (https://cricimpact.onrender.com)', () => {
    test('resolves /competitions to production backend /api/competitions', () => {
      const url = buildApiUrl('/competitions', PROD_RENDER_ORIGIN);
      assert.equal(url, 'https://cricimpact.onrender.com/api/competitions');
    });

    test('resolves /seasons with query parameters', () => {
      const url = buildApiUrl('/seasons?competition=ipl', PROD_RENDER_ORIGIN);
      assert.equal(url, 'https://cricimpact.onrender.com/api/seasons?competition=ipl');
    });

    test('resolves /match/{id}/player/{player} with query parameters', () => {
      const url = buildApiUrl('/match/1254065/player/M%20Shahrukh%20Khan?competition=ipl', PROD_RENDER_ORIGIN);
      assert.equal(url, 'https://cricimpact.onrender.com/api/match/1254065/player/M%20Shahrukh%20Khan?competition=ipl');
    });

    test('resolves /teams, /dashboard/summary, and /players', () => {
      assert.equal(
        buildApiUrl('/teams?season=2024&competition=ipl', PROD_RENDER_ORIGIN),
        'https://cricimpact.onrender.com/api/teams?season=2024&competition=ipl'
      );
      assert.equal(
        buildApiUrl('/dashboard/summary?season=2024&competition=ipl', PROD_RENDER_ORIGIN),
        'https://cricimpact.onrender.com/api/dashboard/summary?season=2024&competition=ipl'
      );
      assert.equal(
        buildApiUrl('/players?season=2024&competition=ipl', PROD_RENDER_ORIGIN),
        'https://cricimpact.onrender.com/api/players?season=2024&competition=ipl'
      );
    });

    test('resolves ground analysis, matchups, and career endpoints', () => {
      assert.equal(
        buildApiUrl('/ground-analysis/venues?competition=combined', PROD_RENDER_ORIGIN),
        'https://cricimpact.onrender.com/api/ground-analysis/venues?competition=combined'
      );
      assert.equal(
        buildApiUrl('/matchups/rankings?season=2024', PROD_RENDER_ORIGIN),
        'https://cricimpact.onrender.com/api/matchups/rankings?season=2024'
      );
      assert.equal(
        buildApiUrl('/player/V%20Kohli/career?competition=combined', PROD_RENDER_ORIGIN),
        'https://cricimpact.onrender.com/api/player/V%20Kohli/career?competition=combined'
      );
    });

    test('prevents duplicate /api prefix if path already includes /api/', () => {
      assert.equal(
        buildApiUrl('/api/competitions', PROD_RENDER_ORIGIN),
        'https://cricimpact.onrender.com/api/competitions'
      );
      assert.equal(
        buildApiUrl('/api/seasons?competition=ipl', PROD_RENDER_ORIGIN),
        'https://cricimpact.onrender.com/api/seasons?competition=ipl'
      );
      assert.equal(
        buildApiUrl('/api?check=1', PROD_RENDER_ORIGIN),
        'https://cricimpact.onrender.com/api?check=1'
      );
    });

    test('handles paths without leading slash', () => {
      assert.equal(
        buildApiUrl('competitions', PROD_RENDER_ORIGIN),
        'https://cricimpact.onrender.com/api/competitions'
      );
    });

    test('handles empty or root path', () => {
      assert.equal(buildApiUrl('', PROD_RENDER_ORIGIN), 'https://cricimpact.onrender.com/api');
      assert.equal(buildApiUrl('/', PROD_RENDER_ORIGIN), 'https://cricimpact.onrender.com/api');
      assert.equal(buildApiUrl('/api', PROD_RENDER_ORIGIN), 'https://cricimpact.onrender.com/api');
    });
  });

  describe('buildApiUrl in development mode (relative /api proxy)', () => {
    test('resolves /competitions to relative /api/competitions', () => {
      assert.equal(buildApiUrl('/competitions', undefined), '/api/competitions');
    });

    test('resolves /seasons with query parameters', () => {
      assert.equal(buildApiUrl('/seasons?competition=ipl', undefined), '/api/seasons?competition=ipl');
    });

    test('resolves /match/{id}/player/{player} with query parameters', () => {
      assert.equal(
        buildApiUrl('/match/1254065/player/M%20Shahrukh%20Khan?competition=ipl', undefined),
        '/api/match/1254065/player/M%20Shahrukh%20Khan?competition=ipl'
      );
    });

    test('handles path already starting with /api', () => {
      assert.equal(buildApiUrl('/api/competitions', undefined), '/api/competitions');
    });

    test('API_BASE constant defaults to /api when VITE_API_BASE_URL is not set', () => {
      assert.equal(API_BASE, '/api');
    });
  });

  describe('Trailing slashes normalization', () => {
    test('strips single and multiple trailing slashes from origin URL', () => {
      assert.equal(getApiBaseUrl('https://cricimpact.onrender.com/'), 'https://cricimpact.onrender.com/api');
      assert.equal(getApiBaseUrl('https://cricimpact.onrender.com///'), 'https://cricimpact.onrender.com/api');
      assert.equal(buildApiUrl('/matches', 'https://cricimpact.onrender.com/'), 'https://cricimpact.onrender.com/api/matches');
      assert.equal(buildApiUrl('/matches', 'https://cricimpact.onrender.com///'), 'https://cricimpact.onrender.com/api/matches');
    });

    test('strips trailing slashes from origin URL that already has /api', () => {
      assert.equal(getApiBaseUrl('https://cricimpact.onrender.com/api/'), 'https://cricimpact.onrender.com/api');
      assert.equal(getApiBaseUrl('https://cricimpact.onrender.com/api///'), 'https://cricimpact.onrender.com/api');
      assert.equal(buildApiUrl('/players', 'https://cricimpact.onrender.com/api/'), 'https://cricimpact.onrender.com/api/players');
    });

    test('strips trailing slashes from local fallback /api', () => {
      assert.equal(getApiBaseUrl('/api/'), '/api');
      assert.equal(getApiBaseUrl('/api///'), '/api');
      assert.equal(buildApiUrl('/players', '/api/'), '/api/players');
    });
  });

  describe('Duplicate-prefix prevention (/api/api prevention)', () => {
    test('never produces /api/api when env is bare origin and path begins with /api', () => {
      const url = buildApiUrl('/api/players?season=2024', PROD_RENDER_ORIGIN);
      assert.equal(url, 'https://cricimpact.onrender.com/api/players?season=2024');
      assert.doesNotMatch(url, /\/api\/api/);
    });

    test('never produces /api/api when env already ends with /api and path begins with /api', () => {
      const url = buildApiUrl('/api/dashboard/summary', PROD_RENDER_WITH_API);
      assert.equal(url, 'https://cricimpact.onrender.com/api/dashboard/summary');
      assert.doesNotMatch(url, /\/api\/api/);
    });

    test('never produces /api/api in local dev when path begins with /api', () => {
      const url = buildApiUrl('/api/matchups/rankings');
      assert.equal(url, '/api/matchups/rankings');
      assert.doesNotMatch(url, /\/api\/api/);
    });

    test('handles path without leading slash without duplication', () => {
      const urlProd = buildApiUrl('api/seasons', PROD_RENDER_ORIGIN);
      assert.equal(urlProd, 'https://cricimpact.onrender.com/api/seasons');
      assert.doesNotMatch(urlProd, /\/api\/api/);

      const urlDev = buildApiUrl('api/seasons');
      assert.equal(urlDev, '/api/seasons');
      assert.doesNotMatch(urlDev, /\/api\/api/);
    });
  });
});
