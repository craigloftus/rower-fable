# June reference and reconstruction studies

`../june-concept.png` is the authoritative design. Generated turnaround views
are working references; they do not override the original if proportions drift.

## Visual acceptance

Compare the actual mesh under neutral light, at the original camera angle and
from front, profile and rear. Check the untextured mesh as well as colour.

- Preserve the tapered adult face, broad cheek planes, narrower almond eyes,
  small closed smile and subtle freckles.
- Model the asymmetric swept hair as thick overlapping masses. The bun is a
  folded knot with an irregular silhouette, rather than a sphere with grooves.
- Keep the athletic shoulder, ribcage, waist and pelvis proportions. Surface
  triangles should describe those forms, rather than decorate a generic body.
- Preserve the singlet silhouette, cream stripe and charcoal fitted shorts.
- Preserve knee direction, planted shoes, seat contact and closed oar grips
  throughout the complete stroke after rigging.

Passing animation checks does **not** establish likeness. Neither does a good
generated reference image: the review must show exported geometry.

## Studies

- `june-head-turnaround.png`: generated front, profile and three-quarter head
  reference. The prompt and source are recorded in `prompts.json`.
- `june-body-turnaround.png`: generated front, profile and rear full-body
  reference, with the exact prompt in `body-prompt.json`.
- `june-planes.blend`: rejected landmark-mesh experiment. Its mask-like face,
  eye projection and hair shape are not acceptable for the runtime model.
- `../../../validation/reconstruction/`: image-to-3D evaluation outputs and
  logs. These are deliberately outside `public/characters`.

## Reconstruction tools

