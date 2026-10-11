// Encodes renders/<name>/frame-*.png into public/img/<name>.mp4 (H.264),
// <name>.webm (VP9), <name>-poster.webp, and exports/<name>.gif for sharing.
// Usage: node scripts/encode.mjs [turntable] [plugin]
import { execFileSync } from 'child_process';
import { existsSync, mkdirSync, statSync } from 'fs';
import sharp from 'sharp';

const root = new URL('../', import.meta.url).pathname;
let ffmpeg;
try { ffmpeg = (await import('@ffmpeg-installer/ffmpeg')).default.path; } catch { ffmpeg = '/opt/pw-browsers/ffmpeg-1011/ffmpeg-linux'; }
const run = (args) => execFileSync(ffmpeg, ['-hide_banner', '-loglevel', 'error', '-y', ...args], { stdio: 'inherit' });
const kb = f => (statSync(f).size / 1024).toFixed(0) + ' KB';

const names = process.argv.slice(2).length ? process.argv.slice(2) : ['turntable', 'plugin'];
mkdirSync(root + 'exports', { recursive: true });
for (const name of names) {
  const frames = `${root}renders/${name}/frame-%03d.png`;
  if (!existsSync(`${root}renders/${name}/frame-000.png`)) { console.log('no frames for', name); continue; }
  const fps = 24;
  const mp4 = `${root}public/img/${name}.mp4`, webm = `${root}public/img/${name}.webm`, gif = `${root}exports/${name}.gif`;
  run(['-framerate', String(fps), '-i', frames, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '23', '-preset', 'slow', '-movflags', '+faststart', '-vf', 'scale=1200:-2', mp4]);
  run(['-framerate', String(fps), '-i', frames, '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '34', '-row-mt', '1', '-pix_fmt', 'yuv420p', '-vf', 'scale=1200:-2', webm]);
  // a sharable GIF: 720 px wide, palette tuned to the frames
  run(['-framerate', String(fps), '-i', frames, '-vf', 'fps=18,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a', '-loop', '0', gif]);
  await sharp(`${root}renders/${name}/frame-000.png`).resize(1200, 900, { fit: 'inside' }).webp({ quality: 84 }).toFile(`${root}public/img/${name}-poster.webp`);
  console.log(`${name}: mp4 ${kb(mp4)}, webm ${kb(webm)}, gif ${kb(gif)}`);
}
