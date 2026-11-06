// OODA-Aegis film. Every frame is a pure function of time t: window.renderAt(t).
// Shots follow STORYBOARD.md, characters follow CHARACTERS.md, the score's bar grid is 96 BPM (one bar = 2.5 s).
const C = { night: "#1D1015", hill: "#421B29", sky: "#702B40", rose: "#A64C61", lamp: "#D28B96", moon: "#F1DDE0" };
const W = 1920, H = 1080, BAR = 2.5, BEAT = BAR / 4;
const cv = document.getElementById("c");
const ctx = cv.getContext("2d");
const capEl = document.getElementById("cap");
await Promise.all(["600 40px Cinzel", "700 40px Cinzel", "italic 500 40px 'Cormorant Garamond'", "40px 'Share Tech Mono'", "500 40px 'JetBrains Mono'"].map((f) => document.fonts.load(f, "OODA-Aegis 0123 ../")));

// ------------------------------------------------------------------ helpers
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (u, a, b) => clamp((u - a) / (b - a));
const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const easeOut = (x) => 1 - Math.pow(1 - x, 3);
const smooth = (x) => x * x * (3 - 2 * x);
const lerp = (a, b, k) => a + (b - a) * k;
const D = Math.PI / 180;
function rand(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

function camera(c, depth = 1) {
  const x = 960 + (c.x - 960) * depth, y = 540 + (c.y - 540) * depth, z = 1 + (c.z - 1) * depth;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.translate(W / 2, H / 2);
  ctx.rotate(c.r || 0);
  ctx.scale(z, z);
  ctx.translate(-x, -y);
}
const screen = () => ctx.setTransform(1, 0, 0, 1, 0, 0);
function fill(col) { screen(); ctx.fillStyle = col; ctx.fillRect(0, 0, W, H); }
function text(str, x, y, { size = 40, color = C.moon, align = "left", font = "display" } = {}) {
  const fam = { display: "600 {s}px Cinzel", story: "italic 500 {s}px 'Cormorant Garamond'", mono: "500 {s}px 'JetBrains Mono'", tech: "{s}px 'Share Tech Mono'" }[font];
  ctx.font = fam.replace("{s}", size);
  ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = "alphabetic";
  ctx.fillText(str, x, y);
}
function poly(pts, col) { ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]); for (const p of pts.slice(1)) ctx.lineTo(p[0], p[1]); ctx.closePath(); ctx.fillStyle = col; ctx.fill(); }
function circle(x, y, r, col) { ctx.beginPath(); ctx.arc(x, y, Math.max(0.1, r), 0, Math.PI * 2); ctx.fillStyle = col; ctx.fill(); }
function rect(x, y, w, h, col) { ctx.fillStyle = col; ctx.fillRect(x, y, w, h); }
function ring(x, y, r, col, w) { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.strokeStyle = col; ctx.lineWidth = w; ctx.stroke(); }
function line(pts, col, w) { ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]); for (const p of pts.slice(1)) ctx.lineTo(p[0], p[1]); ctx.strokeStyle = col; ctx.lineWidth = w; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.stroke(); }

// ------------------------------------------------------------------ world pieces
function building(x, base, w, h, col, tiers = 1, win = null, seed = 1) {
  const r = rand(seed);
  rect(x, base - h, w, h, col);
  let y = base - h;
  for (let i = 0; i < tiers; i++) {
    const ww = w * (1 - i * 0.22), xx = x + (w - ww) / 2, rh = 22 + ww * 0.08;
    ctx.beginPath();
    ctx.moveTo(xx - 26, y);
    ctx.quadraticCurveTo(xx + ww * 0.12, y - rh * 0.25, xx + ww * 0.18, y - rh);
    ctx.lineTo(xx + ww * 0.82, y - rh);
    ctx.quadraticCurveTo(xx + ww * 0.88, y - rh * 0.25, xx + ww + 26, y);
    ctx.closePath();
    ctx.fillStyle = col; ctx.fill();
    if (i < tiers - 1) { rect(xx + ww * 0.2, y - rh - 46, ww * 0.6, 46, col); y = y - rh - 46; } else y = y - rh;
  }
  if (win) for (let k = 0; k < Math.floor(w / 38); k++) for (let j = 0; j < Math.floor(h / 60); j++) if (r() < 0.32) rect(x + 14 + k * 38, base - h + 18 + j * 60, 12, 18, win);
}
const SKY = (() => {
  const r = rand(11), far = [], town = [];
  for (let x = -1400; x < 4200; x += 120 + r() * 160) far.push([x, 210 + r() * 220, 180 + r() * 260]);
  for (let x = -1400; x < 4400; x += 90 + r() * 70) town.push([x, 70 + r() * 70, 80 + r() * 170, r() < 0.3 ? 2 : 1, Math.floor(r() * 1000)]);
  return { far, town };
})();
function mountains(c, base = 760) {
  camera(c, 0.25);
  ctx.beginPath(); ctx.moveTo(-2000, H + 400);
  for (const [x, h, w] of SKY.far) { ctx.lineTo(x, base - 40); ctx.lineTo(x + w * 0.5, base - 40 - h); ctx.lineTo(x + w, base - 40); }
  ctx.lineTo(5000, H + 400); ctx.closePath(); ctx.fillStyle = C.hill; ctx.fill();
}
function town(c, base = 820) {
  camera(c, 0.55);
  rect(-2000, base, 7000, 800, C.night);
  for (const [x, w, h, tiers, s] of SKY.town) building(x, base - 1, w, h, C.hill, tiers, C.lamp, s);
}
function clouds(c, t) {
  camera(c, 0.12);
  for (const [x0, y, s] of [[300, 260, 1], [1250, 380, 0.8], [2100, 230, 1.2]]) {
    const x = x0 + t * 9;
    ctx.beginPath();
    ctx.ellipse(x, y, 160 * s, 26 * s, 0, 0, Math.PI * 2);
    ctx.ellipse(x + 90 * s, y - 18 * s, 90 * s, 24 * s, 0, 0, Math.PI * 2);
    ctx.fillStyle = C.rose; ctx.fill();
  }
}
function night(c, t, { moonX = 1380, moonY = 300, moonR = 150 } = {}) {
  fill(C.sky);
  camera(c, 0.08);
  circle(moonX, moonY, moonR, C.moon);
  clouds(c, t);
  town(c);
}
function fortress(x, base, opts = {}) {
  const { open = 0, lock = null, seal = 0, label = true } = opts;
  rect(x - 330, base - 260, 660, 260, C.hill);
  building(x - 250, base - 260, 500, 170, C.hill, 3, C.lamp, 77);
  for (const dx of [-330, 250]) building(x + dx, base, 80, 330, C.hill, 1, null, 3);
  const gw = 200, gh = 190, gx = x - gw / 2, gy = base - gh;
  rect(gx - 14, gy - 14, gw + 28, gh + 14, C.rose);
  rect(gx, gy, gw, gh, C.night);
  const o = (gw / 2) * open;
  rect(gx - o, gy, gw / 2, gh, C.hill);
  rect(gx + gw / 2 + o, gy, gw / 2, gh, C.hill);
  rect(gx + gw / 2 - 2 - o, gy, 4, gh, C.night);
  if (label) { rect(x - 100, gy - 72, 200, 46, C.hill); text("DocVault", x, gy - 38, { size: 26, align: "center" }); }
  if (lock) padlock(x, gy + 100, 1, lock === "new" ? C.moon : C.rose);
  if (seal > 0) talisman(x + 52, gy + 30, seal);
}
function padlock(x, y, s, col, broken = 0) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  ctx.beginPath(); ctx.arc(0, -18 - broken * 30, 16, Math.PI, 0); ctx.strokeStyle = col; ctx.lineWidth = 8; ctx.stroke();
  rect(-24, -18, 48, 40, col);
  circle(0, 0, 5, C.night);
  ctx.restore();
}
function talisman(x, y, k) {
  ctx.save(); ctx.translate(x, y); const s = easeOut(clamp(k)); ctx.scale(s, s);
  rect(-26, 0, 52, 120, C.moon);
  rect(-14, 16, 28, 6, C.rose); rect(-4, 30, 8, 60, C.rose); rect(-16, 56, 32, 6, C.rose); rect(-12, 100, 24, 6, C.rose);
  ctx.restore();
}
function scroll(x, y, w, label, col = C.moon, ink = C.night, size = 22) {
  rect(x - w / 2, y - size, w, size * 1.7, col);
  rect(x - w / 2 - 8, y - size - 4, 8, size * 1.7 + 8, C.rose);
  rect(x + w / 2, y - size - 4, 8, size * 1.7 + 8, C.rose);
  if (label) text(label, x, y + size * 0.15, { size, font: "mono", color: ink, align: "center" });
}
function burst(x, y, k, col = C.moon, n = 10, r0 = 20, r1 = 90) {
  if (k <= 0 || k >= 1) return;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2 + 0.3;
    const a0 = lerp(r0, r1, easeOut(k)), a1 = a0 + 30 * (1 - k);
    line([[x + Math.cos(a) * a0, y + Math.sin(a) * a0], [x + Math.cos(a) * a1, y + Math.sin(a) * a1]], col, 5 * (1 - k) + 1);
  }
}

