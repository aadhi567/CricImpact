import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, '..');

test('Mobile Responsive Layout & Viewport Boundaries', async (t) => {
  await t.test('index.css enforces universal box-sizing and html/body 100% boundary', () => {
    const cssPath = path.join(srcDir, 'index.css');
    const content = fs.readFileSync(cssPath, 'utf8');

    assert.ok(content.includes('box-sizing: border-box;'), 'index.css must include box-sizing: border-box');
    assert.ok(content.includes('max-width: 100%;'), 'index.css must include max-width: 100% for html and body');
    assert.ok(content.includes('overflow-wrap: break-word;'), 'index.css must include overflow-wrap for headings');
  });

  await t.test('App.jsx main layout element uses min-w-0 and w-full', () => {
    const appPath = path.join(srcDir, 'App.jsx');
    const content = fs.readFileSync(appPath, 'utf8');

    assert.ok(content.includes('min-w-0'), 'App.jsx main container must include min-w-0 to prevent flex blowout');
    assert.ok(content.includes('w-full'), 'App.jsx main container must use w-full rather than fixed percentage');
  });

  await t.test('Navbar.jsx and Logo fit within 320px viewport without overflow', () => {
    const navPath = path.join(srcDir, 'components', 'Navbar.jsx');
    const navContent = fs.readFileSync(navPath, 'utf8');
    const logoPath = path.join(srcDir, 'components', 'CricImpactLogo.jsx');
    const logoContent = fs.readFileSync(logoPath, 'utf8');

    assert.ok(navContent.includes('min-w-0'), 'Navbar mobile controls must have min-w-0');
    assert.ok(logoContent.includes("navbar: 'w-[110px]"), 'Navbar logo width preset must start at 110px on mobile');
  });

  await t.test('SeasonFilter.jsx pill buttons and dropdowns wrap responsively', () => {
    const filterPath = path.join(srcDir, 'components', 'SeasonFilter.jsx');
    const content = fs.readFileSync(filterPath, 'utf8');

    assert.ok(content.includes('flex flex-wrap sm:inline-flex'), 'Min runs filter must wrap on mobile screens');
    assert.ok(content.includes('max-w-full'), 'Filter pill bar must enforce max-w-full');
    assert.ok(!content.includes('sm:flex-nowrap'), 'Dropdowns row must not force sm:flex-nowrap');
  });

  await t.test('Footer.jsx uses w-full and wraps engine status text', () => {
    const footerPath = path.join(srcDir, 'components', 'Footer.jsx');
    const content = fs.readFileSync(footerPath, 'utf8');

    assert.ok(content.includes('w-full'), 'Footer container must use w-full');
    assert.ok(content.includes('break-words'), 'Subfooter text must allow break-words on mobile');
  });
});
