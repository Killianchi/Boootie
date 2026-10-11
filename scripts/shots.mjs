// Screenshots dist/ at 390px and 1440px for review: full page plus one image per
// section. Usage: node scripts/shots.mjs [outdir] [--reduced]
import { chromium } from 'playwright';
import { createServer } from 'http';
import { readFile } from 'fs/promises';
import { mkdirSync } from 'fs';
import { extname } from 'path';

const root = new URL('../', import.meta.url).pathname;
const args = process.argv.slice(2);
const outDir = (args.find(a => !a.startsWith('--')) || root + 'shots') + '/';
mkdirSync(outDir, { recursive: true });
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.png': 'image/png', '.woff2': 'font/woff2', '.glb': 'model/gltf-binary' };
const srv = createServer(async (req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]); if (p === '/') p = '/index.html';
  try { const b = await readFile(root + 'dist' + p); res.writeHead(200, { 'content-type': types[extname(p)] || 'application/octet-stream' }); res.end(b); }
  catch { res.writeHead(404); res.end('not found'); }
});
await new Promise(r => srv.listen(0, r)); const port = srv.address().port;
const browser = await chromium.launch();
for (const [label, vp] of [['m', { width: 390, height: 780 }], ['d', { width: 1440, height: 900 }]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: label === 'm' ? 2 : 1, reducedMotion: args.includes('--reduced') ? 'reduce' : 'no-preference' });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${outDir}${label}-hero.png` });
  // walk the page so every section draws in, then full page
  const h = await page.evaluate(() => document.body.scrollHeight);
  for (let y = 0; y < h; y += vp.height * 0.6) { await page.evaluate(y => window.scrollTo(0, y), y); await page.waitForTimeout(120); }
  await page.waitForTimeout(1600);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${outDir}${label}-full.png`, fullPage: true });
  for (const id of ['how', 'can', 'object', 'preorder', 'faq']) {
    const el = await page.$('#' + id);
    if (el) await el.screenshot({ path: `${outDir}${label}-${id}.png` });
  }
  const footer = await page.$('footer'); if (footer) await footer.screenshot({ path: `${outDir}${label}-footer.png` });
  if (label === 'm') {
    await page.evaluate(() => window.scrollTo(0, 900)); await page.waitForTimeout(600);
    await page.screenshot({ path: `${outDir}m-sticky.png` });
  }
  const weight = await page.evaluate(() => performance.getEntriesByType('resource').reduce((n, r) => n + (r.transferSize || r.encodedBodySize || 0), 0) + (performance.getEntriesByType('navigation')[0]?.transferSize || 0));
  console.log(`${label}: page height ${h}px, transferred ~${(weight / 1024).toFixed(0)} KB, console errors: ${errors.length}`);
  errors.forEach(e => console.log('  ', e.slice(0, 200)));
  await ctx.close();
}
await browser.close(); srv.close();