// ------------------------------------------------------------------ the character rig (CHARACTERS.md)
const JOINTS = ["lean", "chest", "head", "sh1", "el1", "sh2", "el2", "hip1", "kn1", "an1", "hip2", "kn2", "an2"];
const STAND = { lean: 2, chest: 1, head: 0, sh1: 8, el1: 16, sh2: -8, el2: 14, hip1: 5, kn1: 6, an1: 0, hip2: -5, kn2: 4, an2: 0 };
const P = (o) => ({ ...STAND, ...o });
const POSES = {
  stand: STAND,
  breathe: P({ chest: 3, head: -2, sh1: 10, sh2: -6 }),
  crouch: P({ lean: 46, chest: 10, head: -30, sh1: 40, el1: 50, sh2: -30, el2: 40, hip1: 92, kn1: 140, an1: 40, hip2: 30, kn2: 132, an2: 50 }),
  anticip: P({ lean: 34, chest: 6, head: -18, sh1: -60, el1: 30, sh2: -70, el2: 30, hip1: 70, kn1: 110, an1: 30, hip2: 40, kn2: 100, an2: 30 }),
  takeoff: P({ lean: 22, chest: -4, head: -6, sh1: 150, el1: 10, sh2: 120, el2: 16, hip1: 20, kn1: 10, an1: -40, hip2: -30, kn2: 30, an2: -40 }),
  tuck: P({ lean: 40, chest: 12, head: -24, sh1: 60, el1: 70, sh2: 40, el2: 70, hip1: 110, kn1: 140, an1: 20, hip2: 80, kn2: 140, an2: 20 }),
  reach: P({ lean: 14, chest: 0, head: -4, sh1: 70, el1: 10, sh2: -40, el2: 20, hip1: 60, kn1: 40, an1: 0, hip2: -10, kn2: 50, an2: 10 }),
  raise: P({ lean: -4, chest: -6, head: -14, sh1: 168, el1: 8, sh2: -14, el2: 18 }),
  look: P({ lean: 10, chest: 4, head: 12, sh1: 20, el1: 50, sh2: -10, el2: 50 }),
  windup: P({ lean: -10, chest: -8, head: 0, sh1: -80, el1: 60, sh2: 30, el2: 30, hip1: 30, kn1: 30, hip2: -20, kn2: 10 }),
  push: P({ lean: 22, chest: 6, head: -4, sh1: 92, el1: 0, sh2: -40, el2: 30, hip1: 50, kn1: 46, an1: 10, hip2: -36, kn2: 8, an2: -10 }),
  lunge: P({ lean: 30, chest: 8, head: -8, sh1: 96, el1: 0, sh2: -64, el2: 10, hip1: 70, kn1: 70, an1: 10, hip2: -44, kn2: 4, an2: -20 }),
  hurt: P({ lean: -28, chest: -14, head: 26, sh1: -60, el1: 40, sh2: 70, el2: 50, hip1: -16, kn1: 30, hip2: 26, kn2: 60 }),
  hammerUp: P({ lean: -2, chest: -10, head: -6, sh1: 176, el1: 40, sh2: 30, el2: 60, hip1: 22, kn1: 18, hip2: -18, kn2: 8 }),
  hammerDown: P({ lean: 32, chest: 12, head: 14, sh1: 66, el1: 4, sh2: 40, el2: 50, hip1: 28, kn1: 32, hip2: -22, kn2: 12 }),
  pullUp: P({ lean: -6, chest: -10, head: -22, sh1: 172, el1: 0, sh2: 160, el2: 10 }),
  pullDown: P({ lean: 10, chest: 6, head: -8, sh1: 120, el1: 50, sh2: 110, el2: 60, hip1: 40, kn1: 60, hip2: 10, kn2: 50 }),
  bow: P({ lean: 18, chest: 12, head: 22, sh1: 0, el1: 10, sh2: 0, el2: 10 }),
};
function blend(a, b, k) { const o = {}; for (const j of JOINTS) o[j] = lerp(a[j] ?? STAND[j], b[j] ?? STAND[j], k); return o; }
// A clip is a list of [time, pose], sampled with smooth easing between keys.
function clip(keys, u) {
  if (u <= keys[0][0]) return keys[0][1];
  for (let i = 0; i < keys.length - 1; i++) {
    const [a, pa] = keys[i], [b, pb] = keys[i + 1];
    if (u <= b) return blend(pa, pb, smooth((u - a) / (b - a)));
  }
  return keys[keys.length - 1][1];
}
const idle = (t, k = 0) => blend(STAND, POSES.breathe, 0.5 - 0.5 * Math.cos((t + k) * Math.PI / (2 * BEAT)));
// Run: the swing knee bends most at the passing pose; arms pump against the legs.
function run(ph) {
  const leg = (p) => { const s = Math.sin(p), c = Math.cos(p); return { hip: 14 + 56 * s, kn: 18 + 96 * Math.pow(Math.max(0, c), 1.4) + 20 * Math.max(0, -s), an: 10 + 30 * Math.max(0, -c) }; };
  const a = leg(ph), b = leg(ph + Math.PI);
  return { lean: 20 + 3 * Math.sin(2 * ph), chest: 6, head: -10, sh1: -60 * Math.sin(ph), el1: 85, sh2: 60 * Math.sin(ph), el2: 85,
    hip1: a.hip, kn1: a.kn, an1: a.an, hip2: b.hip, kn2: b.kn, an2: b.an };
}
// Sneak: one long low stride per beat, arms tucked, head level.
function sneak(ph) {
  const leg = (p) => { const s = Math.sin(p), c = Math.cos(p); return { hip: 34 + 44 * s, kn: 60 + 70 * Math.pow(Math.max(0, c), 1.2), an: 20 }; };
  const a = leg(ph), b = leg(ph + Math.PI);
  return { lean: 32, chest: 8, head: -28, sh1: 40 + 10 * Math.sin(ph), el1: 100, sh2: 20 - 10 * Math.sin(ph), el2: 110,
    hip1: a.hip, kn1: a.kn, an1: a.an, hip2: b.hip, kn2: b.kn, an2: b.an };
}
const runAir = (ph) => 10 * Math.max(0, Math.sin(2 * ph));
function leap(u, u0, d, h) {
  const k = seg(u, u0, u0 + d);
  const pose = clip([[0, POSES.anticip], [0.2, POSES.anticip], [0.3, POSES.takeoff], [0.55, POSES.tuck], [0.82, POSES.reach], [0.92, POSES.crouch], [1, POSES.crouch]], k);
  const fly = seg(k, 0.25, 0.92);
  return { pose, air: Math.sin(fly * Math.PI) * h, k };
}

