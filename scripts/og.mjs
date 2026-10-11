// Renders the Open Graph image (1200x630): the hero doodle field, the sticker
// panel with the headline, and the product. Output: public/img/og.png.
// Run after `npm run build` (it reuses dist/style.css and the generated doodles).
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'fs';
import { createServer } from 'http';
import { readFile } from 'fs/promises';
import { extname } from 'path';
import sharp from 'sharp';

const root = new URL('../', import.meta.url).pathname;
const cfg = JSON.parse(readFileSync(root + 'site.config.json', 'utf8'));
const read = n => readFileSync(root + 'src/doodles/' + n + '.svg', 'utf8');
const headline = (cfg.headlines[cfg.headlineIndex] || cfg.headlines[0]).replace(/\[([^\]]+)\]/, (_, w) => `<span class="u">${w}${read('underline')}</span>`);

const html = `<!doctype html><html lang="en" class="js"><head><meta charset="utf-8"><link rel="stylesheet" href="/style.css">
<style>:root{--accent:${cfg.accent};--on-accent:${cfg.onAccent}} html,body{margin:0;width:1200px;height:630px;overflow:hidden;background:#fff}
.og{position:relative;width:1200px;height:630px;overflow:hidden}
.panel{position:absolute;left:64px;top:118px;width:560px;padding:36px 40px}
.panel h1{color:var(--accent)}
.panel h1{font-size:62px}
.panel p{font-size:24px;margin-top:16px}
.brand{position:absolute;left:64px;top:44px;font-size:34px}
.prod{position:absolute;right:70px;top:70px;width:520px;height:490px}
.prod img{position:relative;z-index:1;width:100%;height:100%;object-fit:contain}
</style></head><body>${read('symbols')}
<div class="og">
  ${read('hero-field-d').replace('class="field field-d doodle pending"', 'class="field doodle"').replace('viewBox="0 0 1440 900"', 'viewBox="120 120 1200 630"')}
  <div class="brand label-pill">boootie</div>
  <div class="glass panel"><h1>${headline}</h1><p>${cfg.subtext}</p></div>
  <div class="prod">${read('halo')}<img src="/img/poster.webp" alt=""></div>
</div></body></html>`;

const types = { '.css': 'text/css', '.webp': 'image/webp', '.woff2': 'font/woff2' };
const srv = createServer(async (req, res) => {
  const p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/') { res.writeHead(200, { 'content-type': 'text/html' }); return res.end(html); }
  try { const b = await readFile(root + 'dist' + p); res.writeHead(200, { 'content-type': types[extname(p)] || 'application/octet-stream' }); res.end(b); }
  catch { res.writeHead(404); res.end(); }
});
await new Promise(r => srv.listen(0, r)); const port = srv.address().port;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'networkidle' });
await page.waitForTimeout(600);
const png = await page.screenshot();
await browser.close(); srv.close();
writeFileSync(root + 'public/img/og.png', await sharp(png).png({ palette: true, colours: 256 }).toBuffer());
console.log('wrote public/img/og.png');
