# Ada refined candidate

Completed 6 October 2026. The final face, catch and recovery silhouettes, rear
surface and retained grip have passed independent visual review. Modelling is
complete; runtime integration and compressed delivery remain with the parent
agent. This package has not been installed. Production assets and shared runtime
were not edited by the Ada modeller.

Ada follows `art/characters/ada-concept.png`: mature tapered face, cheek and mouth
creases, fuller smiling lips, close silver curls, warm brown skin, lean arms,
defined waist and broader pelvis. Her kit is muted blue, cream, charcoal and ivory.
The final pass quiets the forehead planes, reduces the oversized central curl,
cleans the brow boundaries and replaces flat eyes with recessed convex globes,
thick lid rims, upper iris occlusion and a narrow lower sclera. The mature smile
and nasolabial folds remain intact.

This is a three-dimensional interpretation of one illustration, with inferred
unseen surfaces. Joined fingers and compressed shorts retain stylized angular
forms. The final reviews found no remaining modelling defect worth a broader
change; numerical passes alone did not determine visual acceptance.

## Deliverables

Paths below are relative to this directory.

- `sculpt.blend`: coloured standing surface, hidden connected closed authoring
  surface and packed original illustration.
- `head-authored.blend`: editable head after local plane authoring and reduction.
- `standing.glb`: exact surface bound to the rig, without compression.
- `ada.blend`: editable Preserve Volume rig with 241 keys at 120 Hz.
- `ada.glb`: one two-second `RowingCycle`, 32 bones including grip markers,
  dual-quaternion extras, no animated scale or morph.
- `anatomy.json`: measured joints, palm frames, grip fits and soles.
- `delivery.json`: final asset, input, script and evidence hashes, plus `boatFit`.

The editable GLB has **50,522 triangles, 147,572 vertices and 8,289,752 bytes**.
Flat body/head normals duplicate vertices. Lossless delivery compression reduces
transfer size, not vertex-processing cost. Retain this uncompressed master.

SHA-256: `5cd07c2c66b6c631766c3d77b98a6d6bf521e1c20e62c43ad9fcba33531f52d4`.

## Final checks

Evidence is in `validation/characters/ada/`. `after/` and `after-head/` contain
front, profile, rear, three-quarter and original-angle colour/clay views.
`final-review/` covers catch, drive, finish and recovery, including rear, waist,
seat, feet and both grip surfaces. `browser-candidate-*.png` shows the final DQ
export in its boat at native DPR 2.625. `index.html` is the interactive viewer.

| Check | Result |
| --- | --- |
| Native poses, including transformed boat parent | 1,201; grip error at most 0.650 mm |
| Fixed lengths / material seams | At most 0.00022 / 0.00074 mm error |
| Seat contact | 0.399–0.408 mm clearance; at least 472 mm² within 3 mm |
| Sole contact / drift | 0.392–0.401 mm clearance / at most 0.0084 mm |
| Arm/leg and arm/chest intersections | Zero across 161 poses |
| Complete retained-hand checks | 21 poses; deepest penetration 0.468 mm |
| Thumb/web edge stretch | 1.349 left / 1.360 right |
| Palm contact | Left gap at most 0.370 mm; right penetration at most 0.454 mm |
| Blender/Three.js parity | 3,740 witnesses over five poses; at most 0.0352 mm error |
| Anatomy and placement | All 26 source pivots inside; uniform 1.8 scale; binding moves no vertices |

Native validation ran before Blender parity. Every authoritative report refers
to the final export. No acceptance threshold was loosened during refinement.

The neutral-boat desktop comparison uses 914×412 CSS pixels at DPR 2.625,
2399×1081 drawing buffer, and 300 synchronous calls. Old Ada / June / candidate
used 57 / 69 / 63 draws and 23,692 / 48,073 / 52,818 scene triangles. Median call
costs were 0.10 / 0.30 / 0.20 ms; p95 was 0.20 / 0.40 / 0.30 ms. This is JavaScript
and submission timing, not proof of sustained GPU frame rate or Pixel 8 thermal
performance. Full-river and compressed-installed profiling belongs to delivery.

## Construction and fit

Local TRELLIS.2 MLX processed the unchanged original full image and head crop
`[383, 16, 604, 303]`, at 1024 resolution and 12 steps. Raw outputs are recorded
by hash in `source-provenance.json`; they are not required by the final rebuild.
The full-body face and blocky hair were superseded by the detailed head.

Closed source surfaces retain Ada's anatomy. A measured 6.3° rigid yaw aligns
her shoulders. Local closure repairs cheek/jaw pockets without erasing age folds.
The final forehead crown follows measured source depth; its maximum local
change is 0.02845 head-source units, about 5.5 mm after placement. The head is
reduced from 15,000 to 7,200 triangles after plane authoring. A narrow neck join
preserves the concave throat and chin. The assembled closed sculpt has 34,330
triangles before conforming colour boundaries and eyes.

Source texture samples define hair/brow layout; clean materials remove baked
shadows and fixed glints. Globe normals cross iris/pupil colour boundaries
continuously, with restrained specular. The packed 751,986-byte colour cloud
replays byte-identically. Packing can resolve equal-distance sample ties
differently; all final assets and checks use the compact cloud.

Hip weights follow angle around Ada's measured femoral heads. This removes the
anterior catch pit and posterior ripples without reshaping the broad pelvis.
Actual seated roll is −4.460° to −4.026°, with exact loop closure and at most
1.18°/s normalized-clip derivative. The existing source-specific fit guard remains
0.11 radians. A wider mitt-joint blend and bounded distal-finger rounding
(maximum 1.98 mm at rig scale) soften sharp edges. The measured thumb branch and
complete joined fingers remain; the full exported hand validator is authoritative.

The runtime must use exactly this `delivery.boatFit`:

```json
{"catchAngle":0.90,"seatFinish":0.30,"pinY":0.48,"inboard":0.75,"gripRadius":0.02}
```

## Rebuild and curation

Run from the repository root, using existing background Blender and the existing
TripoSR Python environment for NumPy/SciPy/trimesh geometry only. There is no
TripoSR inference, package install, paid service or new inference in this pass.

```sh
node scripts/ada-build-sculpt.mjs
node scripts/ada-build-native.mjs
blender -b --factory-startup --python-exit-code 1 --python scripts/ada-render-rig.py -- final-review
node scripts/ada-browser-review.mjs
python3 scripts/ada-write-delivery.py
```

The sculpt rebuild needs only the original concept, anatomy, retained
`faceted-surface.ply`, `head-faceted-surface.ply`, and `head-colour-layout.npz`.
The writer reads immutable source provenance instead of raw inference files.
The browser review expects Vite on port 5194. Use `ada-review.py` to refresh
neutral views after a sculpt change, then regenerate the manifest.

Curate the manifest's assets, compact inputs, authoring and final evidence.
Exclude raw inference GLBs, dense texture samples, occupancy arrays, logs,
`.blend1` backups and duplicate study folders. Earlier reconstruction scripts
record provenance; `ada-build-sculpt.mjs` is the cache-independent active path.