function bone(a, b, w1, w2, col) {
  const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L;
  poly([[a[0] + nx * w1 / 2, a[1] + ny * w1 / 2], [b[0] + nx * w2 / 2, b[1] + ny * w2 / 2], [b[0] - nx * w2 / 2, b[1] - ny * w2 / 2], [a[0] - nx * w1 / 2, a[1] - ny * w1 / 2]], col);
  circle(a[0], a[1], w1 / 2, col); circle(b[0], b[1], w2 / 2, col);
}
// A trailing chain (scarf, tails): streams behind with speed, hangs and sways at rest.
function chain(anchor, n, seglen, t, vx, face, droop, phase = 0) {
  const pts = [anchor];
  const speed = clamp(Math.abs(vx) / 500);
  const back = Math.abs(vx) > 5 ? -Math.sign(vx) : -1;
  for (let i = 1; i <= n; i++) {
    const p = pts[i - 1];
    const ang = Math.atan2(lerp(1.0 + droop, 0.12, speed), back) + Math.sin(t * (5 + 5 * speed) - i * 0.8 + phase) * (0.16 + 0.12 * speed);
    pts.push([p[0] + Math.cos(ang) * seglen, p[1] + Math.sin(ang) * seglen]);
  }
  return pts;
}

function ninja(o) {
  const { x, y, s = 1, face = 1, kind = "rogue", t = 0, air = 0, vx = 0, color = C.night, back = C.hill, blink = true } = o;
  const p = { ...STAND, ...(o.pose || {}) };
  const tall = kind === "guardian" ? 1.05 : 1;
  const thigh = 50 * tall, shin = 52 * tall, up = 40, fore = 36, low = 40, upper = 30;
  const dir = (a) => [Math.sin(a * D), Math.cos(a * D)];
  const legPts = (h, k, an) => { const d1 = dir(h), d2 = dir(h - k); const knee = [d1[0] * thigh, d1[1] * thigh]; const ank = [knee[0] + d2[0] * shin, knee[1] + d2[1] * shin];
    const fa = (h - k + 90 - an) * D; const toe = [ank[0] + Math.sin(fa) * 24, ank[1] + Math.cos(fa) * 24]; const heel = [ank[0] - Math.sin(fa) * 7, ank[1] - Math.cos(fa) * 7]; return { knee, ank, toe, heel }; };
  const L1 = legPts(p.hip1, p.kn1, p.an1), L2 = legPts(p.hip2, p.kn2, p.an2);
  const lowest = Math.max(L1.ank[1] + 6, L2.ank[1] + 6, L1.toe[1], L2.toe[1], 30);
  const hip = [0, -lowest - air];
  const mid = [hip[0] + Math.sin(p.lean * D) * low, hip[1] - Math.cos(p.lean * D) * low];
  const ca = (p.lean + p.chest) * D;
  const sh = [mid[0] + Math.sin(ca) * upper, mid[1] - Math.cos(ca) * upper];
  const armPts = (a, el) => { const d1 = dir(a); const e = [sh[0] + d1[0] * up, sh[1] + d1[1] * up]; const d2 = dir(a + el); return [e, [e[0] + d2[0] * fore, e[1] + d2[1] * fore]]; };
  const A1 = armPts(p.sh1, p.el1), A2 = armPts(p.sh2, p.el2);
  const ha = (p.lean + p.chest + p.head) * D, neck = [sh[0] + Math.sin(ca) * 8, sh[1] - Math.cos(ca) * 8];
  const head = [neck[0] + Math.sin(ha) * 20, neck[1] - Math.cos(ha) * 20];
  const add = (a, b) => [a[0] + b[0], a[1] + b[1]];
  const W_ = (pt) => [x + pt[0] * s * face, y + pt[1] * s];

  // scarf and tails, in world space, behind the body
  if (kind === "guardian") {
    const pts = chain(W_(add(neck, [-6, 6])), 11, 15 * s, t, vx, face, 0.2);
    for (let i = 0; i < pts.length - 1; i++) line([pts[i], pts[i + 1]], C.moon, (10 - i * 0.7) * s);
  } else {
    for (const k of [0, 1]) {
      const pts = chain(W_(add(head, [-14, -8])), 5, 11 * s, t, vx, face, 0.5 + k * 0.3, k * 1.3);
      for (let i = 0; i < pts.length - 1; i++) line([pts[i], pts[i + 1]], C.rose, (6 - i) * s);
    }
  }

  ctx.save(); ctx.translate(x, y); ctx.scale(s * face, s);
  const leg = (L, col) => {
    bone(hip, add(hip, L.knee), 21, 16, col); bone(add(hip, L.knee), add(hip, L.ank), 16, 10, col);
    poly([add(hip, L.heel), add(hip, L.ank), add(hip, L.toe), add(add(hip, L.toe), [-2, 5]), add(add(hip, L.heel), [0, 6])], col);
    if (kind === "rogue" && col === color) { const k = add(hip, L.knee), a = add(hip, L.ank); bone([lerp(k[0], a[0], 0.55), lerp(k[1], a[1], 0.55)], [lerp(k[0], a[0], 0.8), lerp(k[1], a[1], 0.8)], 13, 11, C.rose); }
  };
  const arm = (A, col) => { bone(sh, A[0], 14, 11, col); bone(A[0], A[1], 11, 9, col); circle(A[1][0], A[1][1], 7, col); };
  leg(L2, back);
  arm(A2, back);
  if (kind === "rogue") {
    const b0 = add(mid, [-Math.cos(ca) * 22, -Math.sin(ca) * 22 + 4]);
    ctx.beginPath(); ctx.ellipse(b0[0] - 6, b0[1] - 6, 20, 26, ca, 0, Math.PI * 2); ctx.fillStyle = C.hill; ctx.fill();
  } else {
    line([add(mid, [-30, 26]), add(sh, [-4, -46])], C.hill, 7);
    const f = Math.sin(t * 9) * 6 * clamp(Math.abs(vx) / 400) + 4;
    poly([add(hip, [-14, -4]), add(hip, [12, -4]), add(hip, [6 - f, 40]), add(hip, [-24 - f * 1.5, 36])], color);
  }
  bone(hip, mid, 30, 32, color);
  bone(mid, sh, 32, 38, color);
  leg(L1, color);
  if (kind === "rogue") { const b = [lerp(hip[0], mid[0], 0.2), lerp(hip[1], mid[1], 0.2)]; bone(add(b, [-16, 0]), add(b, [16, 0]), 8, 8, C.rose); }
  bone(neck, head, 12, 10, color);
  circle(head[0], head[1], 19, color);
  if (kind === "rogue") poly([[head[0] - 4, head[1] - 19], [head[0] - 30, head[1] - 2], [head[0] - 10, head[1] + 12]], color);
  if (kind === "guardian") {
    ctx.save(); ctx.translate(head[0], head[1] - 8); ctx.rotate((p.head + p.lean + p.chest) * D * 0.35);
    ctx.beginPath(); ctx.moveTo(-62, 4); ctx.quadraticCurveTo(0, -48, 62, 4); ctx.lineTo(58, 8); ctx.lineTo(-58, 8); ctx.closePath(); ctx.fillStyle = color; ctx.fill();
    ctx.restore();
  }
  let eyes = o.eyes ?? 1;
  if (blink) { const b = (t * 0.37 + (kind === "rogue" ? 0.5 : 0)) % 1; if (b < 0.035) eyes *= 0.15; }
  if (eyes > 0.02) rect(head[0] + 3, head[1] - 4 * eyes, 17, Math.max(1.5, 7 * eyes), kind === "guardian" ? C.moon : C.lamp);
  arm(A1, color);
  ctx.restore();
  return { hand: W_(A1[1]), hand2: W_(A2[1]), head: W_(head), hip: W_(hip), sh: W_(sh) };
}
const vel = (fx, u) => (fx(u) - fx(u - 0.04)) / 0.04;

