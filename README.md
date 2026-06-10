# Morning Row — a low-poly sculling study

An interactive 3D simulation of a single scull on a quiet lake, in a muted
low-poly style. Built with [Three.js](https://threejs.org/) and Vite.

## Run it

```sh
npm install
npm run dev      # then open the printed localhost URL
```

## Controls

| Input | Action |
| --- | --- |
| **Hold space** | Row continuously (~24 strokes/min) |
| **Tap space** | Take a single stroke (taps queue through the recovery) |
| Drag / scroll | Orbit and zoom the camera |
| **R** | Reset distance and speed |
| Touch + hold | Row (mobile) |

## How it works

Everything is procedural — no external models.

- **Stroke engine** ([src/stroke.js](src/stroke.js)) — a catch → drive →
  finish → recovery state machine with real rowing sequencing (legs, then
  back swing, then arms on the drive; reversed on the recovery). The drive
  always completes; the recovery pauses at "easy oars" unless space is held.
  Hull speed integrates a thrust profile against linear + quadratic drag,
  landing at a realistic ~2:05 /500 m split at rate 24.
- **Inverse kinematics** ([src/rower.js](src/rower.js)) — analytic two-bone
  IK ([src/util.js](src/util.js)). Hips ride the sliding seat, ankles are
  fixed in the stretcher shoes, and the solver finds the knees; hands track
  the oar handles (computed from the oarlock pin, sweep angle, and blade
  depth) and the solver finds the elbows. Includes the sculling crossover —
  left hand passes over right mid-stroke.
- **Oars** ([src/boat.js](src/boat.js)) — sweep, blade depth, and feathering
  are all driven by the stroke phase: blades square and bury for the drive,
  feather flat and skim on the recovery.
- **World** ([src/world.js](src/world.js)) — the boat stays at the origin
  while the shoreline scrolls past on tiled banks; the water is a custom
  shader (sine displacement + flat facet normals from screen-space
  derivatives) whose wave field scrolls with boat distance. Splash particles
  on blade entry/exit, drips on the recovery, and drifting oar puddles.

Dev console handle: `__sim.pause('drive', 0.5)` freezes the cycle at any
phase for inspection; `__sim.play()` resumes.
