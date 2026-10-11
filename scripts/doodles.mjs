// Generates every doodle SVG the page includes, into src/doodles/.
// Run with `npm run doodles`. Deterministic: same seeds, same output.
import { symbol, motifIds } from './doodle-lib.mjs';
import { composeField, place } from './doodle-compose.mjs';
import { writeFileSync, mkdirSync } from 'fs';

const DIR = new URL('../src/doodles/', import.meta.url).pathname;
mkdirSync(DIR, { recursive: true });
const files = {};
const out = (name, svg) => { files[name] = svg; };

// Motif sets per section so each section's doodles illustrate its own job.
const heroIds = ['phone', 'phone-boot', 'phone-tap', 'bubble', 'bubble-2', 'boot-walk', 'boot', 'hand-point', 'hand-wave', 'hand-tap', 'sparkle', 'star', 'heart', 'app', 'cursor', 'bolt', 'bell', 'mic', 'sun', 'coffee', 'clock', 'taxi', 'plate', 'pizza', 'calendar', 'pin', 'cocktail', 'burger', 'plane', 'smiley', 'thumb', 'key', 'bag', 'spiral', 'wifi', 'usbc'];
const fillers = ['sparkle-sm', 'dots', 'dots-3', 'dash-3', 'squiggle', 'smiley', 'star', 'heart'];
const howIds = ['usbc', 'phone', 'mic', 'bubble', 'hand-tap', 'sparkle', 'cursor', 'check', 'phone-boot', 'wifi', 'hand-wave'];
const taskIds = ['plate', 'calendar', 'cocktail', 'pizza', 'bubble-2', 'heart', 'taxi', 'pin', 'key', 'clock', 'burger', 'noodles', 'thumb'];
const objectIds = ['usbc', 'cable', 'ruler', 'pocket', 'phone', 'sparkle', 'boot', 'spiral'];
const preorderIds = ['tag', 'coin', 'box', 'refund', 'check', 'calendar', 'plane', 'envelope', 'sparkle'];
const faqIds = ['bubble', 'bubble-2', 'lock', 'phone', 'usbc', 'refund', 'app', 'smiley'];

// ---------- hero fields ----------
{
  const m = composeField({ w: 390, h: 860, cell: 70, seed: 7, ids: heroIds, fillerIds: fillers, fillerProb: 0.35, strokePx: 3, scale: [0.85, 1.1], overlap: 0.78 });
  out('hero-field-m', `<svg class="field field-m doodle pending" viewBox="0 0 390 860" preserveAspectRatio="xMidYMin slice" aria-hidden="true" focusable="false">${m.uses}</svg>`);
  const d = composeField({ w: 1440, h: 900, cell: 80, seed: 9, ids: heroIds, fillerIds: fillers, fillerProb: 0.75, strokePx: 3.2, scale: [0.85, 1.1], overlap: 0.72 });
  out('hero-field-d', `<svg class="field field-d doodle pending" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">${d.uses}</svg>`);
}

// ---------- the ring behind the product (white cut-out + hand-drawn circle) ----------
out('halo', `<svg class="halo doodle" viewBox="0 0 400 320" aria-hidden="true" focusable="false">
<ellipse cx="200" cy="160" rx="188" ry="146" fill="#fff" transform="rotate(-6 200 160)"/>
${place('circle', { x: 200, y: 160, size: 396, rot: -6, strokePx: 3.2, cls: 'halo-line' })}
</svg>`);

// ---------- section bands: lighter borders ----------
const band = (name, ids, seed, prob = 0.42) => {
  const f = composeField({ w: 1440, h: 150, cell: 86, seed, ids, scale: [0.6, 0.95], strokePx: 2.8, overlap: 0.9,
    weight: (x, y) => (y < 20 || y > 130 ? 0 : prob), fillerIds: fillers, fillerProb: 0.3 });
  out(name, `<svg class="band doodle pending" viewBox="0 0 1440 150" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">${f.uses}</svg>`);
};
band('band-how', howIds, 21);
band('band-tasks', taskIds, 22);
band('band-object', objectIds, 23, 0.36);
band('band-preorder', preorderIds, 24);
band('band-faq', faqIds, 25, 0.36);