// ------------------------------------------------------------------ shots
const SHOTS = [];
const shot = (a, b, draw, caps = []) => SHOTS.push({ a: a * BAR, b: b * BAR, draw, caps });
const demo = (a, b, d, caps) => SHOTS.push({ a: a * BAR, b: b * BAR, demo: d, caps });

// 1. The city
SHOTS.push({ a: 0, b: 4.7, caps: [[0.5, "In a city that never sleeps, one vault keeps the files of ten thousand customers"]], draw(u, t) {
  const c = { x: 960 + u * 10, y: 540, z: 1 + u * 0.012 };
  night(c, t);
  camera(c, 1);
  rect(-2000, 860, 7000, 600, C.night);
  for (const bx of [80, 420, 760]) building(bx, 860, 260, 110, C.hill, 1, C.lamp, bx);
  fortress(1500, 860);
} });

// 2. The rogue lands on the downbeat (5.0 s), opens his eyes, rises
SHOTS.push({ a: 4.7, b: 10, caps: [[0.5, "Tonight, a thief has found a crack in its door"]], draw(u, t) {
  const c = { x: 900, y: 520, z: 1.7, r: -0.035 };
  night(c, t, { moonX: 1250, moonY: 260 });
  camera(c, 1);
  building(380, 900, 1100, 120, C.night, 1, null, 9);
  const land = 0.3, ground = 668, fall = seg(u, 0, land);
  const pose = u < land ? POSES.tuck : clip([[land, POSES.crouch], [land + 0.12, P({ ...POSES.crouch, lean: 52, kn1: 150, kn2: 146 })], [2.6, POSES.crouch], [3.4, POSES.look], [4.0, idle(t)]], u);
  ninja({ x: 880, y: ground - (u < land ? (1 - fall * fall) * 860 : 0), kind: "rogue", pose, t, eyes: u < 1.5 ? 0.05 : ease(seg(u, 1.5, 1.8)), blink: u > 2 });
  burst(880, ground, seg(u, land, land + 0.6), C.rose, 8, 30, 120);
} });

// 3. The run across the roofs, a leap on bar 6 (15.0 s)
shot(4, 7, (u, t) => {
  const rx = (u) => 300 + u * 360;
  const c = { x: rx(u) + 260, y: 560, z: 1.25 };
  night(c, t, { moonX: 1500, moonY: 250 });
  camera(c, 1);
  for (const [a, b] of [[-200, 1820], [2080, 3400]]) rect(a, 760, b - a, 700, C.night);
  const ph = u * Math.PI * 2 / BEAT;
  const lp = leap(u, 4.45, 1.1, 190);
  const inLeap = u > 4.45 && u < 5.55;
  ninja({ x: rx(u), y: 760, kind: "rogue", pose: inLeap ? lp.pose : run(ph), air: inLeap ? lp.air : runAir(ph), vx: vel(rx, u), t });
}, [[0.3, "He needs no key. Only a strange name for a file: <code>../../../../etc/passwd</code>"]]);

// 4. The breach: he looks both ways, raises the forged scroll, the vault obeys
shot(7, 9, (u, t) => {
  const c = { x: 1480 + u * 8, y: 640, z: 1.45 + u * 0.03, r: 0.07 };
  night(c, t);
  camera(c, 1);
  rect(-1000, 860, 5000, 600, C.night);
  fortress(1650, 860, { open: ease(seg(u, 2.4, 3.0)) });
  const pose = clip([[0, P({ ...POSES.look, head: 30 })], [0.35, P({ ...POSES.look, head: -18 })], [0.6, POSES.look], [0.8, POSES.raise], [0.9, P({ ...POSES.raise, sh1: 176 })], [1.0, POSES.raise], [2.6, POSES.raise], [3.0, POSES.reach]], u);
  const pr = ninja({ x: 1360, y: 860, kind: "rogue", pose, t });
  if (u > 0.85 && u < 2.9) scroll(pr.hand[0] + 10, pr.hand[1] - 30, 330, "../../../../etc/passwd", C.moon, C.night, 22);
  ["passwd", ".env", "customers"].forEach((l, i) => {
    const k = seg(u, 2.8 + i * 0.45, 3.6 + i * 0.45);
    if (k <= 0 || k >= 1) return;
    scroll(lerp(1650, 1370, k), lerp(780, 690, k) - Math.sin(k * Math.PI) * 170, 150, l, C.lamp, C.night, 20);
  });
}, [[0.4, "And the vault, obedient, hands over its own secrets"]]);

// 5. The hours
shot(9, 12, (u, t) => {
  const c = { x: 960, y: 540, z: 1 };
  night(c, t, { moonX: 1280, moonY: 330, moonR: 190 });
  camera(c, 0.08);
  for (let i = 0; i < 12; i++) { const a = (i / 12) * Math.PI * 2; line([[1280 + Math.cos(a) * 160, 330 + Math.sin(a) * 160], [1280 + Math.cos(a) * 175, 330 + Math.sin(a) * 175]], C.night, 6); }
  const ah = u * 1.6, am = u * 19;
  line([[1280, 330], [1280 + Math.sin(ah) * 90, 330 - Math.cos(ah) * 90]], C.night, 12);
  line([[1280, 330], [1280 + Math.sin(am) * 140, 330 - Math.cos(am) * 140]], C.night, 7);
  camera(c, 1);
  rect(-200, 880, 2400, 400, C.night);
  building(120, 880, 330, 210, C.hill, 1, null, 5);
  rect(190, 720, 190, 110, C.lamp);
  poly([[210, 800], [360, 800], [360, 812], [210, 812]], C.night);
  circle(230, 790, 13, C.night);
  if (Math.floor(u / 0.5) % 2 === 0) rect(330, 784, 18, 12, C.moon);
  fortress(1550, 880);
  const lapT = 1.8, out = (u % lapT) / lapT < 0.5;
  const rx = (u) => { const l = (u % lapT) / lapT; return lerp(1000, 1420, l < 0.5 ? l * 2 : (1 - l) * 2); };
  ninja({ x: rx(u), y: 880, s: 0.8, face: out ? 1 : -1, kind: "rogue", pose: run(u * 13), air: runAir(u * 13), vx: vel(rx, u), t });
  if (!out) scroll(rx(u), 790, 70, "", C.lamp);
}, [[0.3, "Someone must wake, find the flaw, forge a fix, test it and send it out"], [4.0, "That takes hours. All the while, the thief keeps taking"]]);

