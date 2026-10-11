// Hand-authored doodle library for boootie.
// Every motif lives in a 100x100 box and is built from strokes (no fills except
// tiny eye dots), so each one can be drawn in with stroke-dashoffset and the
// line weight can be set per instance. Shapes are sampled to polylines, given a
// seeded hand wobble, and emitted as smooth paths.

// ---------- seeded noise ----------
function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hash(str) { let h = 2166136261; for (const c of str) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }

// ---------- primitives (all return stroke objects) ----------
const d2r = d => d * Math.PI / 180;
export const line = (x1, y1, x2, y2) => ({ pts: [[x1, y1], [x2, y2]] });
export const poly = (pts, closed = false, sharp = false) => ({ pts, closed, sharp });
export const circ = (cx, cy, r, a0 = 0, a1 = 360, n = 28) => {
  const pts = []; const full = (a1 - a0) >= 360;
  const steps = Math.max(8, Math.round(n * (a1 - a0) / 360));
  for (let i = 0; i <= steps; i++) { const a = d2r(a0 + (a1 - a0) * i / steps); pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); }
  if (full) pts.pop();
  return { pts, closed: full, smooth: true };
};
export const ellipse = (cx, cy, rx, ry, a0 = 0, a1 = 360, n = 32) => {
  const pts = []; const full = (a1 - a0) >= 360;
  const steps = Math.max(8, Math.round(n * (a1 - a0) / 360));
  for (let i = 0; i <= steps; i++) { const a = d2r(a0 + (a1 - a0) * i / steps); pts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]); }
  if (full) pts.pop();
  return { pts, closed: full, smooth: true };
};
export const rr = (x, y, w, h, r) => {
  r = Math.min(r, w / 2, h / 2);
  const pts = [];
  const corner = (cx, cy, a0) => { for (let i = 0; i <= 6; i++) { const a = d2r(a0 + 90 * i / 6); pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); } };
  corner(x + w - r, y + r, -90); corner(x + w - r, y + h - r, 0); corner(x + r, y + h - r, 90); corner(x + r, y + r, 180);
  return { pts, closed: true, smooth: true };
};
export const dot = (cx, cy, r = 3.4) => ({ dot: [cx, cy, r] });
export const ref = (id, x, y, s) => ({ ref: id, x, y, s });
export const smile = (cx, cy, r) => circ(cx, cy, r, 25, 155, 20);
export const eyes = (cx, cy, gap = 9) => [dot(cx - gap, cy), dot(cx + gap, cy)];
export const wave = (x0, y0, x1, y1, amp, periods, n = 40) => {
  const pts = []; const dx = x1 - x0, dy = y1 - y0, len = Math.hypot(dx, dy); const nx = -dy / len, ny = dx / len;
  for (let i = 0; i <= n; i++) { const t = i / n; const s = Math.sin(t * Math.PI * 2 * periods) * amp; pts.push([x0 + dx * t + nx * s, y0 + dy * t + ny * s]); }
  return { pts, smooth: true };
};
export const arrowhead = (x, y, dirDeg, size = 14, spread = 32) => [
  line(x, y, x - size * Math.cos(d2r(dirDeg - spread)), y - size * Math.sin(d2r(dirDeg - spread))),
  line(x, y, x - size * Math.cos(d2r(dirDeg + spread)), y - size * Math.sin(d2r(dirDeg + spread))),
];

