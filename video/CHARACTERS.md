# OODA-Aegis film: characters and motion design

The two ninjas are drawn by a 2D skeleton rig in `scene.js`. Every pose is a set of joint angles, every action is a timed list of key poses, and the film samples them with easing. This page is the model sheet the code follows.

## Model sheet

| | The rogue (the attacker) | The guardian (OODA-Aegis) |
|---|---|---|
| Height | 7 heads, about 205 px at scale 1 | 7.5 heads, about 215 px, longer legs |
| Silhouette | Hood with a pointed back, two knot tails, a sack on his back, hunched | Wide conical hat, a long scarf, a sword across the back, upright |
| Colours | Body night, wraps and tails dusty rose, eyes lamp pink | Body night, scarf moon white, eyes moon white |
| Attitude | Low and sideways, leads with the head, quick and sly | Still and vertical, leads with the chest, moves only when he must |
| Signature move | The sneak: long low strides, arms tucked | The stillness, then one fast decisive action |

## Rig

Root at the pelvis. Spine in two parts (lower spine `lean`, upper chest `chest`), neck, head. Each arm: shoulder, elbow, wrist. Each leg: hip, knee, ankle, with a foot that pivots at the ankle. Limbs are tapered (thick at the joint nearest the body), with rounded joints. The rig finds the lowest point of either foot and places it on the ground, so every crouch and stride bobs the body naturally.

Angles are degrees from straight down. A positive angle means forward, in the direction the character faces. Knees and elbows bend by a positive amount.

## Secondary motion

- **Guardian's scarf** and **rogue's knot tails** are a ten-point chain hanging from the neck. They stream behind in proportion to speed, hang and sway when standing, and ripple with a travelling wave.
- **Guardian's coat tails** flap at the hips at the same speed.
- **Breathing:** the chest rises 2° every two beats when idle.
- **Blinks:** the eye slit closes for 0.12 s every few seconds, never in the same place twice.

## Motion library

| Action | Length | Keys | Notes |
|---|---|---|---|
| Idle | loop, 2 beats | stand, breathe in, stand | Weight shifts slightly to the back leg |
| Sneak (rogue) | 1 stride per beat | contact, down, passing, up | Spine 32° forward, arms tucked, head level |
| Run | 2 strides per beat | contact, down, passing, up | Spine 20°, arms pump against the legs, a short flight phase |
| Leap | 0.9 to 1.2 s | anticipation crouch (20%), take-off extension (30%), tuck (55%), reach (80%), landing (100%) | The body follows a parabola. Landing squashes into a crouch, then a recovery |
| Land | 0.6 s | impact crouch, hold, rise | The impact frame is on the music's downbeat |
| Raise (show the scroll) | 0.5 s | arm swings up past the head with a 0.1 s overshoot | |
| Seal slap (guardian) | 0.4 s | wind-up behind the shoulder, fast push, hold | The slap lands on beat 3 of the bar |
| Strike (rogue) | 0.6 s | wind-up, lunge, follow-through | Bounce-back plays as a hit reaction: spine back 25°, arms thrown |
| Hammer (guardian) | 1 beat | up, hold, down on the beat, recoil | Sparks on the impact frame |
| Pull the bell rope | 1 bar | reach up, pull down with the knees, release | |
| Flee (rogue) | 1.2 s | turn, crouch, leap up and away | |

## Acting notes, by shot

1. City wide. No characters, only lit windows.
2. The rogue drops from above the frame, lands on the downbeat at 5.0 s, holds the crouch, opens his eyes, then rises.
3. He runs the roofs at full speed, leaps the gap on bar 6 and keeps running out of the landing.
4. He stops at the gate, looks both ways, raises the forged scroll. The gate obeys. Stolen scrolls arc into his sack.
5. Small in the wide shot, he runs back and forth carrying files, stopping at the gate each time.
6. He reads the paper rule, tilts his head, flips the scroll and sneaks through.
7. Close-up: his eye narrows slowly. Cut to black on the last beat.
8. The guardian stands still on the tower against the moon. His scarf moves before he does. His eyes open on the drop.
9. Over his shoulder, he watches the threads of light. His head turns towards the pink one.
11. He leaps down in one arc, lands, slaps the seal on beat 3. The rogue strikes and is thrown back.
13. He sends three rose-coloured shadows of himself at his own seal. One bounces off, two slip through. He lowers his head.
15. In the forge he hammers on every beat, with a held wind-up before each hit.
17. A captured shadow strikes the old lock (it breaks), then the new one (the blade breaks).
19. He runs along the wall as each gate takes the new lock.
21. The rogue tries the scroll again, gets "not found", looks at it, then flees in a leap.
23. The rogue ties the gate in rope. The guardian looks, decides, and pulls the bell rope.
26. The guardian on the tower again, now at rest. Scarf in the wind. Fade.
