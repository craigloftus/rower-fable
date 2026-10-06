# Sol — refined native candidate

Refinement complete, 6 October 2026. The original illustration's swept fringe,
tapered jaw, compact almond eyes, quiet forehead and cheek planes now read in the
exported model. Fitted lids surround convex eyes with dark brown irises and
separate pupils. Shallow lip volumes follow the original restrained smile.
The neck remains continuous, with its chin-to-throat space intact.

The complete original simplified hands remain. A local outside-knuckle rounding
moves the source by at most 1.1 mm (1.98 mm after rig placement); it does not replace
the hand, thumb branch or distal finger ends. Hip weights now follow the angle
around each measured femoral head, removing the earlier posterior shelf and
large concentric folds while retaining the source body. Bent shorts and joined
fingers retain normal angular anatomy.

This is an interpretation of a single illustration. Its practical likeness and
motion are improved; final runtime integration belongs to the parent task.
No production asset, shared runtime, June, Kai or Ada file was changed by this
Sol pass. No installation, commit or push was made.

## Exact deliverables

`sculpt.blend` is the editable standing sculpt with the original concept packed.
`head-authored.blend` retains the authored head planes. `standing.glb` is the exact
binding source. `sol.blend` contains the editable Preserve Volume rig;
`sol.glb` has 47,329 triangles, 32 bones including grip markers, and one two-second
`RowingCycle` sampled at 120 Hz. It uses dual-quaternion skinning extras, fixed limb
lengths, no scale/morph animation, and one uniform 1.8× placement. Binding moves
no source vertices. The editable, uncompressed export is 7,803,340 bytes.

Final GLB SHA-256:
`b7d09d6124052d6d6794bf6c2f496214ffa3afe4f27f93c5efbd0b7caf808f47`.

`delivery.json` records the exact files, compact inputs, evidence and raw
provenance. `anatomy.json` contains measured landmarks and retained-hand fitting.
The boat must use these five values, also recorded in `delivery.boatFit`:

```json
{"catchAngle":0.9,"seatFinish":0.3,"pinY":0.48,"inboard":0.75,"gripRadius":0.02}
```

`sol-fit.mjs` delegates to the shared `fitNativeRowingPose` with those values.

## Final checks and review

All final build steps exited zero. Native validation generated witnesses before
Blender parity ran; all reports refer to the final export above.

| Check | Result |
| --- | --- |
| Native poses | 1,201; grip anchor error ≤0.6502 mm |
| Fixed lengths / material seams | ≤0.0034 mm / ≤0.00075 mm error |
| Seat contact | 0.398–0.423 mm clearance; ≥560 mm² within 3 mm |
| Sole contact / drift | 0.393–0.401 mm clearance / ≤0.0075 mm drift |
| Rest knee plane | 0 rad deviation from the source lateral axis projected perpendicular to each measured limb |
| Surface collisions | Zero tested arm/leg and arm/chest intersections in 161 poses |
| Full grip surfaces | 21 poses; deepest penetration 0.2564 mm; thumb-edge ratios 1.3856 L / 1.3502 R |
| Blender / Three.js DQ parity | 3,520 witnesses across 5 poses; ≤0.0746 mm, below the unchanged 0.1 mm limit |
| Source landmarks | All 26 limb/hand pivots inside the closed sculpt |

Final evidence is under `validation/characters/sol/`: `after/`, `after-head/`,
`final-review/`, and `browser-candidate-*.png`. Views include original-reference
angle, front/profile/rear, clay, five stroke phases and close hands. The finished
cycle retains the smooth posterior contour, planted feet and seat support.

Headless Chromium used 914×412 CSS pixels at native DPR 2.625, with a 2399×1081
drawing buffer. Whole-scene draws/triangles were 57/24,116 for old Sol,
69/48,073 for June and 62/49,625 for this candidate. Median/p95 synchronous
JS/submission costs were 0.10/0.30, 0.30/0.40 and 0.30/0.40 ms. These are not
sustained GPU frame times or evidence of Pixel 8 thermal performance.

## Reproduction and curation

Local TRELLIS.2 MLX used the full original and its unchanged head crop
`[365,6,595,322]`, at 1024 resolution, 12 steps, 100,000 target faces and 2048
texture size. The two runs took about 322 and 2,452 seconds. Raw source hashes
and settings are retained in `source-provenance.json`; raw inference binaries,
occupancy caches, logs and `.blend1` backups are not curated inputs.

The compact colour cloud is 474,579 bytes. Replaying it produces a byte-identical
standing export. Equal-distance texture samples move some material-cut points
by at most 0.0283 mm source relative to the full cloud; the compact layout is the
authoritative input used for final rendering and validation. No baked lighting
or fixed eye highlights are shipped.

To regenerate the standing source from curated inputs, use the existing geometry
Python at `~/.local/share/rower-tools/TripoSR/.venv/bin/python` for Python geometry
scripts and background Blender for the Blender scripts, in this order:

1. Blender `sol-refine-body.py`; geometry Python `sol-refine-hands.py`.
2. Geometry Python `sol-refine-head.py`; Blender `sol-retopologize-head.py`.
3. Geometry Python `sol-assemble.py`, `sol-colour-surface.py` and `sol-check-landmarks.py`.
4. Blender `sol-save-sculpt.py`; then `node scripts/sol-build-native.mjs`.
5. Regenerate final views with `sol-review.py`, `sol-render-rig.py` and
   `sol-browser-review.mjs` (local Vite port 5194), then run
   `python3 scripts/sol-write-delivery.py`.

The native build alone reuses the retained standing surface. Curated inputs
contain the closed body/head facets, head plane mask, refined head, compact
colour cloud and saved provenance; no raw inference cache is required.

Useful source-specific corrections are recorded in authoring comments: preserve
the actual spine rest quaternion; limit arm regions by source y as well as x;
use measured thumb branch/extents; test all three edges of every triangle touching
the thumb. Full exported-surface tests remain authoritative over fitter subsets.
Only final evidence folders should be presented as current. Earlier `*-study`,
`refined-face`, `hand-rounded`, `closed-head` and `assembled-head` folders are
intermediate diagnostics.
