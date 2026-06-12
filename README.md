# Morning Row — a low-poly sculling game

A 3D rowing mini game: a single scull on a quiet meandering river, in a
muted low-poly style. Built with [Three.js](https://threejs.org/) and Vite.

## Run it

```sh
npm install
npm run dev      # then open the printed localhost URL
```

## Playing

Pick a goal on the opening card — just row, a distance, or a time, with
optional repeats and rest periods — then row. Course markers float every
100 m and pop as you pass; a flagged gate marks the finish of each
interval. A summary card shows distance, time and average split.

| Input | Action |
| --- | --- |
| **Hold space** | Row continuously (~24 strokes/min) |
| **Tap space** | Take a single stroke (taps queue through the recovery) |
| Drag / scroll | Orbit and zoom the camera |
| **R** | Back to the goal card |
| Touch + hold | Row (mobile) |
| Connect monitor | Drive strokes from a real rower over Bluetooth FTMS |

With a Fitness Machine Service rower connected (PM5 and most smart rowers;
Chrome/Edge only), real strokes drive the avatar, your stroke rate paces
the animation, and your pace carries the boat.

## How it works

- **Stroke engine** ([src/stroke.js](src/stroke.js)) — a catch → drive →
  finish → recovery state machine with real rowing sequencing (legs, then
  back swing, then arms on the drive; hands away before the slide on the
  recovery). Hull speed integrates a thrust profile against linear +
  quadratic drag, landing at a realistic ~2:05 /500 m split at rate 24.
- **The rower** ([src/rower.js](src/rower.js)) — Quaternius' CC0
  ["Ultimate Modular Women"](https://quaternius.com/packs/ultimatemodularwomen.html)
  casual character, retargeted at runtime: spine bones take the lean and
  hunch, and analytic two-bone IK ([src/util.js](src/util.js)) aims her
  arms at the oar handles and her legs at the foot stretcher, with bend
  axes tracking the IK pole so knees and elbows stay honest.
- **Oars** ([src/boat.js](src/boat.js)) — sweep, blade depth, and feathering
  are all driven by the stroke phase: blades square and bury for the drive,
  feather flat and skim on the recovery.
- **The river** ([src/course.js](src/course.js)) — a meandering centreline
  integrated from a heading function; bank scenery (mounds, groves,
  rocks, instanced reed beds) streams in deterministic chunks ahead of the
  boat and is disposed behind. Water is a custom shader with world-anchored
  waves ([src/world.js](src/world.js)).

Dev console handle: `__sim.pause('drive', 0.5)` freezes the cycle at any
phase for inspection; `__sim.play()` resumes; `__sim.step()` advances a
single frame.

## Credits

Rower character from
[Quaternius — Ultimate Modular Women](https://quaternius.com/packs/ultimatemodularwomen.html)
(CC0), with animations stripped and the skeleton posed procedurally.