// ---------- motifs ----------
export const motifs = {
  // --- system / characters ---
  phone: [rr(29, 5, 42, 90, 10), line(44, 13, 56, 13), line(44, 88, 56, 88), ...eyes(50, 42, 8), smile(50, 52, 9)],
  bubble: [rr(8, 16, 84, 54, 24), poly([[30, 69], [22, 92], [48, 70]]), dot(38, 43, 4), dot(50, 43, 4), dot(62, 43, 4)],
  'bubble-2': [rr(6, 10, 58, 40, 16), poly([[18, 49], [14, 64], [32, 50]]), rr(38, 46, 56, 40, 16), poly([[80, 85], [86, 96], [68, 86]]), line(18, 30, 52, 30), line(50, 66, 82, 66)],
  boot: [
    // ankle boot facing right: shaft, heel notch, rounded toe, double sole, face on the shaft, little legs
    poly([[28, 8], [58, 8], [60, 46], [68, 52], [84, 56], [93, 64], [93, 76], [22, 76], [22, 62], [28, 54]], true, true),
    line(26, 70, 90, 70), smile(44, 36, 6), ...eyes(44, 26, 8),
    line(40, 76, 36, 94), line(30, 94, 40, 94), line(74, 76, 78, 94), line(72, 94, 84, 94),
  ],
  'boot-walk': [
    poly([[28, 6], [58, 6], [60, 44], [68, 50], [84, 54], [93, 62], [93, 74], [22, 74], [22, 60], [28, 52]], true, true),
    line(26, 68, 90, 68), smile(44, 34, 6), ...eyes(44, 24, 8),
    line(40, 74, 26, 92), line(20, 94, 30, 92), line(74, 74, 86, 90), line(80, 92, 92, 90),
    line(6, 44, 16, 44), line(4, 54, 16, 54),
  ],
  'hand-point': [rr(22, 50, 56, 42, 14), rr(36, 6, 16, 52, 8), rr(54, 52, 22, 12, 6), rr(54, 65, 22, 12, 6), rr(54, 78, 22, 12, 6), poly([[22, 62], [10, 60], [12, 74], [24, 78]], false, false)],
  'hand-wave': [rr(28, 44, 46, 46, 16), rr(29, 12, 11, 38, 5), rr(42, 5, 11, 45, 5), rr(55, 8, 11, 42, 5), rr(68, 18, 11, 32, 5), poly([[28, 62], [12, 50], [16, 44]]), circ(16, 26, 10, 200, 320), circ(16, 26, 18, 210, 310)],
  'hand-tap': [rr(42, 32, 16, 60, 8), poly([[42, 72], [30, 64], [28, 90], [72, 90], [70, 64], [58, 72]]), circ(50, 28, 14, 200, 340), circ(50, 28, 24, 210, 330)],
  thumb: [rr(42, 46, 44, 44, 12), poly([[42, 50], [44, 24], [52, 12], [62, 16], [58, 46]]), rr(14, 46, 24, 44, 5), line(42, 60, 86, 60), line(42, 74, 86, 74)],
  sparkle: [poly([[50, 6], [58, 42], [94, 50], [58, 58], [50, 94], [42, 58], [6, 50], [42, 42]], true, true)],
  'sparkle-sm': [poly([[50, 20], [55, 45], [80, 50], [55, 55], [50, 80], [45, 55], [20, 50], [45, 45]], true, true)],
  star: [poly([[50, 8], [61, 38], [93, 38], [67, 57], [77, 88], [50, 70], [23, 88], [33, 57], [7, 38], [39, 38]], true, true), ...eyes(50, 52, 8), smile(50, 58, 6)],
  heart: (() => { const pts = []; for (let i = 0; i <= 40; i++) { const t = i / 40 * Math.PI * 2; const x = 16 * Math.pow(Math.sin(t), 3); const y = 13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t); pts.push([50 + x * 2.6, 48 - y * 2.6]); } pts.pop(); return [{ pts, closed: true, smooth: true }, ...eyes(50, 44, 9), smile(50, 52, 8)]; })(),
  app: [rr(12, 12, 76, 76, 18), ...eyes(50, 42, 12), smile(50, 54, 13)],
  cursor: [poly([[30, 12], [30, 76], [46, 62], [56, 90], [66, 86], [56, 60], [74, 58]], true, true)],
  bolt: [poly([[56, 4], [26, 54], [48, 54], [40, 96], [74, 42], [52, 42]], true, true)],
  bell: [circ(50, 50, 30, 180, 360), poly([[20, 50], [14, 76], [86, 76], [80, 50]], false, true), dot(50, 86, 6), circ(50, 16, 5)],
  mic: [rr(38, 8, 24, 48, 12), circ(50, 44, 22, 0, 180), line(50, 66, 50, 84), line(36, 84, 64, 84), line(28, 30, 10, 24), line(28, 42, 10, 46)],
  sun: [circ(50, 50, 22), ...[0, 45, 90, 135, 180, 225, 270, 315].map(a => line(50 + 30 * Math.cos(d2r(a)), 50 + 30 * Math.sin(d2r(a)), 50 + 42 * Math.cos(d2r(a)), 50 + 42 * Math.sin(d2r(a)))), ...eyes(50, 46, 8), smile(50, 52, 8)],
  coffee: [poly([[22, 36], [27, 88], [63, 88], [68, 36]], true, true), circ(70, 60, 12, -80, 80), wave(36, 28, 38, 8, 3, 1, 12), wave(52, 28, 54, 8, 3, 1, 12), ...eyes(45, 56, 8), smile(45, 66, 7)],
  clock: [circ(50, 50, 40), line(50, 50, 50, 24), line(50, 50, 68, 58), line(50, 12, 50, 18), line(50, 82, 50, 88), line(12, 50, 18, 50), line(82, 50, 88, 50)],
  // --- tasks: restaurant, chat, ride ---
  taxi: [poly([[8, 66], [10, 46], [28, 44], [38, 26], [68, 26], [80, 44], [92, 48], [92, 66]], false, true), line(8, 66, 92, 66), circ(28, 68, 10), circ(72, 68, 10), rr(42, 30, 22, 13, 3), rr(40, 10, 22, 10, 3), dot(16, 54, 3), dot(86, 56, 3)],
  car: [poly([[8, 66], [10, 46], [28, 44], [38, 26], [68, 26], [80, 44], [92, 48], [92, 66]], false, true), line(8, 66, 92, 66), circ(28, 68, 10), circ(72, 68, 10), line(40, 44, 66, 44), line(52, 28, 52, 44)],
  plate: [ellipse(50, 58, 30, 20), ellipse(50, 58, 17, 10), line(10, 44, 10, 90), line(5, 28, 5, 44), line(10, 26, 10, 44), line(15, 28, 15, 44), circ(10, 44, 5, 0, 180), line(90, 44, 90, 90), poly([[86, 22], [94, 20], [94, 44], [86, 44]], true, true)],
  fork: [line(50, 44, 50, 94), line(42, 10, 42, 40), line(50, 6, 50, 40), line(58, 10, 58, 40), circ(50, 40, 8, 0, 180)],
  pizza: [poly([[50, 92], [12, 22], [88, 22]], true, true), poly([[12, 22], [30, 11], [50, 7], [70, 11], [88, 22]], false, false), circ(50, 36, 7), circ(38, 52, 6), circ(60, 56, 6)],
  burger: [circ(50, 42, 36, 180, 360), line(14, 42, 86, 42), rr(12, 48, 76, 12, 6), rr(14, 64, 72, 16, 8), dot(36, 24, 2.5), dot(50, 18, 2.5), dot(64, 24, 2.5)],
  cocktail: [poly([[14, 16], [86, 16], [50, 58]], true, true), line(50, 58, 50, 86), line(30, 88, 70, 88), line(58, 30, 80, 6), circ(40, 36, 6)],
  noodles: [circ(50, 54, 36, 0, 180), line(14, 54, 86, 54), line(40, 12, 66, 54), line(52, 8, 74, 52), wave(22, 66, 78, 66, 4, 2, 20)],
  cupcake: [poly([[22, 54], [28, 90], [72, 90], [78, 54]], true, true), circ(50, 44, 30, 180, 360), line(20, 54, 80, 54), line(34, 60, 36, 86), line(64, 60, 62, 86), line(50, 14, 50, 4)],
  calendar: [rr(14, 20, 72, 70, 8), line(14, 38, 86, 38), line(32, 12, 32, 28), line(68, 12, 68, 28), circ(60, 66, 11), dot(36, 52, 3), dot(48, 52, 3), dot(36, 68, 3)],
  pin: [circ(50, 38, 28, 160, 380), poly([[26, 50], [50, 92], [74, 50]], false, true), ...eyes(50, 34, 9), smile(50, 42, 8)],
  ticket: [rr(8, 30, 84, 40, 8), line(60, 30, 60, 70), circ(60, 30, 6, 0, 180), circ(60, 70, 6, 180, 360), line(20, 44, 48, 44), line(20, 56, 40, 56)],
  key: [circ(30, 50, 16), circ(30, 50, 5), line(46, 50, 90, 50), line(78, 50, 78, 62), line(88, 50, 88, 60)],
  bag: [rr(18, 36, 64, 56, 8), circ(50, 36, 16, 180, 360), ...eyes(50, 60, 10), smile(50, 70, 8)],
  plane: [poly([[8, 42], [92, 12], [58, 90], [48, 56], [8, 42]], true, true), line(48, 56, 92, 12)],
  // --- the object section ---
  usbc: [rr(14, 36, 72, 28, 14), rr(24, 44, 52, 12, 6)],
  cable: [rr(4, 40, 22, 20, 10), wave(26, 50, 74, 50, 6, 1.5, 30), rr(74, 40, 22, 20, 10)],
  battery: [rr(8, 32, 74, 36, 8), rr(82, 42, 8, 16, 3), poly([[48, 36], [34, 52], [46, 52], [42, 64], [58, 46], [46, 46]], true, true)],
  pocket: [poly([[16, 10], [84, 10], [84, 55], [50, 92], [16, 55]], true, true), poly([[24, 18], [76, 18], [76, 51], [50, 82], [24, 51]], true, true)],
  ruler: [rr(8, 38, 84, 24, 4), ...[20, 32, 44, 56, 68, 80].map((x, i) => line(x, 38, x, i % 2 ? 46 : 52))],
  lock: [rr(22, 44, 56, 46, 8), circ(50, 44, 18, 180, 360), dot(50, 64, 5), line(50, 64, 50, 76)],
  check: [poly([[14, 52], [40, 80], [88, 22]], false, false)],
  chevron: [poly([[18, 36], [50, 68], [82, 36]], false, false)],
  refund: [circ(50, 50, 34, 30, 320), ...arrowhead(50 + 34 * Math.cos(d2r(320)), 50 + 34 * Math.sin(d2r(320)), 50, 13)],
  envelope: [rr(10, 24, 80, 52, 6), poly([[10, 26], [50, 58], [90, 26]], false, true)],
  'phone-boot': [rr(29, 5, 42, 90, 10), line(44, 13, 56, 13), line(44, 88, 56, 88), ref('boot-walk', 30, 30, 0.42), line(36, 76, 64, 76)],
  'phone-tap': [rr(29, 5, 42, 90, 10), line(44, 13, 56, 13), line(44, 88, 56, 88), rr(36, 24, 28, 10, 4), rr(36, 40, 28, 10, 4), rr(36, 56, 28, 10, 4), ref('hand-tap', 48, 44, 0.5)],
  tag: [poly([[14, 14], [56, 14], [90, 48], [48, 90], [14, 56]], true, true), circ(32, 32, 6)],
  coin: [circ(50, 50, 38), circ(50, 50, 28), line(44, 36, 44, 64), line(56, 36, 56, 64)],
  box: [poly([[12, 36], [50, 20], [88, 36], [50, 52]], true, true), line(12, 36, 12, 76), line(12, 76, 50, 92), line(50, 92, 88, 76), line(88, 76, 88, 36), line(50, 52, 50, 92), line(31, 28, 69, 44)],
  cloud: [poly([[20, 70], [12, 60], [18, 46], [32, 42], [38, 28], [56, 24], [68, 34], [82, 38], [90, 52], [84, 68], [70, 72]], true, false), line(20, 72, 72, 72)],
  note: [circ(34, 72, 12), circ(70, 64, 12), line(46, 72, 46, 18), line(82, 64, 82, 10), line(46, 18, 82, 10), line(46, 30, 82, 22)],
  smiley: [circ(50, 50, 36), ...eyes(50, 42, 12), smile(50, 52, 14)],
  // --- pointers and accents ---
  'arrow-curl': [poly([[8, 82], [18, 60], [34, 42], [52, 34], [68, 40], [68, 56], [52, 62], [40, 52], [46, 36], [62, 26], [78, 22], [92, 22]], false, false), ...arrowhead(92, 22, 0, 13)],
  'arrow-right': [poly([[8, 60], [40, 44], [70, 48], [90, 40]], false, false), ...arrowhead(90, 40, -20, 14)],
  'arrow-down': [poly([[48, 6], [56, 40], [46, 70], [52, 92]], false, false), ...arrowhead(52, 92, 80, 14)],
  'arrow-up-right': [poly([[12, 88], [40, 70], [56, 44], [86, 16]], false, false), ...arrowhead(86, 16, -45, 14)],
  circle: [ellipse(50, 50, 46, 38, -20, 380, 40)],
  underline: [wave(4, 50, 96, 50, 4, 2, 30)],
  'underline-wide': Object.assign([wave(2, 9, 98, 9, 2.8, 2, 36)], { box: [100, 18], wobble: 0.3, step: 4 }),
  'underline-wide-2': Object.assign([wave(2, 7, 98, 7, 2.6, 2, 36), wave(8, 15, 84, 15, 2.2, 1.5, 28)], { box: [100, 20], wobble: 0.3, step: 4 }),
  'underline-2': [wave(4, 46, 96, 46, 4, 2, 30), wave(10, 60, 80, 60, 3, 1.5, 24)],
  squiggle: [wave(6, 50, 94, 50, 14, 3, 48)],
  dots: [dot(24, 72, 5), dot(50, 50, 5), dot(76, 28, 5)],
  'dots-3': [dot(26, 50, 5), dot(50, 50, 5), dot(74, 50, 5)],
  'dash-3': [line(10, 30, 40, 30), line(20, 50, 56, 50), line(10, 70, 40, 70)],
  'wifi': [circ(50, 70, 14, 200, 340), circ(50, 70, 28, 205, 335), circ(50, 70, 42, 210, 330), dot(50, 72, 4)],
  'spiral': (() => { const pts = []; for (let i = 0; i <= 60; i++) { const t = i / 60; const a = t * Math.PI * 2 * 2.3; const r = 6 + 38 * t; pts.push([50 + r * Math.cos(a), 50 + r * Math.sin(a)]); } return [{ pts, smooth: true }]; })(),
};

