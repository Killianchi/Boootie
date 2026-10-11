// Renders the product visuals from public/models/boootie.glb with three.js in
// headless Chromium:
//   stills     -> public/img/*.webp   (poster, fig-edge, fig-port, phone still)
//   sequences  -> renders/<name>/frame-000.png  (turntable, plug-in loop)
// Run `npm run renders` (stills + sequences) then `npm run encode` to turn the
// sequences into mp4 / webm / gif / poster. Results are committed so the Vercel
// build stays light.
import { chromium } from 'playwright';
import { createServer } from 'http';
import { readFile, writeFile, mkdir } from 'fs/promises';
import { extname } from 'path';
import sharp from 'sharp';

const root = new URL('../', import.meta.url).pathname;
const IMG = root + 'public/img/';
const SEQ = root + 'renders/';
await mkdir(IMG, { recursive: true });

const page_html = `<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#fff;width:100%;height:100%;overflow:hidden}html.t,html.t body{background:transparent}canvas{display:block}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"}}</script>
</head><body><script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
const q = new URLSearchParams(location.search);
if (q.get('bg') === 'transparent') document.documentElement.classList.add('t');
const W = +q.get('w') || 1600, H = +q.get('h') || 1200;
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, alpha: true });
renderer.setSize(W, H); renderer.setPixelRatio(1);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = +q.get('exp') || 0.85;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
if (q.get('bg') !== 'transparent') scene.background = new THREE.Color(0xffffff);
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = +q.get('env') || 0.55;
const cam = new THREE.PerspectiveCamera(+q.get('fov') || 22, W / H, 0.001, 10);
const [tx, ty, tz] = (q.get('target') || '0,0.004,0').split(',').map(Number);
const yaw = (+q.get('yaw') || 35) * Math.PI / 180, pitch = (+q.get('pitch') || 25) * Math.PI / 180, dist = +q.get('dist') || 0.082;
cam.position.set(tx + dist * Math.cos(pitch) * Math.sin(yaw), ty + dist * Math.sin(pitch), tz + dist * Math.cos(pitch) * Math.cos(yaw));
cam.lookAt(tx, ty, tz);
const key = new THREE.DirectionalLight(0xffffff, +q.get('key') || 3.0); key.position.set(0.05, 0.12, 0.08); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); const sc = +q.get('shadow') || 0.05;
key.shadow.camera.left = -sc; key.shadow.camera.right = sc; key.shadow.camera.top = sc; key.shadow.camera.bottom = -sc; key.shadow.camera.near = 0.01; key.shadow.camera.far = 0.6; key.shadow.radius = 6; key.shadow.bias = -0.0002;
scene.add(key);
const fill = new THREE.DirectionalLight(0xffffff, 0.8); fill.position.set(-0.1, 0.05, -0.05); scene.add(fill);
const rim = new THREE.DirectionalLight(0xffffff, 1.2); rim.position.set(0, 0.05, -0.15); scene.add(rim);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShadowMaterial({ opacity: +q.get('shadowOpacity') || 0.22 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = +q.get('floor') || 0; floor.receiveShadow = true; scene.add(floor);

function phoneScreenTexture() {
  // a plain monochrome messaging app drawn on a canvas: a group chat with a reply being typed
  const c = document.createElement('canvas'); c.width = 1170; c.height = 2532; const g = c.getContext('2d');
  g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height);
  g.fillStyle = '#000'; g.font = '700 60px Helvetica, Arial, sans-serif'; g.textBaseline = 'middle';
  g.fillText('9:41', 110, 95);
  for (let i = 0; i < 4; i++) g.fillRect(880 + i * 22, 110 - i * 10 - 30, 14, 30 + i * 10);
  g.strokeStyle = '#000'; g.lineWidth = 6; g.strokeRect(990, 70, 80, 40); g.fillRect(1000, 80, 46, 20); g.fillRect(1072, 82, 8, 16);
  // dynamic island
  g.fillStyle = '#000'; g.beginPath(); g.roundRect(585 - 190, 58, 380, 112, 56); g.fill();
  // header
  g.fillStyle = '#ededed'; g.fillRect(0, 200, c.width, 190);
  g.fillStyle = '#000'; g.font = '700 64px Helvetica, Arial, sans-serif'; g.textAlign = 'center'; g.fillText('Family', 585, 282);
  g.font = '500 40px Helvetica, Arial, sans-serif'; g.fillStyle = '#555'; g.fillText('5 people', 585, 338);
  g.textAlign = 'left'; g.strokeStyle = '#000'; g.lineWidth = 10; g.lineCap = 'round'; g.beginPath(); g.moveTo(110, 250); g.lineTo(70, 282); g.lineTo(110, 314); g.stroke();
  const bubble = (y, mine, lines) => {
    g.font = '500 46px Helvetica, Arial, sans-serif';
    const w = Math.max(...lines.map(l => g.measureText(l).width)) + 80, h = lines.length * 62 + 44;
    const x = mine ? c.width - 60 - w : 60;
    g.fillStyle = mine ? '#000' : '#ececec'; g.beginPath(); g.roundRect(x, y, w, h, 40); g.fill();
    g.fillStyle = mine ? '#fff' : '#000';
    lines.forEach((l, i) => g.fillText(l, x + 40, y + 52 + i * 62));
    return y + h + 28;
  };
  let y = 450;
  y = bubble(y, false, ['Dinner at ours on Friday?']);
  y = bubble(y, false, ['Around 7. Bring anyone.']);
  y = bubble(y, true, ['Sounds good']);
  y = bubble(y, false, ['Can someone bring dessert?']);
  y = bubble(y, false, ['Also, parking is tight,', 'come by train if you can']);
  g.fillStyle = '#ededed'; g.fillRect(0, c.height - 300, c.width, 300);
  g.fillStyle = '#fff'; g.beginPath(); g.roundRect(60, c.height - 250, 900, 120, 60); g.fill();
  g.strokeStyle = '#bbb'; g.lineWidth = 4; g.stroke();
  g.fillStyle = '#000'; g.font = '500 46px Helvetica, Arial, sans-serif'; g.fillText("On our way. We'll bring dessert", 110, c.height - 190);
  g.fillRect(110 + g.measureText("On our way. We'll bring dessert").width + 10, c.height - 222, 5, 64);
  g.beginPath(); g.arc(1050, c.height - 190, 58, 0, Math.PI * 2); g.fill();
  g.strokeStyle = '#fff'; g.lineWidth = 10; g.beginPath(); g.moveTo(1050, c.height - 160); g.lineTo(1050, c.height - 222); g.moveTo(1022, c.height - 196); g.lineTo(1050, c.height - 224); g.lineTo(1078, c.height - 196); g.stroke();
  g.fillStyle = '#000'; g.beginPath(); g.roundRect(435, c.height - 40, 300, 14, 7); g.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

// an iPhone-like body: 71.6 x 146.7 x 8.75 mm, flat frame, dark finish, no logo
function makePhone() {
  const body = new THREE.Mesh(new RoundedBoxGeometry(0.0716, 0.1467, 0.00875, 5, 0.0105), new THREE.MeshStandardMaterial({ color: 0x3a3a3d, roughness: 0.38, metalness: 0.5 }));
  body.castShadow = true; body.receiveShadow = true;
  const shape = new THREE.Shape(); const sw = 0.0666, sh = 0.1417, r = 0.0095;
  shape.moveTo(-sw / 2 + r, -sh / 2); shape.lineTo(sw / 2 - r, -sh / 2); shape.quadraticCurveTo(sw / 2, -sh / 2, sw / 2, -sh / 2 + r);
  shape.lineTo(sw / 2, sh / 2 - r); shape.quadraticCurveTo(sw / 2, sh / 2, sw / 2 - r, sh / 2); shape.lineTo(-sw / 2 + r, sh / 2);
  shape.quadraticCurveTo(-sw / 2, sh / 2, -sw / 2, sh / 2 - r); shape.lineTo(-sw / 2, -sh / 2 + r); shape.quadraticCurveTo(-sw / 2, -sh / 2, -sw / 2 + r, -sh / 2);
  const sg = new THREE.ShapeGeometry(shape, 12);
  const tex = phoneScreenTexture(); tex.repeat.set(1 / sw, 1 / sh); tex.offset.set(0.5, 0.5);
  const screen = new THREE.Mesh(sg, new THREE.MeshBasicMaterial({ map: tex })); screen.position.z = 0.00875 / 2 + 0.00005;
  const glass = new THREE.Mesh(sg, new THREE.MeshPhysicalMaterial({ color: 0xffffff, transparent: true, opacity: 0.07, roughness: 0.04, metalness: 0, clearcoat: 1 })); glass.position.z = 0.00875 / 2 + 0.0001;
  const phone = new THREE.Group(); phone.add(body, screen, glass); return phone;
}

const ease = t => 1 - Math.pow(1 - t, 3);
const easeIO = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

new GLTFLoader().load('/models/boootie.glb', g => {
  g.scene.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  const scn = q.get('scene') || 'product';
  const all = new THREE.Group();
  const docked = { y: -0.074 - 0.011, z: 0.00875 / 2 - 0.00875 };
  if (scn === 'phone') {
    g.scene.rotation.x = Math.PI / 2;            // plug points up into the phone, top face flush with the screen
    g.scene.position.set(0, docked.y, docked.z);
    all.add(makePhone(), g.scene);
    all.position.y = 0.096;
  } else {
    all.add(g.scene);
  }
  const roll = (+q.get('roll') || 0) * Math.PI / 180;
  all.rotation.y = roll;
  scene.add(all);
  // frame i of n for a sequence
  window.__frame = (i, n, seq) => {
    const t = i / n;
    if (seq === 'turntable') {
      all.rotation.y = roll + t * Math.PI * 2;
    } else if (seq === 'plugin') {
      // approach, dock and hold, pull back, short rest: one seamless loop
      let d;
      if (t < 0.32) d = 1 - ease(t / 0.32);
      else if (t < 0.68) d = 0;
      else if (t < 0.9) d = easeIO((t - 0.68) / 0.22);
      else d = 1;
      g.scene.position.y = docked.y - d * 0.034;
    }
    renderer.render(scene, cam);
    return true;
  };
  renderer.render(scene, cam);
  requestAnimationFrame(() => { renderer.render(scene, cam); window.__done = true; });
}, undefined, e => { window.__err = String(e); });
</script></body></html>`;