// 6. A hasty rule, and the walk around it
shot(12, 14, (u, t) => {
  const c = { x: 1450, y: 650, z: 1.4 };
  night(c, t);
  camera(c, 1);
  rect(-1000, 860, 5000, 600, C.night);
  fortress(1650, 860, { open: ease(seg(u, 2.6, 3.0)) });
  const pin = easeOut(seg(u, 0.1, 0.5));
  ctx.save(); ctx.translate(1700, lerp(500, 720, pin)); rect(-90, 0, 180, 60, C.moon); text("block ../", 0, 40, { size: 26, font: "mono", color: C.night, align: "center" }); ctx.restore();
  const flip = seg(u, 1.6, 2.3);
  const rx = (u) => (u < 0.9 ? lerp(1140, 1260, seg(u, 0, 0.9)) : lerp(1260, 1720, seg(u, 3.0, 4.7)));
  const walking = u > 3.0 && u < 4.7;
  const pose = walking || u < 0.9 ? sneak(u * Math.PI * 2 / BEAT) : clip([[0.9, POSES.look], [1.2, P({ ...POSES.look, head: 24 })], [1.5, POSES.raise], [3.0, POSES.raise]], u);
  const pr = ninja({ x: rx(u), y: 860, kind: "rogue", pose, vx: vel(rx, u), t });
  if (!walking && u > 1.5) {
    const sx = Math.abs(Math.cos(flip * Math.PI));
    ctx.save(); ctx.translate(pr.hand[0] + 10, pr.hand[1] - 30); ctx.scale(Math.max(0.02, sx), 1);
    scroll(0, 0, 370, flip < 0.5 ? "../../etc/passwd" : "....//....//etc/passwd", C.moon, C.night, 22);
    ctx.restore();
  }
}, [[0.4, "A hasty rule on the door? He changes one mark and walks straight past"]]);

// 7. Doubt: a slow close-up on his eye, then black on the last beat
shot(14, 16, (u, t) => {
  if (u > 4.4) { fill(C.night); return; }
  fill(C.sky);
  camera({ x: 960, y: 560, z: 1 + u * 0.03 }, 1);
  ninja({ x: 900, y: 540 + 212 * 7, s: 7, kind: "rogue", pose: P({ head: -4, sh1: 0, sh2: 0 }), t, eyes: 1 - 0.65 * ease(seg(u, 1.2, 3.2)), blink: false });
}, [[0.4, "And a fix written by a machine is not safe merely because it looks right"]]);

// 8. The guardian and the title (the drop at 40.0 s)
function tower(x, base) {
  rect(x - 70, base - 640, 140, 640, C.night);
  for (let i = 0; i < 5; i++) building(x - 120 + i * 12, base - 120 * i, 240 - i * 24, 0, C.night, 1, null, i);
  rect(x - 90, base - 660, 180, 26, C.night);
  return base - 660;
}
shot(16, 20, (u, t) => {
  const crane = ease(seg(u, 0, 3.2));
  const c = { x: 1280, y: lerp(980, 420, crane), z: lerp(1.25, 1.0, crane) };
  fill(C.sky);
  camera(c, 0.6);
  circle(1520, 330, 280, C.moon);
  camera(c, 1);
  mountains(c, 980);
  const top = tower(1460, 1300);
  const pose = clip([[0, idle(t)], [0.3, P({ ...STAND, head: -10, chest: 4 })], [1.2, idle(t)]], u);
  ninja({ x: 1460, y: top, s: 1.15, face: -1, kind: "guardian", pose, t, eyes: ease(seg(u, 0.05, 0.25)), blink: u > 1 });
  screen();
  if (u > 2.4) text("OODA-Aegis", 140, 470, { size: 120 });
  if (u > 4.0) text("The guardian that watches, blocks and heals a live service", 146, 548, { size: 44, font: "story" });
  if (u > 5.6) text("By Nikhil Kumar", 146, 612, { size: 40, font: "story", color: C.lamp });
});

// 9. Observe: threads from every window; his head turns to the pink one
shot(20, 22, (u, t) => {
  const c = { x: 960, y: 540, z: 1 };
  night(c, t, { moonX: 520, moonY: 240, moonR: 120 });
  camera(c, 1);
  rect(-200, 900, 2400, 400, C.night);
  fortress(1450, 900);
  const eye = [470, 470];
  [[1290, 560], [1360, 620], [1440, 520], [1520, 600], [1600, 560], [1400, 700], [1500, 700]].forEach(([wx, wy], i) => {
    const hot = i === 3 && u > 1.6;
    line([[wx, wy], eye], hot ? C.lamp : C.rose, hot ? 5 : 2);
    if (hot) { const k = (u - 1.6) % 1; scroll(lerp(wx, eye[0], k), lerp(wy, eye[1], k), 60, "", C.lamp); }
  });
  ninja({ x: 360, y: 1180, s: 3.2, face: 1, kind: "guardian", pose: clip([[0, idle(t)], [1.6, idle(t)], [2.0, P({ ...STAND, head: 14, chest: 6 })]], u), t });
}, [[0.3, "The guardian reads every answer the vault gives. One stolen file is enough"]]);

// --- demo shots: the real dashboard, with a cursor, zooms and scrolling
demo(22, 25, { file: "path_traversal", from: 4.6, to: 10.4, view: "console",
  events: [{ at: 0.9, click: "Read /etc/passwd" }, { at: 1.6, click: "Play recorded run", noop: true }],
  focus: [[0, null], [1.9, "panel:Attacker"], [3.9, "panel:Attacker"], [4.6, "panel:Defense agent"]] },
  [[0.2, "<b>Llama 3.2 3B</b> names the attack in two seconds: path traversal"], [4.2, "What you see is a real run, recorded live on a laptop"]]);

// 11. The seal: one arc down to the gate, the slap on beat 3, the rogue thrown back
shot(25, 27, (u, t) => {
  const c = { x: 1500, y: 640, z: 1.35 + u * 0.02 };
  night(c, t);
  camera(c, 1);
  rect(-1000, 860, 5000, 600, C.night);
  const slap = 1.25;
  fortress(1650, 860, { seal: u > slap ? seg(u, slap, slap + 0.15) : 0 });
  const gx = (u) => lerp(1150, 1530, smooth(seg(u, 0, 1.0)));
  const lp = leap(u, 0, 1.0, 300);
  const pose = u < 1.0 ? lp.pose : clip([[1.0, POSES.crouch], [1.1, POSES.windup], [slap, POSES.push], [slap + 0.6, POSES.push], [2.2, idle(t)]], u);
  ninja({ x: gx(u), y: 860, kind: "guardian", pose, air: u < 1.0 ? lp.air + (1 - lp.k) * 120 : 0, vx: vel(gx, u), t });
  burst(1702, 730, seg(u, slap, slap + 0.5), C.moon, 10, 30, 110);
  if (u > 2.0) {
    const strike = 3.0;
    const rx = (u) => (u < strike ? lerp(1060, 1390, seg(u, 2.0, strike)) : lerp(1390, 1130, easeOut(seg(u, strike, strike + 0.9))));
    const pose = u < 2.6 ? run(u * 13) : clip([[2.6, POSES.windup], [strike, POSES.lunge], [strike + 0.12, POSES.hurt], [strike + 0.9, POSES.hurt], [strike + 1.6, POSES.crouch]], u);
    ninja({ x: rx(u), y: 860, kind: "rogue", pose, vx: vel(rx, u), air: u > strike && u < strike + 0.9 ? Math.sin(seg(u, strike, strike + 0.9) * Math.PI) * 60 : 0, t });
    burst(1440, 740, seg(u, strike, strike + 0.6), C.lamp, 12, 20, 140);
  }
}, [[0.3, "He seals the gate, makes sure honest visitors still pass, and sets the seal at the proxy"]]);

demo(27, 29, { file: "path_traversal", from: 10.42, to: 12.66, view: "console",
  events: [{ at: 0.8, click: "Virtual patch" }],
  focus: [[0, null], [0.4, "panel:Defense agent"], [2.8, "panel:Defense agent"], [3.4, "panel:Production service"]] },
  [[0.2, "<b>Contained 5.3 seconds</b> after the leak. The thief gets 403, customers get their files"]]);