// ---------- rendering ----------
function subdivide(pts, closed, step) {
  const out = []; const n = pts.length; const segs = closed ? n : n - 1;
  for (let i = 0; i < segs; i++) {
    const a = pts[i], b = pts[(i + 1) % n]; const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const k = Math.max(1, Math.round(len / step));
    for (let j = 0; j < k; j++) { const t = j / k; out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]); }
  }
  if (!closed) out.push(pts[n - 1]);
  return out;
}
function jitter(pts, rnd, amp) { return pts.map(([x, y]) => [x + (rnd() - 0.5) * 2 * amp, y + (rnd() - 0.5) * 2 * amp]); }
const f1 = v => (Math.round(v * 10) / 10).toString();
function catmullRomPath(pts, closed) {
  const n = pts.length; if (n < 2) return '';
  const p = i => pts[closed ? ((i % n) + n) % n : Math.min(Math.max(i, 0), n - 1)];
  let d = `M${f1(pts[0][0])} ${f1(pts[0][1])}`;
  const segs = closed ? n : n - 1;
  for (let i = 0; i < segs; i++) {
    const p0 = p(i - 1), p1 = p(i), p2 = p(i + 1), p3 = p(i + 2);
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += `C${f1(c1[0])} ${f1(c1[1])} ${f1(c2[0])} ${f1(c2[1])} ${f1(p2[0])} ${f1(p2[1])}`;
  }
  return d + (closed ? 'Z' : '');
}
function linePath(pts, closed) { return 'M' + pts.map(([x, y]) => `${f1(x)} ${f1(y)}`).join('L') + (closed ? 'Z' : ''); }