- [TRELLIS.2](https://github.com/microsoft/TRELLIS.2): authenticated generation
  produced a full-body GLB and a separate head from the original image. A third
  generation exhausted the free ZeroGPU quota; further evaluation uses local MLX.
- [TRELLIS.2 MLX port](https://github.com/lyonsno/trellis2mlx): installed at
  `~/.local/share/rower-tools/trellis2mlx`, pinned to
  `52ef63856218c35833275b4d7f2413015ca52a9d`.
  DINOv3 ViT-L/16 LVD-1689M access is verified. Native MLX image features were
  finite, took 4.19 seconds and peaked at 2.66 GB on this M1 Max. The complete
  local pipeline has now exported textured GLBs at both 512 (8 steps) and 1024
  (12 steps). Wall times were 527.3 seconds including the first background-model
  download, and 991.1 seconds respectively. No cloud GPU was required.
- [TripoSR](https://github.com/VAST-AI-Research/TripoSR): isolated local evaluation
  in `~/.local/share/rower-tools/TripoSR`, using `scripts/reconstruct-local.py`.
  The adapter uses scikit-image for marching cubes and PyTorch MPS for inference.
  PyTorch 2.5.1 needs `PYTORCH_ENABLE_MPS_FALLBACK=1` for its bicubic positional
  embedding resize. Mesh winding, vertex normals and nonmetal materials are
  explicitly exported for glTF.

## Earlier evaluation results

The three TripoSR studies remain rejected: the body, original head crop, and
larger turnaround head crop were too soft and noisy in geometry and colour.

TRELLIS captures stronger cheek, hair and body planes. Its original full-body
face is weak. Larger-reference local heads are available at 512 and 1024, but
likeness still differs in the eyes, nose and bun.
The first neutral assembly also had an unfinished neck join and ragged garment
boundaries. Those raw outputs are retained as construction references.

`june-trellis-rig.blend` is the earlier experimental rowing binding, which
failed seat contact and showed shoulder/neck deformation defects. It is
superseded by `june-final-rig.blend`. The final review export uses
`validation/reconstruction/rigged/june.glb`; its validation report includes the
exact GLB hash so an older passing report cannot authorize a newer export.

Open `/rower-fable/validation/reconstruction/index.html` for neutral mesh/clay
comparisons and `/rower-fable/validation.html?baseline=reconstruction` for the
previous game character beside the final reconstructed rowing model.

Reproduction scripts:

- `scripts/reconstruct-character.py`: authenticated hosted inference, reading
  the Hugging Face credential store. Respect the service's exhausted free quota.
- `scripts/download-trellis-weights.py`: downloads pinned model snapshots to the
  user's standard Hugging Face cache, outside this repository.
- `scripts/reconstruct-trellis-local.py`: runs the installed MLX pipeline with
  native DINOv3 conditioning.
- `scripts/clean-trellis-study.py`, `scripts/assemble-trellis-study.py`, and
  `scripts/rig-reconstructed-june.py`: experimental cleanup, assembly and binding.

No account keys are stored in the project. The image-to-3D models are build-time
tools, not browser dependencies.

The automatic voxel-remesh experiment in `trellis-local-clean-head` is rejected:
it collapsed the open generated shell into thin fragments. The winding repair
corrected 3,194 reversed triangles in the 512 study but did not make it a closed,
consistently oriented mesh. Raw exports are retained. These diagnostics are
reasons for further topology work, not evidence that a game-ready asset exists.

## Approved assembly: neck pass

The user selected `trellis-assembled` as the shape baseline. The neck overlap
has been replaced with a section-to-section surface. June's head is lowered
0.012 source units and moved forward 0.006, shortening and straightening the
neck in profile. The rest of the body and the head's shape are preserved.

`scripts/validate-neck-join.py` checks the exported seams: all 348 boundary
edges match their source edges, with zero gap and consistent bridge winding.
This validates the neck pass, not unrelated pre-existing reconstruction defects
or the experimental rowing binding. The result has 159,990 triangles.

`june-assembled-template.blend` is the editable template for the faceted
rebuild, with the neck vertices welded. Reproduce it with
`scripts/assemble-trellis-study.py` in the reconstruction Python environment,
then `blender -b --python scripts/save-june-template.py`.

## Final faceted build

The approved assembly supplies the silhouette and anatomy; the original
illustration supplies the warm skin, copper hair, terracotta singlet, cream
stripe and ivory shoes. Eyelids, almond eye surfaces, brows, lips and freckles
are authored geometry. Material borders cut the actual surface, and all cut
edges are made conforming before skinning. No generated texture is shipped. The skin uses intentional cheek/ear pigment
and freckles only; arms and legs have one base colour. Hair uses a uniform
copper base. Eye reflections come from a convex glossy surface and scene
lighting, with no fixed highlight geometry. The chest stripe is clipped
against separate horizontal planes so its edges stay level.
This is still an interpretation of the illustration: the face and hair do not
match it one for one. Numerical geometry checks do not measure that likeness.

The closed underlying sculpt has 10,126 triangles. The coloured export needs
additional coplanar triangles for material borders, facial details and shared
deforming seams. `validation/reconstruction/june-final/palette.json` records
the current per-material and total counts: 45,777 standing triangles and
45,777 in the new rowing export. The rig retains every source triangle. This supersedes the earlier
20,000–30,000 triangle working target; a clean seam takes precedence over that
target. The source assembly has 159,990 triangles.

Editable masters:

- `june-final-topology.blend`: closed, simplified body geometry.
- `june-final-sculpt.blend`: standing colour sculpt, with the approved guide
  in a hidden collection and the original concept packed into the file.
- `validation/reconstruction/fresh-rig/june.blend`, relative to the project root,
  is the new rig master. Installation copies it to `art/characters/june.blend`.
- `june-final-rig.blend` and `june-rowing-components.blend` are historical
  inputs to the previous rig. The current build does not use them.

## Fresh rig, September 25

The fresh rig binds the whole approved `june-final/mesh.glb` at one uniform
scale of 1.8. It keeps the original simplified hands, wrists, shorts, face,
colours and body proportions. The bind checks that no vertex moves after
that placement. It does not add fingers, replacement garments, seam strips,
per-bone stretching or body morphs.

The skeleton follows the sculpt's joint locations. Clavicles allow the
shoulders to move; three forearm bones distribute twist. The existing joined
finger shape bends at its knuckle and tip. Two joints bend the existing
thumb at its base and knuckle. The palm frame follows the inward-facing broad surface of
that sculpt, with its hand bone ending at the knuckles. Thumb weights follow the complete thumb branch, including its tip, and
exclude the inner edge of the finger block. The grip fixes palm contact while a wrist
solve follows the forearm; it no longer imposes a tilt from the torso lean.
Heat weights from the closed sculpt supply the lower body.
Anatomical weight regions keep the ribcage on the torso and localize bending
at shoulders, elbows and wrists. Shared material-boundary positions receive
identical weights. Thigh influence stops at the pelvis so it cannot drag the
singlet hem down. Feet remain rigid and the pelvis fits the seated surface.

`src/rowing-fit.js` fits June's stroke and boat setup to her proportions. It
reduces compression and layback, stops the finish before the arms enter the
torso, and coordinates hands-away with the body swing. Lower oarlocks, shorter
inboard lengths and narrower grips are applied to both the boat and the bake.
The riggers and shafts follow those dimensions, while blade height still
determines oar pitch. Other characters retain their own existing setup.

Blender uses Preserve Volume. `src/volume-skinning.js` implements the matching
dual-quaternion skinning in Three.js, including normals and CPU measurements.
The GLB declares this through `extras.skinning = "dualQuaternion"`. Call
`prepareCharacterSkinning(scene)` after loading it. A generic glTF viewer uses
linear skinning and will not reproduce the joint shapes seen in this app.
Lighting and materials continue to use Three.js's standard shader. This
shader modification targets WebGLRenderer; the app does not cast character
shadow maps or use WebGPU.

Run `npm run june:build`, review `validation.html?baseline=native`, then run
`npm run june:install`. The build always reuses the approved sculpt. It needs
Node and Blender on PATH, with no inference service or extra Python packages.
The other four characters keep their existing rigs.

The active build in `scripts/build-final-june.mjs` runs:

1. `sample-june-native.mjs` generates fixed-length skeletal poses from the
   same stroke and oar functions as the boat.
2. `bind-june-native.py` binds the original mesh and exports it.
3. `fit-june-seating.mjs` fits pelvis height and a small roll to both sitting
   contacts. The bind script then bakes those fitted poses.
4. `validate-native-june.mjs` measures the exported skin at 1,201 times. It
   checks bone lengths, rotation continuity, seams, grips, seat and sole
   contact, and motion under the boat's parent transform.
5. `validate-june-grip.mjs` checks the hand triangle interiors against the
   handles, including contact proximity, penetration, palm-facing direction and
   palm contact at every sampled pose, plus thumb/web edge stretch. `check-native-june.py`
   compares the exported deformation with Blender.
   `validate-body.py -- --native-june` checks arm/leg and arm/torso triangles
   at 161 poses, including the hands. Regions come from the sculpt coordinates
   rather than the weights being tested.
6. `render-final-june.py` renders the portrait from this rig. Installation
   checks the validated hashes before copying the GLB, portrait and blend.

Reports live in `validation/reconstruction/fresh-rig/`. Numerical checks do
not replace visual inspection of shoulders, wrists, elbows, waistband, cuffs,
knees and seat throughout the stroke. The review has close-up controls for
these areas and compares against `pre-recovery-fix/june.glb`, before recovery
smoothing. The Thumb detail view shows the inside of the grip. The earlier
`pre-thumb-fix/june.glb`, `pre-palm-fix/june.glb` and `pre-refinement/june.glb`
baselines are retained. `render-june-rig.py` produces
repeatable front, side and hand renders. The optional `fit-june-grip.mjs` and
`fit-june-grip.py` study fits the retained hand to a handle with rigid joint
rotations; the Python study needs NumPy and SciPy. Its contact objective is
only a fitting aid and must be judged visually before adopting its values.
`fit-june-thumb.py` holds the palm and finger pose fixed while fitting the
thumb; its objective also limits skin stretching and lateral spread.

The [earlier rigging review](../../../validation/rig-audit/README.md) records
why the old bind was replaced. `?baseline=bind` and `?baseline=skinning` remain
historical diagnostics of that asset. The previous bind compressed the chest,
stretched limbs and substituted hands and shorts. Its old contact reports did
not establish acceptable deformation. The source sculpt's authoring scripts
remain available for explicit sculpt edits, outside the rig build.

Rejected local experiments remain outside the active pipeline:
`retopologize-june.py`, `prepare-june-planes.py` and `refine-june-planes.py`
pinched a knee; `craft-june-face.py` reduced likeness; `repair-june-head.py`
did not preserve the head; `seated-june.py` produced unstable hip geometry.
Do not use these as rebuild steps. The rejected projected-colour study was
removed from the viewer because it distorted the eyes and brows.


Recovery uses a continuous handle sweep with matched velocity and acceleration
at its internal join, overlapping body swing and slide, and a smooth crossover
lift. Blade extraction is timed to retain finger/knee clearance. The 121 drive
bone samples are identical to the accepted pre-recovery version. Review playback
uses `G.driveDur` and `G.recDur`, rather than giving both phases equal time.
The rebuilt asset passes the 1,201-pose native check, 21-pose grip check, Blender
parity check and 161-pose mesh collision check. The runtime boat retains the
seat, footboard, oarlock and handle contact dimensions during its visual pass.

See [the condensed modelling notes](../../modelling-notes.md) for lessons that
apply beyond June. The boat-only comparison is `validation.html?baseline=boat`.
