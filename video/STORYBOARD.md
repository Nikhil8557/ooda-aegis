# OODA-Aegis film: script and storyboard

**Length** 68 bars at 96 BPM. One bar is 2.5 s, so the film runs 170 s. Every shot starts on a bar line.
**Look** Flat paper-cut layers, no gradients or glows. Six colours only:
`#1D1015` night, `#421B29` far hills, `#702B40` sky, `#A64C61` accents, `#D28B96` lamps and the rogue's eyes, `#F1DDE0` moon, guardian, text.
**Type** Titles in Cinzel (an engraved, Trajan-style face like a fantasy title). Captions in Cormorant Garamond italic, written in a storyteller's voice. Payloads in JetBrains Mono. The exact caption text lives in `scene.js`.
**Characters** See `CHARACTERS.md` for the model sheet, rig and motion library.
**Demo** The dashboard is never mocked. Every demo shot is the real dashboard replaying a recorded live run, seeked frame by frame.

## Characters

| Name | Silhouette | Colours | Reads as |
|---|---|---|---|
| The rogue | Hunched, hooded, two knot tails on the hood, carries a forged scroll | Body night, tails and sash accent rose, eyes lamp pink | The attacker |
| The guardian | Tall, straight, wide conical hat, long scarf that moves in the wind | Body night, scarf and eyes moon white | OODA-Aegis |

## Shot list

| # | Bars | Time (s) | Camera | Action | Caption | Music cue |
|---|---|---|---|---|---|---|
| 1 | 0-2 | 0-5 | Extreme wide, slow push in | Moon, rooftops, the fortress on the right with lit windows, labelled DocVault | 2:14 a.m. A company's document service is running as usual | Wind, low drone on D, koto motif |
| 2 | 2-4 | 5-10 | Low angle on a roof edge | The rogue drops in and lands on the downbeat, then his eyes open | Someone has found a hole in it | Taiko hit on the landing, heartbeat starts |
| 3 | 4-7 | 10-17.5 | Side tracking shot, layers move at different speeds | He runs across the roofs and leaps a gap on bar 6 | No password. Only a strange file name: `../../../../etc/passwd` | Stealth ostinato: koto eighths, shime ticks |
| 4 | 7-9 | 17.5-22.5 | Medium shot, push in, 4° tilt | He holds up the forged scroll, the gate slides open, stolen scrolls fly out: passwd, .env, customers | The service hands over its own system files, then its secrets | Dissonant swell, hit on bar 8 |
| 5 | 9-12 | 22.5-30 | Wide, locked off | The moon turns into a clock and spins. Far away a person sleeps while a phone lights up. The rogue keeps carrying scrolls out | Someone has to wake up, find the bug, write a fix, test it and ship it / That takes hours, and the leak keeps going | Clock ticks, strings rise, heartbeat speeds up |
| 6 | 12-14 | 30-35 | Medium at the gate | A guard pins a paper rule "block ../" on the gate. The rogue changes the scroll to `....//....//etc/passwd` and walks through | A quick blocking rule? Change the string and walk around it | Stab, sneaky koto line |
| 7 | 14-16 | 35-40 | Extreme close-up on the rogue's eyes, then black | He narrows his eyes. Cut to black on the last beat | And a fix written by AI is not safe just because it looks right | Riser, then one beat of silence |
| 8 | 16-20 | 40-50 | Very low angle, crane up the tower | The guardian stands on the tallest tower against the moon. His eyes open on the drop. Title, then subtitle | OODA-Aegis / An agent that defends a live service on its own / By Nikhil Kumar | Drop: full taiko, flute hook |
| 9 | 20-22 | 50-55 | Over the guardian's shoulder | Thin threads run from every window to the tower. One thread turns pink when a file leaks | It reads every reply the service sends. A system file in a reply is enough | Groove starts |
| 10 | 22-25 | 55-62.5 | Demo | Dashboard: the leak, then Llama 3.2 3B triages it | Llama 3.2 3B names the attack, path traversal, in about two seconds / This is a recorded live run on a laptop | Groove |
| 11 | 25-27 | 62.5-67.5 | Medium, quick push | The guardian leaps down and slaps a seal on the gate. The rogue's next strike bounces off | It writes a blocking rule, checks that real users still pass, and loads it at the proxy | Taiko fill into the seal hit |
| 12 | 27-29 | 67.5-72.5 | Demo | Virtual patch tab, then the log: 403 for the attack, 200 for real users | Contained 5.3 seconds after the leak. The attack gets 403, real users get 200 | Groove |
| 13 | 29-31 | 72.5-77.5 | Wide at the gate | The guardian splits into three shadows, each tries a disguise against his own seal. Two slip through | Then it attacks itself. Its own rule misses some variants, so the code has to change | Off-beat shime, rising bass |
| 14 | 31-32 | 77.5-80 | Demo | Red team tab: 13 variants | 13 variants. A blocking rule alone can't hold | |
| 15 | 32-34 | 80-85 | Low angle in the forge | The guardian hammers a new lock on an anvil, sparks on every beat | Llama 3.1 8B states what the code must guarantee, then rewrites the handler | Anvil hits on the beat |
| 16 | 34-37 | 85-92.5 | Demo | Code repair view: the diff | The fix keeps only the file name, so nothing outside the documents folder can be opened | |
| 17 | 37-39 | 92.5-97.5 | Inside a sealed room, no windows | A captured shadow strikes the old lock, which breaks, then the new lock, which holds | In a sealed sandbox with no network, the real exploit must break the old code and fail on the new one | Tense pulse |
| 18 | 39-42 | 97.5-105 | Demo | Sandbox proof view | Every variant, the service's own tests and real requests must pass. The model's own test can't approve anything | |
| 19 | 42-44 | 105-110 | Tracking along a long wall | Three gates take the new lock one by one: 10%, 50%, 100% | The new version takes 10%, then 50%, then all traffic, checked at every step | Three rising stabs |
| 20 | 44-46 | 110-115 | Demo | The traffic bar moves to the new release | If a check fails, traffic goes straight back to the old version | Build |
| 21 | 46-48 | 115-120 | Medium, then wide | The rogue tries the original scroll again. The gate hands back an empty scroll. He leaps away into the night | Healed 42.6 seconds after the leak. The original attack is replayed and gets nothing | Hook, full and bright |
| 22 | 48-50 | 120-125 | Demo | SQL injection run, code repair view | SQL injection: a parameterised query, healed in 46 seconds | Groove |
| 23 | 50-52 | 125-130 | Medium | The rogue knots an endless rope around the gate. The guardian cannot prove a fix, so he rings a bell | When no fix passes the gate, the agent changes nothing and calls a human | Temple bell |
| 24 | 52-56 | 130-140 | Slow pan across three lanterns | Lanterns light one per bar: Llama 3.2 3B, Llama 3.1 8B, Muse Glimmer 30B | Built on Meta's open-weight models. Your code and data never leave your machine | Breakdown: drums out, flute solo |
| 25 | 56-62 | 140-155 | Locked card | Three results appear on bars 56, 58 and 60 | none (the card is the text) | Final chorus, hits on each result |
| 26 | 62-68 | 155-170 | Pull back from the tower | The guardian on the tower, moon behind. Title, author, link. Fade to night | OODA-Aegis, by Nikhil Kumar | Final hit, drone fades |
