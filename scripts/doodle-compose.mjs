// Field composer: scatters doodle motifs on a jittered hex grid, honours
// keep-out rectangles, and lets a weight(x, y) callback shape density so a
// field can be dense all over or only hug an edge.
// Every placed motif is a <g> carrying the placement transform and a random
// draw-in delay (--d), wrapping a <use> that CSS can animate safely.
// Stroke width is compensated per instance so every doodle on the page has the
// same line weight in CSS pixels regardless of its size.

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const f1 = v => Math.round(v * 10) / 10;
const f2 = v => Math.round(v * 100) / 100;

function hitsKeepOut(cx, cy, r, keepOut) {
  for (const k of keepOut) {
    const pad = k.pad ?? 0;
    const x0 = k.x - pad, y0 = k.y - pad, x1 = k.x + k.w + pad, y1 = k.y + k.h + pad;
    const nx = Math.max(x0, Math.min(cx, x1)), ny = Math.max(y0, Math.min(cy, y1));
    if (Math.hypot(cx - nx, cy - ny) < r) return true;
  }
  return false;
}

export function placeRaw(id, { x, y, size, rot = 0, strokePx = 3, flip = false, cls = '', delay = null, bare = false }) {
  const sw = f1(strokePx * 100 / size);
  const t = `translate(${f1(x)} ${f1(y)}) rotate(${f1(rot)})${flip ? ' scale(-1 1)' : ''}`;
  const style = delay != null ? ` style="--d:${f2(delay)}s"` : '';
  const use = `<use href="#d-${id}" width="${f1(size)}" height="${f1(size)}" x="${f1(-size / 2)}" y="${f1(-size / 2)}" stroke-width="${sw}"`;
  if (bare) return `${use} class="dp fade" transform="${t}"${style}/>`;
  return `<g class="dp draw${cls ? ' ' + cls : ''}" transform="${t}"${style}>${use}/></g>`;
}

/** One motif placed by hand, e.g. an arrow pointing at the CTA. */
export const place = placeRaw;

/**
 * @param {object} o
 * @param {number} o.w field width in px
 * @param {number} o.h field height in px
 * @param {number} [o.cell=84] grid pitch in px
 * @param {number} [o.seed=1]
 * @param {string[]} o.ids motif ids to draw from (repeat an id to weight it)
 * @param {(x:number,y:number)=>number} [o.weight] 0..1 probability a cell is filled
 * @param {{x:number,y:number,w:number,h:number,pad?:number}[]} [o.keepOut]
 * @param {[number,number]} [o.scale=[0.85,1.15]] size multiplier range
 * @param {number} [o.rot=18] max rotation in degrees either way
 * @param {number} [o.strokePx=3] line weight in CSS px
 * @param {number} [o.overlap=0.82] how close two motifs may sit (1 = touching bounding circles)
 * @param {string[]} [o.fillerIds] small motifs for a second gap-filling pass
 * @param {number} [o.fillerProb=0.45]
 * @param {number} [o.maxDelay=1.4] draw-in stagger range in seconds
 */
export function composeField(o) {
  const { w, h, cell = 84, seed = 1, ids, weight = () => 1, keepOut = [], scale = [0.85, 1.15], rot = 18, strokePx = 3, overlap = 0.82, fillerIds = [], fillerProb = 0.45, maxDelay = 1.4 } = o;
  const rnd = mulberry32(seed);
  const pick = arr => arr[Math.floor(rnd() * arr.length)];
  const placed = [];
  const out = [];
  const tryPlace = (cx, cy, size, id, rdeg) => {
    const r = size * 0.5;
    if (cx + r < -4 || cy + r < -4 || cx - r > w + 4 || cy - r > h + 4) return false;
    if (hitsKeepOut(cx, cy, r * 0.9, keepOut)) return false;
    for (const p of placed) if (Math.hypot(p.x - cx, p.y - cy) < (p.r + r) * overlap) return false;
    placed.push({ x: cx, y: cy, r });
    out.push(placeRaw(id, { x: cx, y: cy, size, rot: rdeg, strokePx, delay: rnd() * maxDelay, bare: true }));
    return true;
  };
  const rowH = cell * 0.87;
  const rows = Math.ceil(h / rowH) + 2, cols = Math.ceil(w / cell) + 2;
  for (let ry = -1; ry < rows; ry++) {
    for (let cx0 = -1; cx0 < cols; cx0++) {
      const x = cx0 * cell + (ry % 2 ? cell / 2 : 0) + (rnd() - 0.5) * cell * 0.45;
      const y = ry * rowH + (rnd() - 0.5) * rowH * 0.4;
      if (rnd() > weight(x, y)) continue;
      const s = scale[0] + rnd() * (scale[1] - scale[0]);
      tryPlace(x, y, cell * 0.8 * s, pick(ids), (rnd() - 0.5) * 2 * rot);
    }
  }
  if (fillerIds.length) {
    for (let ry = -1; ry < rows * 2; ry++) {
      for (let cx0 = -1; cx0 < cols * 2; cx0++) {
        const x = cx0 * cell / 2 + cell / 4 + (rnd() - 0.5) * cell * 0.3;
        const y = ry * rowH / 2 + (rnd() - 0.5) * rowH * 0.3;
        if (rnd() > fillerProb * weight(x, y)) continue;
        tryPlace(x, y, cell * 0.32 * (0.8 + rnd() * 0.5), pick(fillerIds), (rnd() - 0.5) * 2 * rot);
      }
    }
  }
  return { uses: out.join('\n'), count: out.length };
}
