#!/usr/bin/env node
/* Re-shoot the topic-review tour photograph and measure where its controls sit.

   node scripts/topic_review_shots.mjs [--url <page url>] [--out docs/topic_review/shots/tour.png] [--measure] [--eval <js>]

   Drives headless Chrome over the DevTools protocol (no puppeteer needed: Node 22 has WebSocket).
   Default URL is the fisheries dashboard from file://, 1600x1000, which is what explain.html's pins
   are measured against. --measure prints each named control's box as % of the viewport, so the
   STEPS in explain.html can be re-pinned after a layout change instead of guessed. */
import { spawn } from 'node:child_process';
import { writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

const args = Object.fromEntries(process.argv.slice(2).map((a, i, arr) => a.startsWith('--') ? [a.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : true] : []).filter(Boolean));
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const url = args.url || `file://${root}/docs/topic_review/review.html?topic=fisheries&rule=d_fisheries`;
const out = args.out || path.join(root, 'docs/topic_review/shots/tour.png');
const W = 1600, H = 1000;

/* what the tour points at: name -> CSS selector (first match) */
const TARGETS = {
  selector: '#ruleSel', selectorLabel: '.sellab', ruleCount: '#ruleCount', defn: '#defn', defnWhat: '#defn span:nth-child(1), #defn span:nth-child(2)', defnSize: '#defn span:nth-child(3)', sideTag: '#viewport .row .side',
  verdictButtons: '#tb1 button[data-act="in"], #tb1 button[data-act="unsure"]', bulkButtons: '#tb1 button[data-act="above"], #tb1 button[data-act="below"]',
  showOrder: '#tb2', firstRow: '#viewport .row', line: '#viewport .line', tabs: '#rtabs',
  paperPanel: '#p-paper', rulePanel: '#p-rule', threshold: '#theta', weights: '.wgrid', keywords: '#p-rule table:last-of-type',
};

const dir = mkdtempSync(path.join(tmpdir(), 'tr-shot-'));
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn('google-chrome', ['--headless=new', '--disable-gpu', '--hide-scrollbars', `--window-size=${W},${H}`, `--remote-debugging-port=${port}`, `--user-data-dir=${dir}`, '--allow-file-access-from-files', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
try {
  let targets; console.error('chrome pid', chrome.pid, 'port', port);
  for (let i = 0; i < 50; i++) { try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (targets.length) break; } catch {} await sleep(200); }
  console.error('targets', targets && targets.map(t => t.type + ' ' + t.url).join(' ; ')); const pg = (targets || []).find(t => t.type === 'page') || targets[0]; const ws = new WebSocket(pg.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = e => j(new Error('ws error')); }); console.error('ws open');
  let id = 0; const pending = new Map();
  ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  await send('Page.enable'); await send('Runtime.enable');
  await send('Page.navigate', { url }); console.error('navigated');
  /* wait for the dashboard to have drawn rows (data files load asynchronously); other pages just get a moment */
  for (let i = 0; i < 100; i++) { const r = await send('Runtime.evaluate', { expression: `document.querySelectorAll('#viewport .row').length + (document.querySelector('#viewport') ? 0 : 1)`, returnByValue: true }); if (r.result?.result?.value > 0) break; await sleep(200); }
  await sleep(600);
  if (args.measure) {
    const expr = `(${JSON.stringify(TARGETS)}, (() => { const T = ${JSON.stringify(TARGETS)}, o = {}; for (const [k, sel] of Object.entries(T)) { const els = [...document.querySelectorAll(sel)]; if (!els.length) { o[k] = null; continue; }
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; for (const e of els) { const b = e.getBoundingClientRect(); if (!b.width) continue; x0 = Math.min(x0, b.left); y0 = Math.min(y0, b.top); x1 = Math.max(x1, b.right); y1 = Math.max(y1, b.bottom); }
      if (x1 < x0) { o[k] = null; continue; } o[k] = { x: +(100 * x0 / ${W}).toFixed(1), y: +(100 * y0 / ${H}).toFixed(1), w: +(100 * (x1 - x0) / ${W}).toFixed(1), h: +(100 * (y1 - y0) / ${H}).toFixed(1) }; } return o; })())`;
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
    console.log(JSON.stringify(r.result?.result?.value, null, 1));
  }
  if (args.eval) { const r = await send('Runtime.evaluate', { expression: String(args.eval), returnByValue: true, awaitPromise: true }); console.log(JSON.stringify(r.result?.result?.value ?? r.result?.exceptionDetails?.text)); }
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(out, Buffer.from(shot.result.data, 'base64'));
  console.error(`wrote ${out}`);
  ws.close();
} finally { const gone = new Promise(r => chrome.once('exit', r)); chrome.kill(); await gone; rmSync(dir, { recursive: true, force: true, maxRetries: 5 }); }