// 13. Red team: his own shadows test his own seal
shot(29, 31, (u, t) => {
  const c = { x: 1450, y: 620, z: 1.2 };
  night(c, t);
  camera(c, 1);
  rect(-1000, 860, 5000, 600, C.night);
  fortress(1650, 860, { seal: 1, open: u > 2.2 ? 0.15 : 0 });
  ninja({ x: 1960, y: 860, kind: "guardian", face: -1, pose: u > 3.8 ? blend(idle(t), POSES.bow, seg(u, 3.8, 4.3)) : idle(t), t });
  [["..%2f..%2fetc/passwd", false], ["....//....//etc/passwd", true], ["%2e%2e/%2e%2e/etc/passwd", true]].forEach(([label, through], i) => {
    const a = 0.2 + i * 1.3;
    if (u < a) return;
    const rx = (u) => { const k = seg(u, a, a + 1.0); return !through && k >= 1 ? lerp(1560, 1400, easeOut(seg(u, a + 1.0, a + 1.5))) : lerp(1050, 1580, k); };
    if (through && u > a + 1.0) return;
    const bounced = !through && u > a + 1.0;
    ninja({ x: rx(u), y: 860, kind: "rogue", color: C.rose, back: C.hill, pose: bounced ? POSES.hurt : run(u * 12 + i), s: 0.9, vx: vel(rx, u), t: t + i });
    text(label, rx(u), 640, { size: 22, font: "mono", align: "center" });
    if (!through) burst(1600, 760, seg(u, a + 1.0, a + 1.5), C.moon, 8, 20, 90);
  });
}, [[0.3, "Then he attacks his own seal. Some of his shadows slip through. The door itself must change"]]);

demo(31, 32, { file: "path_traversal", from: 13.25, to: 13.25, view: "console",
  events: [{ at: 0.4, click: "Red team" }], scroll: { el: "scroller", a: 1.0, b: 2.4, px: 420 },
  focus: [[0, "panel:Defense agent"]] },
  [[0.1, "Thirteen new tricks. A rule alone cannot hold them all"]]);

// 15. The forge: a held wind-up, a hit on every beat
shot(32, 34, (u, t) => {
  fill(C.hill);
  camera({ x: 960, y: 560, z: 1.25 }, 1);
  rect(-400, 820, 2800, 600, C.night);
  rect(1300, 380, 360, 440, C.night);
  const fl = (k) => 0.8 + 0.2 * Math.sin(t * 13 + k);
  poly([[1380, 760], [1430, 760 - 120 * fl(0)], [1470, 760], [1500, 760 - 150 * fl(1)], [1540, 760], [1570, 760 - 110 * fl(2)], [1600, 760]], C.lamp);
  poly([[1420, 760], [1470, 760 - 60 * fl(3)], [1520, 760], [1560, 760 - 70 * fl(4)], [1590, 760]], C.moon);
  poly([[780, 700], [1080, 700], [1040, 740], [990, 740], [990, 820], [870, 820], [870, 740], [820, 740]], C.night);
  padlock(930, 690, 1.2, C.moon);
  const b = (u / BEAT) % 1;
  const pose = clip([[0, POSES.hammerDown], [0.12, P({ ...POSES.hammerDown, lean: 26 })], [0.55, POSES.hammerUp], [0.85, POSES.hammerUp], [1.0, POSES.hammerDown]], b);
  const g = ninja({ x: 700, y: 820, s: 1.15, kind: "guardian", pose, t });
  const a = Math.atan2(g.hand[1] - g.sh[1], g.hand[0] - g.sh[0]);
  const tip = [g.hand[0] + Math.cos(a) * 50, g.hand[1] + Math.sin(a) * 50];
  line([g.hand, tip], C.night, 10);
  ctx.save(); ctx.translate(tip[0], tip[1]); ctx.rotate(a + Math.PI / 2); rect(-22, -12, 44, 24, C.night); ctx.restore();
  burst(940, 660, b / 0.5, C.lamp, 9, 20, 120);
}, [[0.3, "<b>Llama 3.1 8B</b> writes down what the code must promise, then reforges it"]]);

demo(34, 37, { file: "path_traversal", from: 37.3, to: 37.3, view: "console",
  events: [{ at: 0.8, click: "Code repair" }], scroll: { el: "pre", a: 2.6, b: 7.0, px: 520 },
  focus: [[0, null], [1.4, "pre"]] },
  [[0.2, "The new code keeps only the file's name, so nothing outside the folder can be reached"]]);

// 17. The sealed room
shot(37, 39, (u, t) => {
  fill(C.night);
  camera({ x: 960, y: 540, z: 1 }, 1);
  rect(260, 140, 1400, 760, C.hill);
  text("A sealed room, no way out", 960, 220, { size: 40, font: "story", align: "center", color: C.lamp });
  rect(560, 700, 140, 200, C.night); rect(1220, 700, 140, 200, C.night);
  const breakK = seg(u, 1.25, 1.8);
  padlock(630, 650, 1.4, C.rose, breakK);
  burst(630, 640, breakK, C.rose, 10, 20, 120);
  padlock(1290, 650, 1.4, C.moon);
  text("Old code", 630, 960, { size: 30, align: "center" });
  text("New code", 1290, 960, { size: 30, align: "center" });
  const sx = (u) => (u < 1.0 ? lerp(320, 520, seg(u, 0.1, 1.0)) : u < 2.0 ? 520 : lerp(520, 1180, seg(u, 2.0, 2.8)));
  const pose = clip([[0, run(u * 12)], [0.9, run(u * 12)], [1.0, POSES.windup], [1.25, POSES.lunge], [1.8, POSES.lunge], [2.0, run(u * 12)], [2.8, run(u * 12)], [2.85, POSES.windup], [3.05, POSES.lunge], [3.15, POSES.hurt], [4.2, POSES.hurt]], u);
  ninja({ x: sx(u), y: 900, kind: "rogue", color: C.rose, back: C.sky, pose, vx: vel(sx, u), t });
  if (u > 3.05) { burst(1290, 640, seg(u, 3.05, 3.7), C.moon, 12, 20, 140); text("holds", 1290, 540, { size: 34, align: "center" }); }
  if (u > 1.5) text("breaks", 630, 540, { size: 34, align: "center", color: C.lamp });
}, [[0.3, "In a sealed room, the real attack must break the old lock and fail on the new one"]]);

demo(39, 42, { file: "path_traversal", from: 39.03, to: 39.03, view: "console",
  events: [{ at: 0.8, click: "Sandbox proof" }], scroll: { el: "window", a: 3.4, b: 7.0, px: 520 },
  focus: [[0, null], [1.5, "first:.grid"], [3.0, null]] },
  [[0.2, "Every trick, every old test and every honest request must pass. The machine's own test counts for nothing"]]);

// 19. Rollout along the wall
shot(42, 44, (u, t) => {
  const camx = (u) => lerp(700, 2050, ease(seg(u, 0.2, 4.6)));
  const c = { x: camx(u), y: 600, z: 1.15 };
  night(c, t);
  camera(c, 1);
  rect(-200, 820, 3200, 600, C.night);
  rect(-200, 560, 3200, 260, C.hill);
  const swaps = [0.6, 2.5, 4.4], pct = ["10%", "50%", "100%"];
  [700, 1375, 2050].forEach((gx, i) => {
    const on = u > swaps[i];
    rect(gx - 110, 610, 220, 210, C.rose);
    rect(gx - 96, 624, 192, 196, C.night);
    padlock(gx, 720, 1.2, on ? C.moon : C.rose);
    burst(gx, 710, seg(u, swaps[i], swaps[i] + 0.5), C.moon, 10, 30, 110);
    if (on) text(pct[i], gx, 520, { size: 56, align: "center" });
  });
  const gx = (u) => camx(u) - 40;
  ninja({ x: gx(u), y: 560, s: 0.8, kind: "guardian", pose: run(u * 12), air: runAir(u * 12), vx: Math.max(200, vel(gx, u)), t });
}, [[0.3, "The new lock goes on one gate, then half of them, then all, checked at every step"]]);

