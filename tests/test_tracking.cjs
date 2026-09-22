const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const appCode = fs.readFileSync(path.join(root, 'static/app.js'), 'utf8');
const resultCode = fs.readFileSync(path.join(root, 'static/static-fortune.js'), 'utf8');
const html = fs.readFileSync(path.join(root, '_site/result.html'), 'utf8');
const data = JSON.parse(html.match(/window.FORTUNE_DATA=(.*?);<\/script>/s)[1]);

function environment({ landing = false, result = false, saved = null, beacon = true } = {}) {
  const events = [];
  const callbacks = {};
  const form = { addEventListener() {} };
  const profile = { dataset: {} };
  const document = {
    body: { dataset: { backendOrigin: 'https://backend.example' }, hasAttribute: key => key === 'data-static-result' && result },
    addEventListener: (name, callback) => { callbacks[name] = callback; },
    querySelector: selector => selector === '[data-fortune-form]' && landing ? form : selector === '.oni-profile' ? profile : null,
    querySelectorAll: () => [],
  };
  const location = { origin: 'https://pages.example', replace(url) { this.redirect = url; } };
  const context = vm.createContext({
    document, window: { location, FORTUNE_DATA: data },
    sessionStorage: { getItem: () => saved, removeItem: () => { saved = null; } },
    navigator: { sendBeacon: (url, blob) => { if (beacon) events.push(JSON.parse(blob.body).event); return beacon; } },
    Blob: class { constructor(parts) { this.body = parts.join(''); } },
    fetch: (url, options) => { if (options.body) events.push(JSON.parse(options.body).event); return Promise.resolve(); },
    Intl, Date, console,
  });
  return { events, document, location, context, start() { vm.runInContext(appCode, context); callbacks.DOMContentLoaded(); } };
}

test('landing counts one PV and one entry, including beacon fallback', () => {
  for (const beacon of [true, false]) {
    const env = environment({ landing: true, beacon });
    env.start();
    assert.deepEqual(env.events, ['page_view', 'landing_view']);
  }
});

test('successful Pages rendering counts completion once, reload does not', () => {
  const env = environment({ result: true, saved: JSON.stringify({ name: '計測テスト', birthday: '1990-01-01' }) });
  vm.runInContext(resultCode, env.context);
  assert.equal(env.document.body.dataset.readingReady, 'true');
  env.start();
  assert.deepEqual(env.events, ['page_view', 'pages_fortune_completed']);
  delete env.document.body.dataset.readingReady;
  vm.runInContext(resultCode, env.context);
  env.start();
  assert.equal(env.location.redirect, './#uranau');
  assert.deepEqual(env.events, ['page_view', 'pages_fortune_completed']);
});

test('direct result visits do not count a template as a reading or PV', () => {
  const env = environment({ result: true });
  vm.runInContext(resultCode, env.context);
  env.start();
  assert.equal(env.location.redirect, './#uranau');
  assert.deepEqual(env.events, []);
});

test('server-rendered result does not send a second completion', () => {
  const env = environment();
  env.start();
  assert.deepEqual(env.events, ['page_view']);
});
