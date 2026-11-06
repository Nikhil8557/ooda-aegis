# OODA-Aegis film: score

Tempo **96 BPM**, 4/4, one bar = **2.5 s**, **68 bars = 170 s**. Key **D minor**, with the flattened second (E flat) from the Japanese *in* scale for the rogue's music.
All sounds are synthesised in `music.py` with numpy, so the music is original.

## Themes

| Theme | Notes | Who it belongs to |
|---|---|---|
| Rogue motif | D4 E♭4 A4 . B♭4 A4 E♭4 . (koto) | The attacker: sly, uses the flat second |
| Guardian hook | D5 . F5 G5 A5 . . G5 / F5 . E5 D5 C5 . D5 . (flute) | OODA-Aegis: rises, then lands home |
| Clock | wood tick on every beat | Time passing while the leak runs |

## Harmony

| Name | Chords, one per bar | Used in |
|---|---|---|
| Night | Dm · Dm · B♭ · A | Intro, prowl |
| Dread | Dm · E♭ · Dm · A | The hours, the rule failing |
| Rise | Dm · B♭ · F · C | Guardian, counter-attack, finale |

## Cue sheet

Each kind of scene has its own sound, so the ear never hears the same loop twice. Ninja scenes use traditional instruments, and every demo shot uses one electronic theme (the "cyber" cue) in a different variation.

| Bars | Time (s) | Scene | Cue |
|---|---|---|---|
| 0-2 | 0-5 | The city | Wind, low D drone, a slow flute phrase |
| 2-4 | 5-10 | The landing | One deep taiko hit on 5.0 s, heartbeat, glassy harmonics as his eyes open |
| 4-7 | 10-17.5 | The chase | Fast koto sixteenths with the flat second, shime, driving taiko, a hit on the leap |
| 7-9 | 17.5-22.5 | The breach | Cluster swell into a hit on bar 8, then a falling koto run as the scrolls fly |
| 9-12 | 22.5-30 | The hours | A music box in G minor over a ticking clock and a heartbeat, no drums |
| 12-14 | 30-35 | The walk-around | Sneaky pizzicato rogue motif with a woodblock |
| 14-16 | 35-40 | Doubt | Low dissonance and a riser, then one beat of silence |
| 16-20 | 40-50 | The guardian | O-daiko, a full choir, the guardian hook on brass then flute |
| 20-22 | 50-55 | Observe | Choir on "oo", a pulse that builds |
| 22-25 | 55-62.5 | Demo | Cyber: arpeggiator sixteenths, electro kick, sub bass, Dm Bb Gm A |
| 25-27 | 62.5-67.5 | The seal | Taiko rolls, the slap on beat 3 with a brass stab, a hit as the rogue is thrown |
| 27-29 | 67.5-72.5 | Demo | Cyber, an octave higher |
| 29-31 | 72.5-77.5 | Red team | Tremolo strings on E flat, off-beat shime, distorted bass |
| 31-32 | 77.5-80 | Demo | Cyber, stuttered |
| 32-34 | 80-85 | The forge | Anvil on every beat, deep taiko, a humming choir |
| 34-37 | 85-92.5 | Demo | Cyber, calm, no kick |
| 37-39 | 92.5-97.5 | The sealed room | A sub pulse and glass tones only. A hit when the old lock breaks, a clang when the blade breaks |
| 39-42 | 97.5-105 | Demo | Cyber in brighter chords (Bb F C Dm) |
| 42-44 | 105-110 | Rollout | Accelerating taiko, one brass stab and chime per gate, each a step higher |
| 44-46 | 110-115 | Demo | Cyber at full, riser |
| 46-48 | 115-120 | Triumph | The hook on brass with the flute an octave down, choir, big taiko |
| 48-50 | 120-125 | Demo | Cyber |
| 50-52 | 125-130 | The bell | Low drone, choir, the temple bell |
| 52-56 | 130-140 | Lanterns | No drums: koto arpeggios, flute solo, one chime per lantern |
| 56-62 | 140-155 | The trials | An anthem in F C Dm Bb, choir and taiko, a hit on each result |
| 62-68 | 155-170 | Outro | Last hit, a fading pad, a distant bell, solo flute ending on D |

## Instruments

- **Taiko and o-daiko:** a sine that drops in pitch fast, plus a short noise slap on the skin.
- **Shime:** a tight high drum, a short burst of band-passed noise with a 600 Hz body.
- **Koto:** Karplus-Strong plucked string, slightly bright, panned left.
- **Flute:** a sine with breath noise, slow vibrato and a short slide into each note, panned right.
- **Bass:** a low triangle wave following the chord root.
- **Pad and strings:** detuned saw stacks, low-passed.
- **Cyber theme:** a square-wave arpeggiator, an electro kick, closed and open hats, a sine sub.
- **Choir:** detuned saws through vowel formants ("ah", "oo"). **Brass:** saws whose filter opens on each note.
- **Music box, pizzicato, glass, woodblock, tremolo strings:** short plucked or struck tones for the quieter scenes.
- **Clock:** a short high wooden click. **Heartbeat:** two soft low sine thumps.
- **Bell:** inharmonic partials with a long decay.
- **FX:** wind (filtered noise), risers (noise rising in pitch), a sub boom on the drops.