demo(44, 46, { file: "path_traversal", from: 39.03, to: 47.6, view: "sandbox",
  events: [{ at: 0.5, click: "Command center" }],
  focus: [[0, null], [1.0, "panel:Production service"]] },
  [[0.2, "If a single check fails, the old lock returns at once"]]);

// 21. The rogue gets nothing, and flees
shot(46, 48, (u, t) => {
  const c = { x: 1500, y: 630, z: 1.3 };
  night(c, t);
  camera(c, 1);
  rect(-1000, 860, 5000, 600, C.night);
  fortress(1650, 860, { lock: "new" });
  rect(1780, 600, 260, 260, C.hill);
  ninja({ x: 1890, y: 600, kind: "guardian", face: -1, pose: idle(t), t, s: 0.9 });
  const rx = (u) => (u < 0.8 ? lerp(1100, 1400, seg(u, 0, 0.8)) : lerp(1400, 900, seg(u, 3.1, 4.3)));
  const lp = leap(u, 3.0, 1.3, 320);
  const pose = u > 3.0 ? lp.pose : u < 0.8 ? sneak(u * Math.PI * 2 / BEAT) : clip([[0.8, POSES.raise], [1.9, POSES.raise], [2.2, P({ ...POSES.raise, head: 20, sh1: 120, el1: 40 })], [2.8, P({ ...POSES.look, head: 30 })]], u);
  const pr = ninja({ x: rx(u), y: 860, kind: "rogue", face: u > 2.8 ? -1 : 1, pose, air: u > 3.0 ? lp.air : 0, vx: vel(rx, u), t });
  if (u > 0.9 && u < 3.0) scroll(pr.hand[0] + 10, pr.hand[1] - 30, 330, u < 1.9 ? "../../../../etc/passwd" : "not found", u < 1.9 ? C.moon : C.lamp, C.night, 22);
}, [[0.3, "<b>Healed 42.6 seconds</b> after the leak. The thief tries his scroll again, and gets nothing"]]);

demo(48, 50, { file: "sqli", from: 42.52, to: 42.52, view: "console",
  events: [{ at: 0.5, click: "Code repair" }], scroll: { el: "pre", a: 1.8, b: 5.0, px: 380 },
  focus: [[0, null], [1.1, "pre"]] },
  [[0.2, "A second flaw, SQL injection: mended with a parameterised query in <b>46 seconds</b>"]]);

// 23. The knot and the bell
shot(50, 52, (u, t) => {
  const c = { x: 1450, y: 620, z: 1.25 };
  night(c, t);
  camera(c, 1);
  rect(-1000, 860, 5000, 600, C.night);
  fortress(1650, 860, { seal: 1 });
  const k = seg(u, 0.1, 2.2), pts = [];
  for (let i = 0; i <= 60 * k; i++) { const a = i * 0.55; pts.push([1650 + Math.cos(a) * (70 + i * 0.7) + Math.sin(i * 0.3) * 20, 765 + Math.sin(a) * (55 + i * 0.4)]); }
  if (pts.length > 1) line(pts, C.rose, 6);
  ninja({ x: 1180, y: 860, kind: "rogue", pose: clip([[0, POSES.windup], [0.3, POSES.lunge], [0.6, POSES.reach], [2.2, POSES.reach], [2.6, POSES.look]], u), t });
  const r_ = seg(u, 2.5, 4.6), sw = Math.sin(r_ * 14) * (1 - r_) * 0.4;
  rect(1960, 560, 12, 300, C.night); rect(2150, 560, 12, 300, C.night); rect(1940, 545, 240, 20, C.night);
  ctx.save(); ctx.translate(2066, 565); ctx.rotate(sw); poly([[-40, 20], [40, 20], [60, 130], [-60, 130]], C.rose); ctx.restore();
  if (r_ > 0) for (let i = 0; i < 3; i++) { const r = ((u - 2.5) * 140 + i * 70) % 260; if (r > 20) ring(2066, 640, r, C.moon, 3); }
  const pose = clip([[0, idle(t)], [1.2, P({ ...STAND, head: 18 })], [1.9, P({ ...STAND, head: -6 })], [2.2, POSES.pullUp], [2.5, POSES.pullDown], [3.0, POSES.pullUp], [3.3, POSES.pullDown], [4.0, idle(t)]], u);
  ninja({ x: 1900, y: 860, kind: "guardian", face: 1, pose, t, s: 0.95 });
}, [[0.3, "And when no fix can pass the trial, he changes nothing and rings for a human"]]);

// 24. Lanterns: Meta models
shot(52, 56, (u, t) => {
  fill(C.night);
  const c = { x: lerp(900, 1020, u / 10), y: 520, z: 1 };
  camera(c, 0.3);
  circle(1500, 230, 110, C.hill);
  camera(c, 1);
  ctx.beginPath(); ctx.moveTo(140, 230); ctx.quadraticCurveTo(960, 360, 1780, 230); ctx.strokeStyle = C.hill; ctx.lineWidth = 5; ctx.stroke();
  [[460, "Llama 3.2 3B", "Sees the attack and blocks it", "Open weights, on a laptop"],
    [960, "Llama 3.1 8B", "Writes the code fix", "Open weights, on a laptop"],
    [1460, "Muse Glimmer 30B", "Both tasks, right on the first try", "Two free Kaggle T4 GPUs"]].forEach(([x, name, job, where], i) => {
    const lit = u > i * BAR;
    const y = 300 + Math.sin(t * 1.2 + i) * 6;
    rect(x - 2, 262, 4, y - 262, C.hill);
    rect(x - 36, y - 6, 72, 14, C.hill);
    ctx.beginPath(); ctx.ellipse(x, y + 70, 62, 78, 0, 0, Math.PI * 2); ctx.fillStyle = lit ? C.lamp : C.hill; ctx.fill();
    if (lit) { ctx.beginPath(); ctx.ellipse(x, y + 70, 34, 52, 0, 0, Math.PI * 2); ctx.fillStyle = C.moon; ctx.fill(); }
    rect(x - 36, y + 140, 72, 14, C.hill);
    if (lit) {
      text(name, x, 590, { size: 40, align: "center" });
      text(job, x, 644, { size: 34, font: "story", align: "center", color: C.lamp });
      text(where, x, 688, { size: 34, font: "story", align: "center", color: C.lamp });
    }
  });
}, [[0.4, "Every model is Meta's, with open weights. Your code and secrets never leave your own machine"]]);

// 25. The trials (results)
shot(56, 62, (u) => {
  fill(C.night);
  screen();
  text("The trials", 200, 200, { size: 52, color: C.lamp });
  text("Three real flaws, three trials each, the same sealed room for both", 200, 256, { size: 36, font: "story" });
  [["9 of 9", "flaws fixed and proven with Llama on a laptop"], ["9 of 9", "with Muse Glimmer 30B, every one on the first try"], ["0 of 9", "of Llama's own tests were right. The sealed room caught every one"]].forEach(([big, small], i) => {
    if (u < i * 2 * BAR) return;
    const y = 400 + i * 190;
    text(big, 200, y + 40, { size: 112 });
    text(small, 700, y + 24, { size: 44, font: "story" });
  });
});

