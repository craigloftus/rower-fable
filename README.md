# Morning Row — a low-poly sculling game

A 3D rowing mini game: a single scull on a quiet meandering river, in a
muted low-poly style. Built with [Three.js](https://threejs.org/) and Vite.

## Run it

```sh
npm install
npm run dev      # then open the printed localhost URL
```

## Playing

Pick a goal on the opening card — just row, a distance, a time (with
optional repeats and rest periods), or a **plan** session — then row.
Course markers float every 100 m and pop as you pass; a flagged gate marks
the finish of each interval. A summary card shows distance, time and
average split.

The plan is British Rowing's
[Go Row beginner training plan](https://www.britishrowing.org/indoor-rowing/go-row-indoor/):
eight weeks, two sessions a week, building from 1:00 efforts to a 2000 m
row. Pick a week and session and the game walks you through it — a stage
strip across the top shows the shape of the session (taller segments are
harder), chimes mark every stage change (rising into work, higher still
for high intensity, falling into rest, with 3-2-1 ticks before work
resumes), and the HUD shows the current stage, what's left of it, and the
guide stroke rate for the target intensity.

| Input | Action |
| --- | --- |
| **Hold space** | Row continuously (~24 strokes/min) |
| **Tap space** | Take a single stroke (taps queue through the recovery) |
| Drag / scroll | Orbit and zoom the camera |
| **R** | Back to the goal card |
| Touch + hold | Row (mobile) |
| Connect monitor | Drive strokes from a real rower over Bluetooth FTMS |

With a Fitness Machine Service rower connected (PM5 and most smart rowers;
Chrome/Edge only), real FTMS stroke/power events drive the avatar, your
stroke rate paces the animation, and your pace carries the boat. Starting a
row also asks the browser to keep the screen awake where supported.

The card reopens where you left it — the same goal mode, that mode's target,
repeats and rest, and the plan week and session
([src/prefs.js](src/prefs.js), `localStorage` key `morningrow.cfg`).

## How it works

- **Stroke engine** ([src/stroke.js](src/stroke.js)) — a catch → drive →
  finish → recovery state machine with real rowing sequencing (legs, then
  back swing, then arms on the drive; hands away before the slide on the
  recovery). Hull speed integrates a thrust profile against linear +
  quadratic drag, landing at a realistic ~2:05 /500 m split at rate 24.
- **The rower** ([src/rower.js](src/rower.js)) — four custom Blender characters,
  each with a rowing-specific deform rig and one baked `RowingCycle` clip.
  The stroke phase samples the clip directly (drive = seconds 0–1,
  recovery = 1–2), so Bluetooth timing and pauses cannot drift from the oars.
  June retains the approved sculpt's simplified grip hands. The rig bake and boat share
  [src/oar-pose.js](src/oar-pose.js), including physical crossover height.
- **Character selection** — choose Kai, June, Sol or Ada on the opening
  card. Portraits use the original generated illustrations. June is the default;
  saved Mira selections migrate to June. The loaded
  choice is saved as `character` in `morningrow.cfg`; existing workout
  preferences are preserved.
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

## Capturing a real machine (temporary)

The stroke model is hand-tuned; the **debug** row on the setup card exists to
replace that with measurements. With a monitor connected, `record ble` saves
every Bluetooth notification the machine sends, verbatim, and prompts for
somewhere to put the file. Drop that file back on the setup card and it plays
back through the same code path a live machine drives — the sim runs off real
strokes with no machine attached.

The file ([src/recorder.js](src/recorder.js)) is deliberately raw, so a
decoding mistake today does not cost the capture:

```json
{ "format": "morningrow.ble-recording", "version": 1,
  "device": { "name": "PM5 430123456" }, "durationMs": 184320,
  "characteristics": { "2ad1": { "name": "rower_data", "samples": 368 } },
  "samples": [ { "t": 998.4, "c": "2ad1", "d": "2c0930000100..." } ] }
```

`t` is milliseconds from the start, `c` the characteristic (16-bit UUIDs in
short form), `d` the payload as hex. Recording widens the subscription beyond
Rower Data to every other stream the machine will notify on, including
Concept2's proprietary rowing service where present — that is where a PM5
publishes its force curve, which standard FTMS has no field for.

To work with a capture ([src/replay.js](src/replay.js)):

```js
__sim.replay.play(rec, { speed: 4 })  // feed it to the sim, optionally faster
__sim.frames(rec)                     // decoded Rower Data as a time series
__sim.catches(rec)                    // catch times, from stroke-counter steps
```

Rower Data arrives at about 2 Hz, so it pins stroke *timing*, rate and pace
but not sub-stroke phase; the force curve, where a machine offers one, is what
would let [src/stroke.js](src/stroke.js)'s thrust profile and drive/recovery
ratio be fitted rather than guessed. Remove the debug row, `src/recorder.js`
and `src/replay.js` once that work has landed.

## Credits

Original comparison character from
[Quaternius — Ultimate Modular Women](https://quaternius.com/packs/ultimatemodularwomen.html)
(CC0), with animations stripped and the skeleton posed procedurally.

Earlier shared-body experiments used [MakeHuman graphical assets](https://github.com/makehumancommunity/makehuman)
(CC0), reshaped and rigged for rowing. Asset URLs and hashes are in
`art/source/manifest.json`; the asset license is included alongside them.


## Character authoring and validation

The four characters share June's approved body, skeleton, skin weights and
rowing animation. Kai, Sol and Ada retain their individually refined heads,
with character-specific skin and top colours. A fixed chest variant is chosen
per character in the source configuration; there is no runtime body morphing.
The opening selector uses the original illustrations and saves the choice locally.

- Editable shared source and configuration: `art/characters/shared-cast/`.
- Losslessly compressed runtime GLBs: `public/characters/`.
- Reusable workflow: [.agents/skills/rowing-character/SKILL.md](.agents/skills/rowing-character/SKILL.md).
- Build commands, validation and limitations: [art/characters/README.md](art/characters/README.md).

Use background Blender and headless Chromium. Rebuild from the approved body
and retained head surfaces, inspect the result, then install the validated cast:

```sh
npm run characters:build
# After visual review:
npm run characters:install
npm run characters:validate
npm test
npm run build
```

For June alone, the background build preserves the approved sculpt and its
simplified hands. It writes review assets and checks the exported animation,
seams, seat contact, collisions and agreement with Blender. Install it separately:

```sh
npm run june:build
npm run june:install
```

This rig build uses Node and Blender on `PATH`. June uses volume-preserving
skinning in Blender and the matching Three.js renderer in `src/volume-skinning.js`.
The active pipeline and rejected experiments are documented in
[art/characters/reference/README.md](art/characters/reference/README.md).

With Vite running, open `/rower-fable/validation.html` for the original/new
comparison, phase scrubber, close-up views and character selector. Add
`?baseline=body` to compare the new anatomical body against the first Blender
version. Use `?baseline=seat` for the seated-support correction and a camera
that follows the slider, or `?baseline=sculpt` for June's detailed sculpt.
Use `?baseline=native` to compare June's staged recovery with the continuous
return. Both retain the original sculpt and corrected grip, and playback uses
the app's actual drive/recovery timing. `?baseline=boat` compares the previous
boat with the refined shell, cockpit, fittings and oars.
The practical lessons are collected in [art/modelling-notes.md](art/modelling-notes.md).
The standing sculpt and original illustration are available at
`/rower-fable/validation/reconstruction/index.html?study=june-final`.
The knee-hinge check covers bone roll, and the seat
check measures the actual exported skin surface and contact area.
`/rower-fable/validation/mobile.html` embeds the real setup screen at phone width.
These review pages are development tools and are not part of the production entry.

## Performance and keeping the screen awake

Rowing targets up to **120 fps** at the device's native pixel density. The
setup/summary background runs at 30 fps, and rendering stops while the page is
hidden. Static scenery is batched in spatial cells; a worker builds upcoming
river chunks so construction does not block rowing. The character geometry,
rig, water shader and materials retain their detail. Text HUD updates run at
10 Hz independently of the animation.

Add `?perf=1` to the app URL for local diagnostics: frame times, CPU rendering
work, asynchronous GPU timings where supported, draw calls, triangle counts,
resource counts and wake-lock status. **Run 60s rowing sample** starts simulated
rowing after a ten-second warm-up; it requires a disconnected monitor.
Real BLE workouts are measured continuously. **Save report** downloads JSON
with the fixed sample and up to 15 minutes of rolling measurements. Switching
tabs interrupts a fixed sample. Nothing is uploaded. The resolution override
and character visibility checkbox are diagnostic controls; normal rendering
uses native resolution and the full character.

```sh
npm test
npx playwright install chromium
# With Vite running on port 5176 (or set PROFILE_URL to its ?perf=1 URL):
node scripts/profile-headless.mjs
```

These tests always use headless Chromium. They do not emulate a phone GPU,
prove 120 Hz presentation on the phone display, or measure phone heat. Reports
and screenshots are saved in `validation/performance/`.

For the Pixel 8, test the HTTPS build in Chrome for 15 minutes with `?perf=1`,
normal brightness, and the phone unplugged. Check frame-time trends at the start
and end, and note battery use and heat. Keep Chrome foreground and leave the
screen untouched beyond its usual auto-lock timeout, including a rest interval.
The status should say **Screen awake**. Switch away and return to verify that
it reacquires; reset/end the workout to verify that it releases. Rejections are
shown with a retry control, and their exact reasons are included in the report.

### Character authoring

The reusable [character workflow](.agents/skills/rowing-character/SKILL.md) records
how to reconstruct the original illustrations, clean the geometry, fit a rig
without reshaping the sculpt, and validate the exported animation. The approved
June, editable character masters, native rig inputs and current validation reports
are versioned. Intermediate reconstruction caches, rejected face experiments and
most historical screenshots remain local; older study-viewer options require
those local artifacts. Build and install a June export with `npm run june:build`
and `npm run june:install`; the installer checks the validated asset hashes.

The selector uses the original concept illustrations, cropped in CSS so the
source art remains unchanged. Model-rendered portraits are separate validation
assets. New character candidates are developed and reviewed one at a time before
replacing a production asset.
