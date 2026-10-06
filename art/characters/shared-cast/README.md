# Shared cast source

All four characters use the approved June skeleton, rowing animation, limb weights, joined-finger hands, hips, shorts and shoes. June is copied byte for byte. Kai has a fixed flatter chest; Sol and Ada retain June’s approved chest. Chest choice and palettes are internal authoring settings in `cast.json`, with no runtime morph or animated scale.

Kai, Sol and Ada retain their accepted illustrated heads. Head scale uses facial landmarks rather than hair height. A welded neck bridge joins each head to June above source height 0.302. Local posterior-neck fairing smooths that join without moving the protected body. Skin and singlet colours are material settings; face detail materials remain separate.

## Rebuild

From the repository root, with Blender and the project’s Node dependencies available:

```sh
blender -b --factory-startup --python-exit-code 1 --python scripts/shared-cast-build.py
node scripts/shared-cast-validate.mjs
```

Required inputs are `cast.json`, `head-provenance.json`, the three `*-head.glb` files here, and the approved `june.blend`, `june.glb` and `layout.json` in `validation/reconstruction/fresh-rig/`. The build uses Blender’s bundled NumPy. It needs no inference cache or historical candidate body. `scripts/shared-cast-extract-heads.py` is an optional donor-refresh operation and is not part of a normal rebuild.

The approved June source is canonical. `shared-body.blend` is its editable byte-identical copy, refreshed by the build. The generated `june.blend`, `kai.blend`, `sol.blend` and `ada.blend` contain editable meshes and the native rig. Edit reproducible settings or head inputs before rebuilding; rebuilding replaces generated exports. Raw `<id>.glb` outputs retain dual-quaternion metadata and the exact two-second `RowingCycle`.

## Evidence and delivery

`manifest.json` records source/donor hashes, raw export hashes, fixed variants, palettes and validation results. All characters use June’s boat fit: catch angle 1, seat finish 0.36, pin height 0.45, inboard length 0.8 and grip radius 0.02.

`validation/characters/shared-cast/` contains:

- `<id>/source-identity.json` for the three head variants: unchanged protected body positions and weights; welded neck-band boundary and nonmanifold edge checks. June is verified by byte identity in the manifest.
- `<id>/export-identity.json`: exact exported protected positions, weights and triangles, plus every time/value in all 96 June animation tracks.
- `<id>/report.json`: 1,201-pose native rowing validation for each raw export.
- `body-report.json`: independent 161-pose arm/leg and arm/chest intersection checks, with input blend hashes.
- `<id>/review/`: neutral rest/head front, profile and reference-angle renders. Kai and Ada’s final profile images include the last neck fairing; final animated scene review belongs to installation validation.

The final source package has zero protected body position/weight deltas, zero neck-band boundary or nonmanifold edges, exact animation tracks, and passing native and collision checks. Kai’s bounded chest sculpt changes 1,071 source vertices; all other June body surfaces outside the neck replacement remain unchanged. The head joins retain stylised faceting and are ready for review at application scale.

A clean rebuild from the staged source snapshot reproduced all four raw GLB
hashes exactly; see `validation/characters/shared-cast/rebuild-report.json`.

Installation and lossless delivery compression are separate steps owned by `scripts/install-shared-cast.mjs`. Historical separate-body candidates remain under `art/characters/candidates/` for provenance; they are not build dependencies for this cast.
