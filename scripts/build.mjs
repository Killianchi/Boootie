// Assembles dist/index.html from src/index.html, site.config.json and the
// generated doodle SVGs, then copies public/ into dist/.
//   {{key}}      config value, HTML-escaped
//   {{{key}}}    config value, raw
//   {{> name}}   inline src/doodles/name.svg
import { readFileSync, writeFileSync, mkdirSync, cpSync, existsSync } from 'fs';

const root = new URL('../', import.meta.url).pathname;
const cfg = JSON.parse(readFileSync(root + 'site.config.json', 'utf8'));
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const money = n => '$' + Number(n).toLocaleString('en-US');

// derived values
const underlineSvg = readFileSync(root + 'src/doodles/underline.svg', 'utf8');
const headlineHtml = h => esc(h).replace(/\[([^\]]+)\]/, (_, w) => `<span class="u">${w}${underlineSvg}</span>`);
const v = {
  ...cfg,
  price: money(cfg.priceUsd),
  deposit: money(cfg.depositUsd),
  rest: money(cfg.priceUsd - cfg.depositUsd),
  headline: headlineHtml(cfg.headlines[cfg.headlineIndex] ?? cfg.headlines[0]),
  headlinesJson: esc(JSON.stringify(cfg.headlines.map(h => headlineHtml(h)))),
  year: new Date().getFullYear(),
  formAction: `https://formspree.io/f/${cfg.formspreeId}`,
  ogImage: `${cfg.siteUrl}/img/og.png`,
};

let html = readFileSync(root + 'src/index.html', 'utf8');
html = html.replace(/\{\{>\s*([\w-]+)\s*\}\}/g, (_, name) => {
  const p = `${root}src/doodles/${name}.svg`;
  if (!existsSync(p)) throw new Error(`missing doodle partial: ${name}`);
  return readFileSync(p, 'utf8');
});
html = html.replace(/\{\{\{(\w+)\}\}\}/g, (_, k) => { if (!(k in v)) throw new Error(`unknown key ${k}`); return String(v[k]); });
html = html.replace(/\{\{(\w+)\}\}/g, (_, k) => { if (!(k in v)) throw new Error(`unknown key ${k}`); return k === 'headline' || k === 'headlinesJson' ? String(v[k]) : esc(v[k]); });

mkdirSync(root + 'dist', { recursive: true });
cpSync(root + 'public', root + 'dist', { recursive: true });
writeFileSync(root + 'dist/index.html', html);
{
  // light minification: strip comments and leading indentation (no tooling needed)
  const js = readFileSync(root + 'src/js/main.js', 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').split('\n').map(l => l.trim()).filter(Boolean).join('\n');
  writeFileSync(root + 'dist/main.js', js);
}
writeFileSync(root + 'dist/robots.txt', `User-agent: *\nAllow: /\nSitemap: ${cfg.siteUrl}/sitemap.xml\n`);
writeFileSync(root + 'dist/sitemap.xml', `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>${cfg.siteUrl}/</loc></url></urlset>\n`);
console.log(`built dist/index.html (${(html.length / 1024).toFixed(0)} KB)`);
if (cfg.stripeLink.includes('REPLACE_ME') || cfg.formspreeId.includes('REPLACE_ME')) console.warn('warning: placeholder values still in site.config.json');