export function renderMotif(id, { wobble = 0.9, step = 7, seed = 0 } = {}) {
  const strokes = motifs[id]; if (!strokes) throw new Error('unknown motif ' + id);
  const rnd = mulberry32(hash(id) + seed);
  wobble = strokes.wobble ?? wobble; step = strokes.step ?? step;
  let out = '';
  const expand = (list, tx = 0, ty = 0, sc = 1) => list.flatMap(st => {
    if (st.ref) return expand(motifs[st.ref], tx + st.x * sc, ty + st.y * sc, sc * st.s);
    if (st.dot) return [{ dot: [tx + st.dot[0] * sc, ty + st.dot[1] * sc, st.dot[2] * sc] }];
    return [{ ...st, pts: st.pts.map(([x, y]) => [tx + x * sc, ty + y * sc]) }];
  });
  for (const s of expand(strokes)) {
    if (s.dot) { const [cx, cy, r] = s.dot; out += `<circle class="dd" cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}"/>`; continue; }
    const closed = !!s.closed;
    let pts = subdivide(s.pts, closed, step);
    pts = jitter(pts, rnd, wobble);
    const d = s.sharp ? linePath(pts, closed) : catmullRomPath(pts, closed);
    out += `<path d="${d}" pathLength="1"/>`;
  }
  return out;
}
export function box(id) { const b = motifs[id].box; return b ? b : [100, 100]; }
export function symbol(id, opts) { const [bw, bh] = box(id); return `<symbol id="d-${id}" viewBox="0 0 ${bw} ${bh}" overflow="visible">${renderMotif(id, opts)}</symbol>`; }
export function allSymbols(opts) { return Object.keys(motifs).map(id => symbol(id, opts)).join('\n'); }
export const motifIds = Object.keys(motifs);