const types = { '.html': 'text/html', '.glb': 'model/gltf-binary' };
const srv = createServer(async (req, res) => {
  const p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/' || p === '/render.html') { res.writeHead(200, { 'content-type': 'text/html' }); return res.end(page_html); }
  try { const b = await readFile(root + 'public' + p); res.writeHead(200, { 'content-type': types[extname(p)] || 'application/octet-stream' }); res.end(b); }
  catch { res.writeHead(404); res.end(); }
});
await new Promise(r => srv.listen(0, r)); const port = srv.address().port;

const stills = {
  poster: { w: 1600, h: 1200, yaw: 32, pitch: 24, dist: 0.1, fov: 20, bg: 'transparent' },
  'fig-edge': { w: 1600, h: 1200, yaw: 90, pitch: 4, dist: 0.092, fov: 18, target: '0,0.004,-0.002' },
  'fig-port': { w: 1600, h: 1200, yaw: 24, pitch: 14, dist: 0.056, fov: 20, target: '0,0.006,0.008' },
  'fig-phone': { w: 1600, h: 1200, yaw: 24, pitch: 12, dist: 0.3, fov: 24, target: '0,0.052,0', scene: 'phone', shadow: 0.2, floor: 0, exp: 0.9, shadowOpacity: 0.12 },
};
const sequences = {
  turntable: { w: 1200, h: 900, yaw: 0, pitch: 26, dist: 0.1, fov: 20, frames: 240, roll: 32 },
  plugin: { w: 1200, h: 900, yaw: 24, pitch: 12, dist: 0.3, fov: 24, target: '0,0.045,0', scene: 'phone', shadow: 0.2, floor: 0, exp: 0.9, shadowOpacity: 0.12, frames: 72 },
};
const only = process.argv.slice(2);
const want = n => !only.length || only.includes(n);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const open = async (s) => {
  const page = await browser.newPage({ viewport: { width: s.w, height: s.h } });
  page.on('console', m => { if (m.type() === 'error') console.log('console:', m.text()); });
  await page.goto(`http://127.0.0.1:${port}/render.html?${new URLSearchParams(s)}`);
  await page.waitForFunction(() => window.__done || window.__err, null, { timeout: 90000 });
  const err = await page.evaluate(() => window.__err); if (err) console.log('ERR', err);
  return page;
};
for (const [name, s] of Object.entries(stills)) {
  if (!want(name)) continue;
  const page = await open(s);
  const png = await page.screenshot({ omitBackground: s.bg === 'transparent' });
  await page.close();
  await writeFile(IMG + name + '.webp', await sharp(png).resize(1200, 900, { fit: 'inside' }).webp({ quality: 86, alphaQuality: 90, effort: 5 }).toBuffer());
  console.log('wrote', name + '.webp');
}
for (const [name, s] of Object.entries(sequences)) {
  if (!want(name)) continue;
  const dir = `${SEQ}${name}/`; await mkdir(dir, { recursive: true });
  const page = await open(s);
  for (let i = 0; i < s.frames; i++) {
    await page.evaluate(([i, n, seq]) => window.__frame(i, n, seq), [i, s.frames, name]);
    await writeFile(`${dir}frame-${String(i).padStart(3, '0')}.png`, await page.screenshot());
  }
  await page.close();
  console.log('wrote', s.frames, 'frames for', name);
}
await browser.close(); srv.close();
