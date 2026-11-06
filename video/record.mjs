// Render the OODA-Aegis film frame by frame (see STORYBOARD.md and SCORE.md).
//   npm run build                                   (the dashboard the demo shots replay)
//   python3 -m http.server 8770 --bind 127.0.0.1    (from the repo root, in another shell)
//   PREVIEW=12,25,60 node video/record.mjs          -> stills in video/out/preview/
//   node video/record.mjs                           -> video/out/silent.mp4 + video/out/captions.srt
//   python3 video/music.py                          -> video/out/score.wav
//   ffmpeg -i video/out/silent.mp4 -i video/out/score.wav -c:v copy -c:a aac -b:a 192k -shortest video/out/ooda-aegis-demo.mp4
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';

const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const URL = process.env.URL || 'http://127.0.0.1:8770/video/scene.html';
const FPS = +(process.env.FPS || 30);
mkdirSync('video/out/preview', { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
page.on('pageerror', (e) => console.log('page exception:', e.message));
page.on('console', (m) => { if (m.type() === 'error') console.log('page error:', m.text()); });
await page.goto(URL);
await page.waitForFunction(() => window.READY === true, null, { timeout: 120000 });
const duration = await page.evaluate(() => window.DURATION);

if (process.env.PREVIEW) {
  for (const t of process.env.PREVIEW.split(',').map(Number)) {
    await page.evaluate((t) => window.renderAt(t), t);
    await page.screenshot({ path: `video/out/preview/t${t}.jpg`, type: 'jpeg', quality: 80 });
  }
  await browser.close();
  process.exit(0);
}

const caps = await page.evaluate(() => window.CAPTIONS);
const ts = (s) => { const ms = Math.round(s * 1000), h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, sec = Math.floor(ms / 1000) % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')},${String(ms % 1000).padStart(3, '0')}`; };
writeFileSync('video/out/captions.srt', caps.map(([a, b, html], i) => `${i + 1}\n${ts(a)} --> ${ts(b)}\n${html.replace(/<[^>]+>/g, '')}\n`).join('\n'));

const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', 'video/out/silent.mp4'], { stdio: ['pipe', 'inherit', 'inherit'] });
const frames = Math.round(duration * FPS), t0 = Date.now();
for (let f = 0; f < frames; f++) {
  await page.evaluate((t) => window.renderAt(t), f / FPS);
  const buf = await page.screenshot({ type: 'jpeg', quality: 93 });
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  if (f % 300 === 0) { const el = (Date.now() - t0) / 1000; console.log(`frame ${f}/${frames} ${el.toFixed(0)}s`); }
}
ff.stdin.end();
await new Promise((r) => ff.on('close', r));
await browser.close();
console.log('done video/out/silent.mp4');
