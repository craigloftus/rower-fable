# Kai candidate

Kai is ready for final integration review. The previous palm gaps, folded rear
vest, neck shelf and join ring are resolved. Production assets remain unchanged.
The original `art/characters/kai-concept.png` defines identity and palette; this
is a practical three-dimensional interpretation, not a pixel-identical match.

## Deliverables

Paths are relative to the repository root. `delivery.json` records exact hashes.

- `art/characters/candidates/kai/sculpt.blend`: editable standing sculpt with the original reference packed.
- `art/characters/candidates/kai/head-authored.blend`: source-derived facial plane authoring stage.
- `art/characters/candidates/kai/standing.glb`: standing source used by the rig.
- `art/characters/candidates/kai/kai.blend`: editable fixed-length native rig, Preserve Volume.
- `art/characters/candidates/kai/kai.glb`: two-second `RowingCycle`, 241 keys at 120 Hz, dual-quaternion extras, 32 bones including two grip markers.
- `art/characters/candidates/kai/anatomy.json`: measured anatomical pivots and fitted hand frames.

Final evidence is in `validation/characters/kai/`: `before-rest/` shows the old
model; `after/` and `after-head/` show current front, profile, rear and both
three-quarter angles in colour and clay. `after-head/colour-reference-angle.png`
faces the same direction as the original. `final-review/` covers catch, drive,
finish and two recovery phases, with front, side, rear, waist, hand and sole
views. `browser-candidate-*.png` shows the exact export in headless Three.js DQ
with the fitted boat. `first-candidate/` and `refined-*` are superseded studies.

## Construction and refinement

Local TRELLIS.2 MLX reconstructed the original full image at 1024/12 steps in
403 seconds. Reconstruction of an unchanged original head crop took 1,042
seconds. The original full-body inferred face was rejected. No paid service,
cloud GPU or new installation was used.

The closed source body keeps its original simplified hands. Posterior singlet
folds were removed in the standing sculpt, rather than concealing them with
weights. The separate head retains the reconstructed nose, jaw, ears and curls;
local cheek and forehead planes remove hollow corrugation. Facial decimation
follows that cleanup. The neck bridge is welded and locally faired across the
source cut loops. Convex eyes have fitted eyelid rims, warm irises and separate
pupils; the upper lids occlude them and the lower sclera remains visible. The
restrained mouth has shallow upper and lower lip volume. Flat source-derived
planes define the face and curls. Eye normals follow the globe. No lighting,
eye catchlight or limb shadow is baked into the palette.

Source pivots, sole offsets, thumb extent and palm frames were measured for Kai.
The rig applies one uniform 1.8 scale and rigid placement. Limb lengths remain
fixed; weights match across material seams; no bone scale or morph animation is
used. The grip optimiser measures complete triangles in source-defined palm,
finger and thumb regions and all edges touching the thumb. Final acceptance is
performed on the complete exported mesh with unchanged contact/strain bounds.

Geometry tools use the existing TripoSR virtual environment only for SciPy and
Trimesh, not for inference. Principal authoring scripts are `kai-close-surface.py`,
`kai-facet-surface.py`, `kai-refine-head.py`, `kai-reduce-head.py`,
`kai-assemble.py`, `kai-colour-surface.py` and `kai-save-sculpt.py`.
Curated sculpt inputs total about 1 MB: `faceted-surface.ply`,
`head-faceted-surface.ply`, `head-refined-surface.ply` and
`head-colour-layout.npz`. The 181 KB colour layout contains precisely the 13,224
reference samples used by the final cut surface; replay produces a byte-identical
standing GLB. Raw inference meshes, occupancy volumes and the original 19 MB
colour cloud are provenance-only caches and need not be tracked.

To replay the sculpt, run `kai-refine-head.py` with the geometry Python, then
`kai-reduce-head.py` in background Blender, `kai-assemble.py` and
`kai-colour-surface.py` with the geometry Python, and `kai-save-sculpt.py` in
background Blender. The geometry Python is
`~/.local/share/rower-tools/TripoSR/.venv/bin/python`.
Rebuild and validate the native candidate with `node scripts/kai-build-native.mjs`.
The build stops on any failed native, parity, collision or grip test.

## Validation

The exact reports and asset hashes are linked by `delivery.json`:

- 1,201 native poses, including between keys and a transformed boat parent; no scale/morph tracks, fixed limb lengths and closed material seams.
- 161 collision poses: zero arm/leg or arm/chest triangle intersections.
- Complete grip surface at 21 poses: maximum palm gap 0.309 mm left, 0.294 mm right; finger gaps below 0.409 mm; thumb/web stretch 1.352 and 1.355.
- Seat gap 0.400–0.413 mm; sole clearance 0.388–0.401 mm and sole drift below 0.013 mm.
- Blender/Three.js DQ parity over five poses: maximum positional difference below 0.017 mm.

The final motion views show a smooth rear vest and collar transition without
pointed back flaps. The shorts retain a normal deep fold at the bent hip, with
no inverted or pinched protrusion. The retained joined fingers have angular
tips, but remain complete and curl around the handle without the previous palm
gap. The facial proportions remain an interpretation of the illustration;
this export is a substantial likeness improvement over production Kai and the
first candidate, subject to final in-app review.

Native-DPR headless comparison uses 914×412 CSS pixels at DPR 2.625 (2399×1081
buffer). Scene draw calls are old Kai 57, June 69, candidate 63; scene triangles
are 25,268, 48,073 and 48,584. Synchronous frame-call timings are recorded in
`performance.json`; they measure desktop submission costs, not sustained GPU
performance or Pixel 8 thermal behaviour. The parent task owns full-river
benchmarking and lossless delivery compression. Editable exports remain uncompressed.

## Required runtime fit

Use these exact measured parameters with the shared native rowing profile:

```json
{"catchAngle":1.0,"seatFinish":0.36,"pinY":0.45,"inboard":0.8,"gripRadius":0.02}
```

Finish angle is -0.10. `scripts/kai-fit.mjs` remains the candidate's authoritative
continuous stroke implementation. The boat and animation must use the same
profile; replacing only the GLB would misalign the handles. Shared runtime
installation is owned by the parent task and has not been performed here.