// 26. End
shot(62, 68, (u, t) => {
  const c = { x: 1280, y: lerp(420, 560, ease(seg(u, 0, 12))), z: lerp(1.1, 0.86, ease(seg(u, 0, 12))) };
  fill(C.sky);
  camera(c, 0.6);
  circle(1520, 330, 280, C.moon);
  camera(c, 1);
  mountains(c, 980);
  const top = tower(1460, 1300);
  ninja({ x: 1460, y: top, s: 1.15, face: -1, kind: "guardian", pose: clip([[0, idle(t)], [3, POSES.bow], [5, idle(t)]], u), t });
  screen();
  if (u > 0.6) text("OODA-Aegis", 140, 450, { size: 120 });
  if (u > 1.8) text("By Nikhil Kumar", 146, 530, { size: 52, font: "story" });
  if (u > 3.0) text("github.com/Nikhil8557/ooda-aegis", 146, 610, { size: 34, font: "tech", color: C.lamp });
  if (u > 3.6) text("Meta Global AI Developer Hackathon 2026", 146, 664, { size: 36, font: "story", color: C.lamp });
  const out = seg(u, 13, 15);
  if (out > 0) { ctx.globalAlpha = out; fill(C.night); ctx.globalAlpha = 1; }
});

export const DURATION = 68 * BAR;
export const CAPTIONS = [];
for (const s of SHOTS) s.caps.forEach(([off, html], i) => CAPTIONS.push([s.a + off, i + 1 < s.caps.length ? s.a + s.caps[i + 1][0] - 0.1 : s.b - 0.15, html]));

// ------------------------------------------------------------------ the real dashboard in demo shots
const frames = {};
const screenEl = document.getElementById("screen"), stage = document.getElementById("stage");
const cursor = document.getElementById("cursor"), ripple = document.getElementById("ripple");
async function prepDemo(file) {
  const f = document.getElementById("d_" + file);
  if (!f.contentDocument || f.contentDocument.readyState !== "complete") await new Promise((r) => f.addEventListener("load", r, { once: true }));
  const w = f.contentWindow;
  while (!(w.__aegis && w.__aegis.frames.length)) await new Promise((r) => setTimeout(r, 100));
  w.__aegis.load(file + ".jsonl");
  while (!(w.__aegis.file === file + ".jsonl" && w.__aegis.frames.length)) await new Promise((r) => setTimeout(r, 100));
  const st = f.contentDocument.createElement("style");
  st.textContent = "[data-film-hide]{display:none!important} ::-webkit-scrollbar{display:none} *{transition:none!important}";
  f.contentDocument.head.appendChild(st);
  frames[file] = w.__aegis.frames;
}
await Promise.all(["path_traversal", "sqli"].map(prepDemo));
const raf = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));

function find(doc, spec) {
  if (!spec) return null;
  if (spec.startsWith("panel:")) { const h = [...doc.querySelectorAll("h2")].find((e) => e.textContent.trim() === spec.slice(6)); return h ? h.parentElement.parentElement : null; }
  if (spec.startsWith("first:")) return doc.querySelector(spec.slice(6));
  if (spec === "pre") return doc.querySelector("main pre");
  return [...doc.querySelectorAll("button")].find((b) => b.textContent.trim().startsWith(spec));
}
const box = (el) => { if (!el) return { x: 0, y: 0, w: 1600, h: 900 }; const r = el.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; };
function zoomFor(b) {
  // zoom by width; tall panels are framed from their top
  const pad = 40, s = clamp(1600 / (b.w + pad * 2), 1, 1.75);
  let tx = 800 - (b.x + b.w / 2) * s;
  let ty = b.h * s > 860 ? -(b.y - 24) * s : 450 - (b.y + b.h / 2) * s;
  tx = clamp(tx, 1600 - 1600 * s, 0); ty = clamp(ty, 900 - 900 * s, 0);
  return { s, tx, ty };
}
let demoState = { shot: null, idx: -1, done: new Set() };

async function renderDemo(s, u) {
  const d = s.demo, f = document.getElementById("d_" + d.file), w = f.contentWindow, doc = f.contentDocument;
  for (const x of document.querySelectorAll(".demo")) x.style.visibility = x === f ? "visible" : "hidden";
  screenEl.style.visibility = "visible";
  fill(C.night);
  const times = frames[d.file];
  const rt = d.from + (d.to - d.from) * clamp(u / (s.b - s.a));
  let idx = 0;
  while (idx + 1 < times.length && times[idx + 1] <= rt) idx++;
  if (demoState.shot !== s) {
    w.__aegis.view(d.view || "console");
    w.__aegis.seek(idx);
    await raf();
    w.scrollTo(0, 0);
    const tr = find(doc, "Trace"); if (tr) tr.click();
    demoState = { shot: s, idx, done: new Set() };
    await raf();
  }
  if (demoState.idx !== idx) { w.__aegis.seek(idx); demoState.idx = idx; await raf(); }
  for (const [i, e] of (d.events || []).entries()) {
    if (u >= e.at && !demoState.done.has(i)) { demoState.done.add(i); if (!e.noop) { const b = find(doc, e.click); if (b) b.click(); await raf(); } }
  }
  if (d.scroll) {
    const k = smooth(seg(u, d.scroll.a, d.scroll.b));
    if (d.scroll.el === "window") w.scrollTo(0, k * d.scroll.px);
    else {
      const el = d.scroll.el === "pre" ? doc.querySelector("main pre") : [...doc.querySelectorAll(".overflow-y-auto")].find((x) => x.scrollHeight > x.clientHeight + 10 && x.closest(".bg-deep"));
      if (el) el.scrollTop = k * d.scroll.px;
    }
  }
  // camera: ease between focus targets
  const F = d.focus || [[0, null]];
  let i = 0; while (i + 1 < F.length && F[i + 1][0] <= u) i++;
  const cur = zoomFor(box(find(doc, F[i][1])));
  let z = cur;
  if (i > 0) {
    const prev = zoomFor(box(find(doc, F[i - 1][1])));
    const k = smooth(seg(u, F[i][0], F[i][0] + 0.7));
    z = { s: lerp(prev.s, cur.s, k), tx: lerp(prev.tx, cur.tx, k), ty: lerp(prev.ty, cur.ty, k) };
  }
  stage.style.transform = `translate(${z.tx}px, ${z.ty}px) scale(${z.s})`;
  // cursor: glide to each click target, ripple on the click
  const ev = d.events || [];
  let pos = { x: 1250, y: 760 }, rip = null;
  for (const e of ev) {
    const b = box(find(doc, e.click)), target = { x: b.x + b.w * 0.4, y: b.y + b.h / 2 };
    const k = smooth(seg(u, e.at - 0.7, e.at - 0.05));
    pos = { x: lerp(pos.x, target.x, k), y: lerp(pos.y, target.y, k) };
    if (u >= e.at && u < e.at + 0.4) rip = { ...target, k: (u - e.at) / 0.4 };
  }
  cursor.style.transform = `translate(${pos.x}px, ${pos.y}px)`;
  cursor.style.visibility = ev.length ? "visible" : "hidden";
  if (rip) { ripple.style.visibility = "visible"; ripple.style.left = rip.x + "px"; ripple.style.top = rip.y + "px"; ripple.style.transform = `scale(${0.4 + rip.k})`; ripple.style.borderWidth = `${3 * (1 - rip.k) + 0.5}px`; }
  else ripple.style.visibility = "hidden";
  await raf();
}

async function renderAt(t) {
  const s = SHOTS.find((x) => t >= x.a && t < x.b) || SHOTS[SHOTS.length - 1];
  const u = t - s.a;
  const cap = s.caps.filter(([off]) => u >= off).pop();
  capEl.innerHTML = cap ? cap[1] : "";
  if (s.demo) return renderDemo(s, u);
  screenEl.style.visibility = "hidden";
  cursor.style.visibility = "hidden"; ripple.style.visibility = "hidden";
  for (const x of document.querySelectorAll(".demo")) x.style.visibility = "hidden";
  demoState = { shot: null, idx: -1, done: new Set() };
  ctx.globalAlpha = 1;
  s.draw(u, t);
  screen();
}

window.renderAt = renderAt;
window.DURATION = DURATION;
window.CAPTIONS = CAPTIONS;
window.READY = true;
