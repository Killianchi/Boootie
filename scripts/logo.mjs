// Logo concepts: a doodled boot that reads as a lowercase "b".
// The boot shaft is the ascender, the toe curls round into the bowl.
// Renders a contact sheet plus each concept at favicon size for a legibility check.
// Usage: node scripts/logo.mjs <outdir>
import { motifs, renderMotif, line, poly, circ, ellipse, dot } from './doodle-lib.mjs';
import { writeFileSync, mkdirSync } from 'fs';
import { chromium } from 'playwright';

const out = (process.argv[2] || 'logo-out') + '/';
mkdirSync(out, { recursive: true });

// shared outline of the boot-b: shaft up the left, heel at bottom-left,
// sole along the bottom, toe rounding up and back into the shaft = the bowl
const bootB = () => poly([
  [26, 8], [26, 76],             // back of the shaft (the b's ascender)
  [21, 82], [23, 89], [34, 91],  // heel bump
  [70, 91], [86, 88], [94, 78],  // sole out to a round toe
  [94, 64], [86, 52], [72, 46],  // toe cap rising into the b's bowl
  [56, 45], [46, 47], [40, 51],  // top of the bowl back into the ankle
], false, false);
const shaftFront = () => line(40, 8, 40, 50);
const topCuff = () => line(26, 8, 40, 8);

motifs['logo-a'] = [bootB(), shaftFront(), topCuff()];
motifs['logo-b'] = [bootB(), shaftFront(), topCuff(), dot(62, 64, 3.6), dot(76, 64, 3.6), circ(69, 70, 8, 25, 155, 16)];
motifs['logo-c'] = [bootB(), shaftFront(), topCuff(), line(40, 91, 36, 99), line(30, 99, 40, 99), line(76, 90, 80, 99), line(76, 99, 86, 99)];
motifs['logo-d'] = [bootB(), shaftFront(), topCuff(), line(28, 18, 38, 22), line(28, 28, 38, 32), line(28, 38, 38, 42)];
motifs['logo-e'] = [bootB(), shaftFront(), topCuff(), poly([[28, 83], [90, 82]]), dot(74, 64, 4)];
motifs['logo-f'] = [bootB(), shaftFront(), topCuff(), dot(62, 64, 3.6), dot(76, 64, 3.6), circ(69, 70, 8, 25, 155, 16),
  poly([[82, 14], [85, 22], [93, 25], [85, 28], [82, 36], [79, 28], [71, 25], [79, 22]], true, true)];

const concepts = [
  ['logo-a', 'A. Plain boot-b', 'Cleanest. Reads as "b" first, boot second.'],
  ['logo-b', 'B. With a face', 'Same b, the bowl becomes a friendly face, like the site doodles.'],
  ['logo-c', 'C. Walking', 'Little legs: the "step into your phone" idea.'],
  ['logo-d', 'D. Laced shaft', 'Lace marks on the ascender make it unmistakably a boot.'],
  ['logo-e', 'E. Sole line', 'A sole stripe and one eye: more product, less character.'],
  ['logo-f', 'F. Face + sparkle', 'B plus a sparkle for the AI moment.'],
];

const sym = id => renderMotif(id, { wobble: 0.7, step: 6, seed: 3 });
const tile = (id, size, stroke, radius = 0.24) => `<svg width="${size}" height="${size}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <rect width="100" height="100" rx="${100 * radius}" fill="#000"/>
  <g transform="translate(5 4) scale(0.9)" fill="none" stroke="#fff" stroke-width="${stroke}" stroke-linecap="round" stroke-linejoin="round">${sym(id).replace(/class="dd"/g, 'fill="#fff" stroke="none"')}</g></svg>`;

for (const [id] of concepts) writeFileSync(`${out}${id}.svg`, tile(id, 512, 6.5));

const html = `<!doctype html><meta charset="utf-8"><style>
@font-face{font-family:Figtree;src:url(file:///home/user/Boootie/public/fonts/Figtree.woff2)}
body{margin:0;padding:32px;background:#f3f3f3;font-family:Figtree,sans-serif;width:1180px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:28px}
.card{background:#fff;border-radius:24px;padding:20px;box-shadow:0 10px 30px -18px rgba(0,0,0,.35)}
.row{display:flex;align-items:flex-end;gap:16px}
h3{margin:14px 0 4px;font-size:19px}p{margin:0;color:#444;font-size:14px;line-height:1.35}
.small{display:flex;gap:10px;align-items:center}
.lock{display:flex;align-items:center;gap:10px;margin-top:14px;background:#000;border-radius:16px;padding:10px 14px;width:max-content}
.lock span{color:#fff;font-weight:800;font-size:30px;letter-spacing:-.035em}
</style><div class="grid">${concepts.map(([id, name, note]) => `<div class="card">
<div class="row">${tile(id, 180, 6.5)}<div class="small">${tile(id, 48, 9)}${tile(id, 32, 11)}${tile(id, 16, 14)}</div></div>
<div class="lock">${tile(id, 44, 8)}<span>boootie</span></div>
<h3>${name}</h3><p>${note}</p></div>`).join('')}</div>`;
writeFileSync(out + 'sheet.html', html);
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1244, height: 900 }, deviceScaleFactor: 2 });
await p.goto('file://' + out + 'sheet.html'); await p.waitForTimeout(300);
await p.screenshot({ path: out + 'logo-concepts.png', fullPage: true }); await b.close();
console.log('wrote', out + 'logo-concepts.png');