// ---------- scenes: hand-placed compositions ----------
const scene = (name, w, h, items, backdrop = false) => out(name, `<svg class="scene doodle pending" viewBox="0 0 ${w} ${h}" aria-hidden="true" focusable="false">${backdrop ? `<ellipse cx="${w / 2}" cy="${h / 2}" rx="${w / 2}" ry="${h / 2}" fill="#fff"/>` : ''}${items.join('\n')}</svg>`);
const P = (id, x, y, size, rot = 0, extra = {}) => place(id, { x, y, size, rot, strokePx: 3, ...extra });
let dly = 0; const D = () => (dly = (dly + 0.18) % 1.1);

scene('scene-plug', 240, 200, [
  P('phone', 120, 78, 130, -4, { delay: 0.1 }),
  P('usbc', 120, 168, 64, 0, { delay: 0.4 }),
  P('arrow-down', 172, 128, 40, 180, { delay: 0.7 }),
  P('sparkle-sm', 48, 48, 30, 10, { delay: 0.9 }),
  P('sparkle-sm', 196, 36, 24, -15, { delay: 1.0 }),
], true);
scene('scene-say', 240, 200, [
  P('mic', 86, 112, 120, -6, { delay: 0.1 }),
  P('bubble', 172, 62, 98, 6, { delay: 0.5 }),
  P('hand-wave', 190, 150, 66, 12, { delay: 0.8 }),
], true);
scene('scene-watch', 240, 200, [
  P('phone-tap', 120, 100, 150, 3, { delay: 0.1 }),
  P('sparkle', 46, 60, 44, 12, { delay: 0.5 }),
  P('check', 198, 150, 54, 0, { delay: 0.8 }),
  P('sparkle-sm', 206, 54, 26, -10, { delay: 1.0 }),
], true);

scene('scene-table', 320, 220, [
  P('plate', 150, 120, 150, -3, { delay: 0.1 }),
  P('calendar', 254, 70, 90, 8, { delay: 0.4 }),
  P('cocktail', 54, 60, 70, -10, { delay: 0.6 }),
  P('check', 268, 170, 48, 0, { delay: 0.9 }),
  P('sparkle-sm', 110, 36, 24, 0, { delay: 1.0 }),
]);
scene('scene-chat', 320, 220, [
  P('bubble-2', 150, 100, 170, -2, { delay: 0.1 }),
  P('heart', 262, 56, 56, 12, { delay: 0.5 }),
  P('thumb', 60, 170, 64, -8, { delay: 0.7 }),
  P('phone', 276, 160, 84, 8, { delay: 0.9 }),
]);
scene('scene-ride', 320, 220, [
  P('taxi', 150, 120, 180, 0, { delay: 0.1 }),
  P('pin', 262, 64, 70, 6, { delay: 0.5 }),
  P('key', 58, 70, 64, -12, { delay: 0.7 }),
  P('arrow-right', 250, 176, 70, 0, { delay: 0.9 }),
]);

