"""OODA-Aegis film score, synthesised from SCORE.md (96 BPM, D minor, 68 bars = 170 s).

Every sound is generated here with numpy, so the music is original.
Run: python3 video/music.py  ->  video/out/score.wav (44.1 kHz stereo)
"""
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM          # 0.625 s
BAR = 4 * BEAT           # 2.5 s
BARS = 68
DUR = BARS * BAR         # 170 s
N = int((DUR + 3) * SR)
rng = np.random.default_rng(7)
L = np.zeros(N)
R = np.zeros(N)
VERB = np.zeros(N)       # send bus for the room

hz = lambda m: 440 * 2 ** ((m - 69) / 12)
T = lambda bar, beat=0.0: bar * BAR + beat * BEAT


def add(sig, t0, gain=1.0, pan=0.0, verb=0.25):
    i = int(round(t0 * SR))
    if i >= N:
        return
    s = sig[: N - i] * gain
    L[i:i + len(s)] += s * np.sqrt((1 - pan) / 2) * 1.414
    R[i:i + len(s)] += s * np.sqrt((1 + pan) / 2) * 1.414
    VERB[i:i + len(s)] += s * verb


def tt(sec):
    return np.arange(int(sec * SR)) / SR


def lp(x, fc):
    """Low-pass by spectrum shaping (fine for one-shot sounds)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X /= np.sqrt(1 + (f / fc) ** 4)
    return np.fft.irfft(X, len(x))


def bp(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (f > lo) & (f < hi)
    return np.fft.irfft(X, len(x))


def fade(x, a=0.005, r=0.05):
    n = len(x)
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return x * e


# ------------------------------------------------------------------ instruments
def taiko(big=False):
    t = tt(1.6 if big else 0.9)
    f0 = 52 if big else 78
    f = f0 * (1 + 1.4 * np.exp(-t * 28))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (3.2 if big else 6.5))
    slap = lp(rng.standard_normal(len(t)), 1800) * np.exp(-t * 60) * 0.5
    return fade(body + slap, 0.001, 0.05)


def shime():
    t = tt(0.18)
    n = bp(rng.standard_normal(len(t)), 1500, 7000) * np.exp(-t * 55) * 0.5
    body = np.sin(2 * np.pi * 610 * t) * np.exp(-t * 40) * 0.6
    return fade(n + body, 0.0005, 0.02)


def koto(m, dur=1.4):
    t = tt(dur)
    f = hz(m)
    out = np.zeros(len(t))
    for h in range(1, 9):
        fh = f * h * (1 + 0.0007 * h * h)
        if fh > 12000:
            break
        out += np.sin(2 * np.pi * fh * t) / h * np.exp(-t * (2.2 + 1.6 * h))
    out += np.sin(2 * np.pi * f * t) * 0.3 * np.exp(-t * 1.2)
    return fade(out * 0.5, 0.001, 0.1)


def flute(m, dur, slide_from=None):
    t = tt(dur)
    f = np.full(len(t), hz(m))
    if slide_from is not None:
        k = np.clip(t / 0.07, 0, 1)
        f = hz(slide_from) * (1 - k) + hz(m) * k
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.25) / 0.3, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    tone = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    breath = bp(rng.standard_normal(len(t)), 1200, 6000) * 0.05
    env = np.clip(t / 0.06, 0, 1) * np.clip((dur - t) / 0.12, 0, 1)
    return (tone + breath) * env * 0.35


def saw_stack(m, dur, cut=1800, voices=(0.995, 1.0, 1.006)):
    t = tt(dur)
    out = np.zeros(len(t))
    for d in voices:
        f = hz(m) * d
        for h in range(1, 14):
            if f * h > 9000:
                break
            out += np.sin(2 * np.pi * f * h * t + rng.uniform(0, 6.28)) / h
    out = lp(out, cut)
    env = np.clip(t / 0.4, 0, 1) * np.clip((dur - t) / 0.5, 0, 1)
    return out * env * 0.06


def bass(m, dur):
    t = tt(dur)
    ph = (hz(m) * t) % 1
    tri = 2 * np.abs(2 * ph - 1) - 1
    return fade(lp(tri, 900) * np.exp(-t * 1.2) * 0.5, 0.004, 0.05)


def tick():
    t = tt(0.05)
    return fade(bp(rng.standard_normal(len(t)), 2500, 9000) * np.exp(-t * 140) + np.sin(2 * np.pi * 2100 * t) * np.exp(-t * 120) * 0.5, 0.0003, 0.01)


def heartbeat():
    t = tt(0.28)
    return fade(np.sin(2 * np.pi * 48 * t) * np.exp(-t * 18), 0.004, 0.05)


def bell():
    t = tt(6.0)
    out = np.zeros(len(t))
    for ratio, a, d in [(0.5, 0.6, 0.35), (1.0, 1.0, 0.6), (1.19, 0.5, 0.8), (1.56, 0.4, 1.0), (2.0, 0.35, 1.3), (2.74, 0.25, 1.8), (3.76, 0.15, 2.4)]:
        out += a * np.sin(2 * np.pi * 220 * ratio * t) * np.exp(-t * d)
    return fade(out * 0.25, 0.002, 0.3)


def chime(m):
    t = tt(2.5)
    out = sum(np.sin(2 * np.pi * hz(m) * r * t) * a * np.exp(-t * d) for r, a, d in [(1, 1, 1.4), (2.76, 0.35, 3), (5.4, 0.15, 5)])
    return fade(out * 0.25, 0.001, 0.2)


def anvil():
    t = tt(0.8)
    out = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in [(1180, 7), (1730, 9), (2630, 12), (3950, 16)])
    hit = bp(rng.standard_normal(len(t)), 2000, 9000) * np.exp(-t * 80)
    return fade(out * 0.18 + hit * 0.3, 0.0005, 0.05)


def noise_riser(dur, lo=300, hi=6000):
    t = tt(dur)
    n = rng.standard_normal(len(t))
    out = np.zeros(len(t))
    steps = 24
    for k in range(steps):
        a, b = int(k * len(t) / steps), int((k + 1) * len(t) / steps)
        fc = lo * (hi / lo) ** (k / steps)
        out[a:b] = lp(n[a:b], fc)
    return out * (t / dur) ** 2 * 0.35


def boom():
    t = tt(3.0)
    f = 38 * (1 + 0.8 * np.exp(-t * 6))
    return fade(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.3) * 0.9, 0.002, 0.3)


def wind(dur):
    t = tt(dur)
    n = lp(rng.standard_normal(len(t)), 700)
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * t / 7.3)
    return n * swell * np.clip(t / 2, 0, 1) * np.clip((dur - t) / 2, 0, 1) * 0.12


def cluster(dur):
    out = sum(saw_stack(m, dur, cut=1400) for m in (50, 51, 57, 58))
    t = tt(dur)
    return out[: len(t)] * (t / dur) ** 1.5 * 2.2


# ------------------------------------------------------------------ more instruments (one palette per kind of scene)
def arp(m, dur=0.18):
    t = tt(dur)
    f = hz(m)
    out = sum(np.sin(2 * np.pi * f * h * t) / h for h in (1, 3, 5, 7, 9) if f * h < 12000)
    return fade(lp(out, 2600) * np.exp(-t * 14) * 0.35, 0.002, 0.02)


def ekick():
    t = tt(0.35)
    f = 48 * (1 + 2.2 * np.exp(-t * 40))
    return fade(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9), 0.001, 0.03)


def hat(open_=False):
    t = tt(0.25 if open_ else 0.05)
    n = bp(rng.standard_normal(len(t)), 7000, 16000)
    return fade(n * np.exp(-t * (12 if open_ else 80)) * 0.35, 0.0005, 0.01)


def sub(m, dur):
    t = tt(dur)
    return fade(np.sin(2 * np.pi * hz(m) * t) * 0.6, 0.01, 0.05)


def choir(m, dur, vowel="ah"):
    raw = saw_stack(m, dur, cut=5000, voices=(0.992, 0.997, 1.0, 1.004, 1.009)) / 0.06
    f1, f2 = (700, 1150) if vowel == "ah" else (320, 800)
    out = bp(raw, f1 - 120, f1 + 120) + 0.6 * bp(raw, f2 - 150, f2 + 150) + 0.15 * lp(raw, 400)
    t = tt(dur)
    env = np.clip(t / 0.6, 0, 1) * np.clip((dur - t) / 0.7, 0, 1)
    return out[: len(t)] * env * 0.09


def brass(m, dur):
    raw = saw_stack(m, dur, cut=6000) / 0.06
    t = tt(dur)
    k = np.clip(t / 0.25, 0, 1)
    out = lp(raw, 700) * (1 - k) + lp(raw, 2800) * k
    env = np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.15, 0, 1)
    return out[: len(t)] * env * 0.05


def musicbox(m):
    t = tt(1.6)
    return fade((np.sin(2 * np.pi * hz(m) * t) + 0.3 * np.sin(2 * np.pi * hz(m) * 4.01 * t) * np.exp(-t * 6)) * np.exp(-t * 2.8) * 0.28, 0.001, 0.1)


def pizz(m):
    t = tt(0.35)
    out = sum(np.sin(2 * np.pi * hz(m) * h * t) / h * np.exp(-t * (9 + 4 * h)) for h in range(1, 6))
    return fade(out * 0.5, 0.001, 0.05)


def glass(m):
    t = tt(3.0)
    return fade((np.sin(2 * np.pi * hz(m) * t) + 0.25 * np.sin(2 * np.pi * hz(m) * 2.98 * t)) * np.exp(-t * 1.1) * 0.16, 0.003, 0.3)


def woodblock():
    t = tt(0.08)
    return fade(np.sin(2 * np.pi * 900 * t) * np.exp(-t * 70) * 0.6, 0.0005, 0.01)


def tremolo(m, dur):
    t = tt(dur)
    return saw_stack(m, dur, cut=2200)[: len(t)] * (0.6 + 0.4 * np.sin(2 * np.pi * 12 * t)) * 1.4


# ------------------------------------------------------------------ harmony
CH = {"Dm": (50, [62, 65, 69]), "Bb": (46, [58, 62, 65]), "A": (45, [57, 61, 64]), "Eb": (51, [58, 63, 67]),
      "F": (41, [60, 65, 69]), "C": (48, [60, 64, 67]), "Gm": (43, [58, 62, 67]), "Cm": (48, [60, 63, 67])}
RISE = ["Dm", "Bb", "F", "C"]
CYBER = ["Dm", "Bb", "Gm", "A"]
BRIGHT = ["Bb", "F", "C", "Dm"]
ANTHEM = ["F", "C", "Dm", "Bb"]
ROGUE = [62, 63, 69, None, 70, 69, 63, None]
HOOK = [(74, 2), (77, 1), (79, 1), (81, 3), (79, 1), (77, 2), (76, 1), (74, 1), (72, 2), (74, 2)]


def play_hook(bar, gain=1.0, inst="flute", octave=False):
    pos, prev = 0, None
    for m, d in HOOK:
        t0 = T(bar) + pos * BEAT / 2
        dur = d * BEAT / 2 + 0.05
        if inst == "flute":
            add(flute(m, dur, slide_from=prev if prev and abs(prev - m) <= 3 else None), t0, gain, 0.25, verb=0.45)
        else:
            add(brass(m - 12, dur), t0, gain * 1.3, 0.1, verb=0.4)
        if octave:
            add(flute(m - 12, dur), t0, gain * 0.6, -0.2, verb=0.4)
        prev = m
        pos += d


def play_rogue(bar, gain=0.8, speed=1.0, inst=koto):
    for i, m in enumerate(ROGUE):
        if m is not None:
            add(inst(m), T(bar) + i * BEAT / 2 / speed, gain, -0.35)


def cyber(bar, prog=CYBER, kick=True, hats=True, octave=0, stutter=False, gain=1.0):
    """The theme for every demo shot: arpeggiator, electro kick, sub."""
    root, notes = CH[prog[bar % 4]]
    seq = [notes[0], notes[1], notes[2], notes[1] + 12, notes[2], notes[1], notes[0] + 12, notes[2]]
    for s in range(16):
        if stutter and s % 4 == 3:
            continue
        add(arp(seq[s % 8] + octave), T(bar, s / 4), 0.5 * gain, 0.3 if s % 2 else -0.3, verb=0.2)
    if kick:
        for b in range(4):
            add(ekick(), T(bar, b), 0.9 * gain, 0, verb=0.05)
    if hats:
        for s in range(8):
            add(hat(s % 2 == 1), T(bar, s / 2 + 0.25), 0.5 * gain, 0.4)
    add(sub(root - 12, BAR), T(bar), 0.5 * gain, 0, verb=0.0)
    for m in notes:
        add(saw_stack(m, BAR + 0.2, cut=900), T(bar), 0.45 * gain, 0, verb=0.3)


def taiko_groove(bar, gain=1.0):
    for b in [0, 1.5, 2, 3, 3.5]:
        add(taiko(), T(bar, b), 0.7 * gain * (1.0 if b in (0, 2) else 0.6), 0, verb=0.25)
    for s in range(16):
        add(shime(), T(bar, s / 4), (0.2 if s % 2 else 0.1) * gain, 0.35 if s % 4 else -0.2, verb=0.1)


# ------------------------------------------------------------------ the arrangement, scene by scene (SCORE.md)
# 1. City (0-4.7 s): wind, a low drone, a slow flute phrase
add(wind(12), 0, 1.0, 0, verb=0.1)
add(saw_stack(38, 5.5, cut=500), 0, 1.6, 0, verb=0.3)
for i, (m, d) in enumerate([(62, 1.2), (65, 0.6), (63, 1.6)]):
    add(flute(m, d + 0.2), 0.4 + sum(x[1] for x in [(62, 1.2), (65, 0.6), (63, 1.6)][:i]), 0.6, 0.2, verb=0.6)

# 2. The landing (5.0 s) and the eyes: one deep hit, a heartbeat, harmonics
add(taiko(big=True), T(2), 1.1, 0, verb=0.5)
for bar in (2, 3):
    for b in (0, 0.45, 2, 2.45):
        add(heartbeat(), T(bar, b), 0.9, 0, verb=0.05)
    add(saw_stack(38, BAR + 0.3, cut=450), T(bar), 1.4, 0, verb=0.3)
for k, m in enumerate((74, 81, 86)):
    add(glass(m), T(2, 2 + k), 0.6, 0.3, verb=0.6)

# 3. The chase (bars 4-7): fast koto sixteenths in D with the flat second, shime, taiko
for bar in range(4, 7):
    pat = [62, 63, 69, 63, 62, 69, 70, 69] if bar % 2 == 0 else [62, 63, 67, 63, 62, 67, 69, 67]
    for s in range(16):
        add(koto(pat[s % 8], 0.4), T(bar, s / 4), 0.32, -0.4, verb=0.15)
        if s % 2 == 1:
            add(shime(), T(bar, s / 4), 0.3, 0.3)
    for b in (0, 1.5, 2, 3.5):
        add(taiko(), T(bar, b), 0.6, 0)
    add(bass(38, BAR), T(bar), 0.6)
add(taiko(big=True), T(6), 0.8, 0, verb=0.4)   # the leap

# 4. The breach (bars 7-9): a cluster swell into the hit, then a falling koto run
add(cluster(2.5), T(7), 1.0, 0, verb=0.4)
add(taiko(big=True), T(8), 1.1, 0, verb=0.5)
add(boom(), T(8), 0.7)
for k, m in enumerate([81, 77, 75, 74, 70, 69, 65, 63, 62]):
    add(koto(m, 0.8), T(8, 0.5 + k * 0.25), 0.4, -0.2, verb=0.4)

# 5. The hours (bars 9-12): a music box over the ticking clock, in G minor, no drums
MB = [79, 74, 70, 74, 75, 74, 70, 67]
for bar in range(9, 12):
    for b in range(4):
        add(tick(), T(bar, b), 0.55, 0.5, verb=0.1)
        add(heartbeat(), T(bar, b + 0.1), 0.5, 0, verb=0.05)
    for e, m in enumerate(MB):
        add(musicbox(m - (bar - 9)), T(bar, e / 2), 0.7, -0.2, verb=0.5)
    root, notes = CH[["Gm", "Cm", "Gm"][bar - 9]]
    for m in notes:
        add(saw_stack(m - 12, BAR + 0.3, cut=900), T(bar), 0.8, 0, verb=0.4)

# 6. The walk-around (bars 12-14): sneaky pizzicato and woodblock
add(saw_stack(38, 0.4, cut=2500), T(12), 3.0)
for bar in (12, 13):
    play_rogue(bar, 0.9, speed=1.0, inst=pizz)
    for b in (0.5, 1.5, 2.5, 3.5):
        add(woodblock(), T(bar, b), 0.5, 0.4)
    add(bass(38 if bar == 12 else 39, BAR), T(bar), 0.4)

# 7. Doubt (bars 14-16): low dissonance and a riser, then a beat of silence
add(noise_riser(4.3), T(14), 1.2, 0, verb=0.3)
for m in (38, 45, 50, 51):
    add(saw_stack(m, 4.3, cut=2200), T(14), 1.0, 0, verb=0.5)

# 8. The guardian (bars 16-20): o-daiko, choir, brass hook, in Rise
add(taiko(big=True), T(16), 1.3, 0, verb=0.6)
add(boom(), T(16), 1.0)
for bar in range(16, 20):
    root, notes = CH[RISE[bar % 4]]
    for m in notes:
        add(choir(m - 12, BAR + 0.4), T(bar), 1.0, 0, verb=0.6)
    add(taiko(big=True), T(bar), 0.7, 0, verb=0.5)
    add(taiko(), T(bar, 2.5), 0.6)
    add(bass(root - 12, BAR), T(bar), 0.5)
play_hook(16, 1.0, inst="brass")
play_hook(18, 0.9, inst="flute")

# 9. Observe (bars 20-22): the choir holds, a soft pulse starts
for bar in (20, 21):
    for m in CH[RISE[bar % 4]][1]:
        add(choir(m - 12, BAR + 0.4, "oo"), T(bar), 0.8, 0, verb=0.6)
    for s in range(8):
        add(shime(), T(bar, s / 2), 0.15 + 0.03 * s, 0.2)
add(noise_riser(2.5, 600, 5000), T(21), 0.5)

# 10. Demo A (bars 22-25): the cyber theme
for bar in range(22, 25):
    cyber(bar)

# 11. The seal (bars 25-27): fast taiko rolls, the slap on beat 3, brass stabs
for s in range(10):
    add(taiko(), T(25, s / 4), 0.35 + 0.05 * s, 0)
add(taiko(big=True), T(25, 2), 1.1, 0, verb=0.5)
for m in (62, 65, 69):
    add(brass(m - 12, 0.5), T(25, 2), 1.5)
taiko_groove(26, 0.9)
add(taiko(big=True), T(26, 2), 1.0, 0, verb=0.5)  # the rogue thrown back

# 12. Demo B (bars 27-29): cyber, an octave up
for bar in (27, 28):
    cyber(bar, octave=12)

# 13. Red team (bars 29-31): tremolo strings over E flat, syncopated shime, fuzzy bass
for bar in (29, 30):
    for m in (51, 58, 63):
        add(tremolo(m, BAR + 0.2), T(bar), 0.9, 0, verb=0.4)
    for b in (0, 0.75, 1.5, 2.5, 3.25):
        add(shime(), T(bar, b), 0.4, 0.3)
    add(np.tanh(bass(39, BAR) * 4) * 0.2, T(bar), 1.0)

# 14. Demo C (bar 31): cyber, stuttered
cyber(31, stutter=True)

# 15. The forge (bars 32-34): anvil on every beat, low taiko, a humming choir
for bar in (32, 33):
    for b in range(4):
        add(anvil(), T(bar, b), 0.8, 0.1, verb=0.4)
    add(taiko(big=True), T(bar), 0.7)
    for m in (38, 45):
        add(choir(m + 12, BAR + 0.4, "oo"), T(bar), 0.9, 0, verb=0.5)

# 16. Demo D (bars 34-37): cyber, calm (no kick)
for bar in range(34, 37):
    cyber(bar, kick=False, hats=bar > 35)

# 17. The sealed room (bars 37-39): a sub pulse, glass tones, nothing else
for bar in (37, 38):
    for b in range(4):
        add(sub(38, 0.25), T(bar, b), 0.8)
    for k, m in enumerate((86, 81, 88, 79)):
        add(glass(m), T(bar, k), 0.5, 0.4 - 0.25 * k, verb=0.7)
add(taiko(big=True), T(37, 2), 0.8)        # old lock breaks
add(anvil(), T(38, 0.2), 1.0, 0.2, verb=0.6)  # the blade breaks on the new lock

# 18. Demo E (bars 39-42): cyber, brighter chords
for bar in range(39, 42):
    cyber(bar, prog=BRIGHT)

# 19. Rollout (bars 42-44): an accelerating build, one stab per gate
for bar in (42, 43):
    for s in range(8 if bar == 42 else 16):
        add(taiko(), T(bar, s / (2 if bar == 42 else 4)), 0.45, 0)
for k, (bar, beat) in enumerate(((42, 1), (43, 0), (43, 3))):
    for m in CH[["Dm", "F", "A"][k]][1]:
        add(brass(m, 0.6), T(bar, beat), 1.4 + 0.2 * k)
    add(chime(81 + 3 * k), T(bar, beat), 0.8, 0.2, verb=0.6)

# 20. Demo F (bars 44-46): cyber at full, a riser into the triumph
for bar in (44, 45):
    cyber(bar, prog=BRIGHT, octave=12 if bar == 45 else 0)
add(noise_riser(2.5), T(45), 0.9)

# 21. Triumph (bars 46-48): hook on brass and flute, choir, big taiko
for bar in (46, 47):
    taiko_groove(bar, 1.1)
    for m in CH[RISE[bar % 4]][1]:
        add(choir(m - 12, BAR + 0.4), T(bar), 1.0, 0, verb=0.6)
play_hook(46, 1.1, inst="brass", octave=True)
add(taiko(big=True), T(46), 1.2, 0, verb=0.6)
add(boom(), T(46), 0.8)

# 22. Demo SQLi (bars 48-50): cyber
for bar in (48, 49):
    cyber(bar)

# 23. The bell (bars 50-52): a solemn drone and the temple bell
for bar in (50, 51):
    add(saw_stack(38, BAR + 0.5, cut=600), T(bar), 1.4, 0, verb=0.4)
    add(choir(50, BAR + 0.4, "oo"), T(bar), 0.8, 0, verb=0.6)
add(bell(), T(51), 1.0, 0, verb=0.7)

# 24. Lanterns (bars 52-56): no drums, koto arpeggios, flute solo, one chime per lantern
for bar in range(52, 56):
    root, notes = CH[RISE[bar % 4]]
    for m in notes:
        add(saw_stack(m - 12, BAR + 0.5, cut=1100), T(bar), 0.9, 0, verb=0.5)
    for s in range(8):
        add(koto(notes[s % 3] + (12 if s >= 4 else 0), 1.0), T(bar, s / 2), 0.25, -0.45, verb=0.4)
for k, bar in enumerate((52, 53, 54)):
    add(chime(86 - 2 * k), T(bar), 1.0, 0.3 - 0.3 * k, verb=0.8)
play_hook(52, 0.7)
play_hook(54, 0.7)
add(noise_riser(2.5), T(55), 0.8)

# 25. The trials (bars 56-62): an anthem in brighter chords, hits on each result
for bar in range(56, 62):
    taiko_groove(bar, 1.0)
    root, notes = CH[ANTHEM[bar % 4]]
    for m in notes:
        add(choir(m - 12, BAR + 0.4), T(bar), 0.9, 0, verb=0.5)
    add(bass(root - 12, BAR), T(bar), 0.5)
for bar in (56, 58, 60):
    add(taiko(big=True), T(bar), 1.1, 0, verb=0.6)
    play_hook(bar, 1.0, inst="brass" if bar != 58 else "flute", octave=bar == 60)
add(boom(), T(56), 0.7)

# 26. Outro (bars 62-68): the last hit, a pad that fades, a solo flute ending on D
add(taiko(big=True), T(62), 1.3, 0, verb=0.8)
add(boom(), T(62), 1.0)
for m in (50, 57, 62, 65):
    add(saw_stack(m, 15.0, cut=1200), T(62), 1.2, 0, verb=0.6)
add(flute(74, 4.0, slide_from=76), T(63), 0.8, 0.2, verb=0.6)
add(flute(62, 6.0), T(65), 0.6, 0.2, verb=0.7)
add(bell(), T(64), 0.5, 0, verb=0.8)
add(wind(16), T(62), 0.8)

# ------------------------------------------------------------------ room and master
ir_t = tt(2.2)
ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 2.6)
ir = lp(ir, 5000) * 0.035
size = 1 << int(np.ceil(np.log2(N + len(ir))))
wet = np.fft.irfft(np.fft.rfft(VERB, size) * np.fft.rfft(ir, size), size)[:N]
wet_r = np.fft.irfft(np.fft.rfft(VERB, size) * np.fft.rfft(np.roll(ir, 331), size), size)[:N]
L += wet
R += wet_r

end = int(DUR * SR)
fade_n = int(4 * SR)
for ch in (L, R):
    ch[end - fade_n:end] *= np.linspace(1, 0, fade_n)
    ch[end:] = 0
mix = np.stack([L[:end], R[:end]], 1)
mix = np.tanh(mix / np.max(np.abs(mix)) * 1.6) * 0.89
mix /= np.max(np.abs(mix)) / 0.89

out = Path(__file__).parent / "out"
out.mkdir(exist_ok=True)
with wave.open(str(out / "score.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("wrote", out / "score.wav", f"{DUR:.1f} s")
