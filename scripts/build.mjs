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
// Until a real Stripe Payment Link is configured, the buy buttons become an honest
// "Get launch updates" link to the signup form, so the site can be live without a dead checkout.
const stripeReady = !/REPLACE_ME/.test(cfg.stripeLink);
const v = {
  ...cfg,
  cta: stripeReady ? cfg.cta : 'Get launch updates',
  stripeLink: stripeReady ? cfg.stripeLink : '#signup',
  holdLine: stripeReady ? `hold one for ${money(cfg.depositUsd)}` : 'deposits open soon',
  price: money(cfg.priceUsd),
  retail: money(cfg.retailUsd),
  deposit: money(cfg.depositUsd),
  rest: money(cfg.priceUsd - cfg.depositUsd),
  headline: headlineHtml(cfg.headlines[cfg.headlineIndex] ?? cfg.headlines[0]),
  headlinesJson: esc(JSON.stringify(cfg.headlines.map(h => headlineHtml(h)))),
  year: new Date().getFullYear(),
  formAction: `https://formspree.io/f/${cfg.formspreeId}`,
  ogImage: `${cfg.siteUrl}/img/og.png`,
  // contact details for the legal pages; blanks render as visible placeholders
  legalName: cfg.legalName || '[name to be added]',
  legalAddressHtml: (cfg.legalAddress || '[postal address to be added]').split('\n').map(esc).join('<br>'),
  contactEmail: cfg.contactEmail || 'contact-email-to-be-added',
};

const render = (tpl, extra = {}) => {
  const vals = { ...v, ...extra };
  tpl = tpl.replace(/\{\{>\s*([\w-]+)\s*\}\}/g, (_, name) => {
    const p = `${root}src/doodles/${name}.svg`;
    if (!existsSync(p)) throw new Error(`missing doodle partial: ${name}`);
    return readFileSync(p, 'utf8');
  });
  tpl = tpl.replace(/\{\{\{(\w+)\}\}\}/g, (_, k) => { if (!(k in vals)) throw new Error(`unknown key ${k}`); return String(vals[k]); });
  return tpl.replace(/\{\{(\w+)\}\}/g, (_, k) => { if (!(k in vals)) throw new Error(`unknown key ${k}`); return k === 'headline' || k === 'headlinesJson' ? String(vals[k]) : esc(vals[k]); });
};
const html = render(readFileSync(root + 'src/index.html', 'utf8'));
const layout = readFileSync(root + 'src/legal-layout.html', 'utf8');
const legalPages = [
  { slug: 'privacy', title: 'Privacy Policy', description: 'How the boootie app, device and website handle your data.' },
  { slug: 'support', title: 'Support', description: 'Get help with boootie, the app or your pre-order.' },
];
mkdirSync(root + 'dist', { recursive: true });
cpSync(root + 'public', root + 'dist', { recursive: true });
writeFileSync(root + 'dist/index.html', html);
for (const pg of legalPages) {
  const body = render(readFileSync(`${root}src/${pg.slug}.body.html`, 'utf8'));
  writeFileSync(`${root}dist/${pg.slug}.html`, render(layout, { pageTitle: pg.title, pageDescription: pg.description, pageSlug: pg.slug, pageBody: body }));
}
{
  // light minification: strip comments and leading indentation (no tooling needed)
  const js = readFileSync(root + 'src/js/main.js', 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').split('\n').map(l => l.trim()).filter(Boolean).join('\n');
  writeFileSync(root + 'dist/main.js', js);
}
writeFileSync(root + 'dist/robots.txt', `User-agent: *\nAllow: /\nSitemap: ${cfg.siteUrl}/sitemap.xml\n`);
writeFileSync(root + 'dist/sitemap.xml', `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>${cfg.siteUrl}/</loc></url>${legalPages.map(pg => `<url><loc>${cfg.siteUrl}/${pg.slug}</loc></url>`).join('')}</urlset>\n`);
console.log(`built dist/index.html (${(html.length / 1024).toFixed(0)} KB)`);
if (!cfg.legalName || !cfg.legalAddress || !cfg.contactEmail) console.warn('warning: legalName, legalAddress or contactEmail is empty; the privacy and support pages show placeholders');
if (cfg.stripeLink.includes('REPLACE_ME') || cfg.formspreeId.includes('REPLACE_ME')) console.warn('warning: placeholder values still in site.config.json');