// pointers and small accents used inline
out('pointer-cta', `<svg class="doodle pointer" viewBox="0 0 60 60" aria-hidden="true" focusable="false">${place('arrow-down', { x: 30, y: 30, size: 56, rot: 96, strokePx: 3, cls: 'nudge' })}</svg>`);
out('underline', `<svg class="doodle underline" viewBox="0 0 100 18" preserveAspectRatio="none" aria-hidden="true" focusable="false"><use href="#d-underline-wide" stroke-width="3"/></svg>`);
out('ruler', `<svg class="doodle" viewBox="0 0 100 100" aria-hidden="true" focusable="false">${place('ruler', { x: 50, y: 50, size: 96, rot: -4, strokePx: 3 })}</svg>`);
out('refund', `<svg class="doodle" viewBox="0 0 100 100" aria-hidden="true" focusable="false">${place('refund', { x: 50, y: 50, size: 92, rot: 0, strokePx: 3 })}</svg>`);
out('check', `<svg class="doodle" viewBox="0 0 100 100" aria-hidden="true" focusable="false">${place('check', { x: 50, y: 50, size: 92, rot: -4, strokePx: 3.2 })}</svg>`);
out('box', `<svg class="doodle" viewBox="0 0 100 100" aria-hidden="true" focusable="false">${place('box', { x: 50, y: 50, size: 92, rot: 0, strokePx: 3 })}</svg>`);
out('coin', `<svg class="doodle" viewBox="0 0 100 100" aria-hidden="true" focusable="false">${place('coin', { x: 50, y: 50, size: 92, rot: 0, strokePx: 3 })}</svg>`);
out('chevron', `<svg class="doodle chevron" viewBox="0 0 40 40" aria-hidden="true" focusable="false">${place('chevron', { x: 20, y: 20, size: 36, rot: 0, strokePx: 3 })}</svg>`);
out('boot-hero', `<svg class="doodle boot-hero" viewBox="0 0 100 100" aria-hidden="true" focusable="false">${place('boot-walk', { x: 50, y: 50, size: 92, rot: -6, strokePx: 3, cls: 'wobble' })}</svg>`);
out('scene-footer', `<svg class="scene doodle pending" viewBox="0 0 320 120" aria-hidden="true" focusable="false">
${place('dash-3', { x: 40, y: 64, size: 44, rot: 0, strokePx: 3, delay: 0.5 })}
${place('boot-walk', { x: 110, y: 62, size: 92, rot: -4, strokePx: 3, cls: 'wobble', delay: 0.1 })}
${place('dots-3', { x: 190, y: 72, size: 50, rot: 0, strokePx: 3, delay: 0.8 })}
${place('sparkle-sm', { x: 250, y: 40, size: 28, rot: 0, strokePx: 3, delay: 1.0 })}
${place('usbc', { x: 282, y: 76, size: 44, rot: -10, strokePx: 3, delay: 1.1 })}
</svg>`);

// dashed hand-drawn path behind the three "how it works" stops (desktop)
{
  const pts = []; for (let i = 0; i <= 40; i++) { const t = i / 40; pts.push([t * 1000, 30 + Math.sin(t * Math.PI * 3) * 14 + Math.sin(t * 37) * 2]); }
  const d = 'M' + pts.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join('L');
  out('step-path', `<svg class="step-path doodle" viewBox="0 0 1000 60" preserveAspectRatio="none" aria-hidden="true" focusable="false"><path class="line" d="${d}" stroke-dasharray="14 12"/></svg>`);
}

// label arrows for the object figures
out('arrow-label', `<svg class="doodle" viewBox="0 0 100 100" aria-hidden="true" focusable="false">${place('arrow-up-right', { x: 50, y: 50, size: 92, rot: 0, strokePx: 3 })}</svg>`);
out('arrow-label-flip', `<svg class="doodle" viewBox="0 0 100 100" aria-hidden="true" focusable="false">${place('arrow-up-right', { x: 50, y: 50, size: 92, rot: 0, strokePx: 3, flip: true })}</svg>`);

// ---------- symbol definitions: only the motifs actually used ----------
const used = new Set();
for (const svg of Object.values(files)) for (const m of svg.matchAll(/href="#d-([\w-]+)"/g)) used.add(m[1]);
const defs = [...used].filter(id => motifIds.includes(id)).sort().map(id => symbol(id)).join('\n');
out('symbols', `<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>${defs}</defs></svg>`);

for (const [name, svg] of Object.entries(files)) writeFileSync(DIR + name + '.svg', svg);
const total = Object.values(files).reduce((n, s) => n + s.length, 0);
console.log(`doodles: ${Object.keys(files).length} files, ${used.size} motifs, ${(total / 1024).toFixed(0)} KB raw`);
