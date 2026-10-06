# Character pipeline assessment

Blender plus its community MCP integration is a viable authoring route for this
project. MCP provides Python execution and scene inspection; the visual quality
still depends on the geometry, rig and motion we author. We used the actual MCP
`execute_blender_code` tool via `scripts/blender-mcp.py`, with local Blender 5.2.1.
June's later rebuild uses retained TRELLIS.2 reconstruction inputs and local
Blender authoring; the original shared cast was scripted from its references.

## What was wrong with the original

The original CC0 Quaternius character was designed for general animation, then
adapted with runtime bone scaling and analytic IK. Its fingers were curled by
rotating every finger about a guessed local X axis. The hand direction was an
approximation of the forearm direction rather than the oar frame. The solver
had no collision awareness, and the grip path passed through the knees at some
phases. Finally, crossover raised the hand targets without moving the oars.

The original code and model remain available to the development comparison
viewer. They are not a runtime fallback.

## The replacement

Four custom faceted meshes use fixed rowing proportions and a single
`RowingCycle` clip. The shared cast has 15 deform bones plus a root. June's fresh
rig has 30 deform bones and two grip markers. Kai, June, Sol and Ada use the
generated concept images in this directory. Mira was retired from the app in
October 2026; her editable source remains as an archive. Hair geometry, face details, skin and kit distinguish the cast.

The reference images were produced with the built-in image generation tool.
Exact prompts are in `prompts.json`; each requested concept is saved alongside
its `.blend` source. Portraits in `public/characters/` are rendered from the
meshes for validation. The opening selector uses the original concept art,
as requested, independently of these rendered validation portraits.

The shared body now uses MakeHuman's CC0 anatomical topology and skin weights,
reshaped into fixed rowing proportions in an A-pose. Shoulder, hip, elbow and
knee loops blend across joints; there are no overlapping skin-coloured thigh
caps. Kai, Sol and Ada share topology, shoes and a rig, with separate body profiles.
Cleanly cut vest/short boundaries, contoured soles and curved velcro straps
replace the primitive clothing and shoes. The stretcher fits the new soles.

In the shared cast, the right grip is mirrored geometrically, including its wrist target. Fingers
are tapered, closed meshes around the handle; they do not have individually
animated finger bones. This is a rowing-specific rig, not a walking/running rig.

A position-only IK rotation originally rolled the shin roughly 142 degrees at
the catch. Both bones of each limb now use the same anatomical hinge plane in
both the bind pose and the bake. This removes the knee twist and gives the
elbows a consistent bend direction. The exported knee axes are regression-tested.

The shared cast's seat correction reshapes the centre of the shorts into a flatter garment
surface and pins the posterior contact pads to an upright pelvis. The torso
still hinges and the thighs still flex. This prevents standing-body weights
from lifting the buttocks off the slider. The pads have a 0.4 mm rendering
clearance above the shared seat plane, with about 7–12 cm² of contact area per
side. `G.seat` supplies the dimensions to the boat and `rig-layout.json` bake.

June now uses the approved reconstructed anatomy, rebuilt as a closed faceted
surface with clean material cuts, authored facial features, copper hair and
warm vertex colours. Her fresh rig retains every triangle, including the source
shorts and simplified hands. It uses a uniform scale, anatomical joint pivots,
fixed limb lengths and volume-preserving skinning in Blender and Three.js.
Pelvis height and a small roll fit the original sitting surface to the seat.
The rig does not reshape the chest or substitute garments and hands. It is
still a stylized interpretation, not an exact copy of the generated illustration.

Asset provenance and SHA-256 hashes are in `art/source/manifest.json`; the
MakeHuman asset license is preserved in `art/source/LICENSE.ASSETS.md`.
Only its graphical assets are used, not MakeHuman's AGPL application code.

The script samples the app's actual stroke and oar transforms at 120 samples per
phase. It places the feet on the stretcher and solves fixed-length limbs with
stable outward elbow poles. Oarlocks are raised to fit the new seated proportions,
and the catch sweep and slide timing are adjusted for clearance. Both the actual
oars and the grip bones use the same crossover transform.

Blender exports only the active animation, with its first frame shifted to time
zero. Three.js `AnimationMixer.setTime` samples drive at `p` seconds and recovery
at `1 + p` seconds. Animation time is derived from the stroke engine, including
Bluetooth rate changes, rather than from a second clock.

## Validation

`npm run characters:validate` reads the exported GLBs through Three.js and checks
1,201 poses per character, including poses between baked keys. The shared-cast checks assert:

- Exactly one named, two-second clip and finite joint positions.
- Maximum grip-to-oar drift under 2 mm (measured about 1.15 mm).
- Planted feet with drift under 1 mm (measured below 0.001 mm).
- No discontinuous joint or bone-rotation jumps at phase boundaries.
- Actual skinned shorts stay within 1 mm of the seat, with contact area on both
  sides, no seat penetration and no centre drooping below the sitting pads.
- Less than one degree of relative knee-axis twist (measured below 0.001°).
- At least 10 mm arm–leg separation using conservative capsules around both
  arms and both legs (measured about 13.45 mm).

The detailed results are in `validation/character-report.json`.
June's validator measures the original skinned surface with the same
dual-quaternion calculation as the game. It checks fixed bone lengths, shared
seams, seated support, rigid shoes, grip alignment and rotation continuity.
June also has tests for hand/handle surface contact and arm/torso intersections.
Her fitted stroke and boat dimensions are shared by the bake and live scene
through `src/rowing-fit.js`.
The build also compares exported skin positions with Blender's Preserve Volume
output. See `validation/reconstruction/fresh-rig/` for these reports.
`npm run characters:validate-mesh` also evaluates the actual Blender skin at
161 poses per character, including half-key positions, and checks arm/leg
triangle intersections using a BVH plus triangle SAT. It found none; results
are in `validation/body-report.json`. This checks arm/leg surfaces, not all
self-intersections or every part of the boat. The browser comparison adds
visual inspection of catch, finish, crossover and recovery from several angles.
Use `/rower-fable/validation.html?baseline=body` to compare this pass with the
previous Blender body; the plain URL compares with the original runtime rig. This is a stylized animation, not a biomechanics or
rowing-technique simulator; the catch retains some elbow bend.

Preference tests cover existing workout settings, character round-tripping,
unknown IDs, malformed storage and blocked storage. Browser checks cover live
selection, reload persistence, keyboard selection and the phone-width layout.
No live Bluetooth hardware was available for a physical-machine test; the
existing Bluetooth/recording code was preserved.

## Useful sources

- [MakeHuman graphical assets and license](https://github.com/makehumancommunity/makehuman/blob/master/LICENSE.md)
- [Blender MCP source and installation](https://github.com/ahujasid/blender-mcp)
- [Three.js AnimationMixer](https://threejs.org/docs/#api/en/animation/AnimationMixer)
- [Three.js GLTFLoader](https://threejs.org/docs/#examples/en/loaders/GLTFLoader)

The Blender exporter options were checked against the installed 5.2 source;
Three.js animation and loader documentation was consulted through Context7.

## Seat regression review

`/rower-fable/validation.html?baseline=seat` compares June immediately before
and after the seat correction. The Seat camera follows the slider while the
phase is scrubbed. `validation/seat/comparison.json` records the catch: the old
mesh had a 45 mm support gap, no contact patch, and a 22 mm central protrusion
below the sitting pads. The new test measures exported Three.js skin vertices
and contact triangle areas, not only the pelvis bone.

## Earlier June reference sculpt

The earlier detailed pass was confined to June. `scripts/june_sculpt.py` controlled
her facial proportions, swept hairline, layered bun and tapered cheek locks.
The crown is lower, the cheeks fuller and the jaw shorter. Eyelid apertures,
curved irises and surface-fitted lash edges replace flat eye discs. Lip/blush
vertex colours and projected freckles export with the mesh. Broad facial
planes are simplified locally and blended into the finer eye, mouth and ear
normals. Freckles are re-projected after that topology pass.

The vest has a wider scoop neckline, a tensioned chest surface and thin bound
edges carrying the body's blended skin weights. Triangular planes in the skin
and clothing move the finish closer to the faceted illustration. The stroke,
grips, knee axes and sitting pads keep the existing animation design. These
changes have not been applied to the other three active characters.

That MakeHuman-based June sculpt is retained as a previous version in the
development viewer. The active June build now runs without the Blender GUI:

```sh
npm run june:build
npm run june:install
```

The build writes review assets, the editable masters and a portrait rendered
from the mesh. Installation verifies the current GLB against its animation
report before replacing June's production assets. Use
`/rower-fable/validation.html?baseline=native` for the animated
before/after comparison, and
`/rower-fable/validation/reconstruction/index.html?study=june-final` for the
standing sculpt beside the original illustration. See
[reference/README.md](reference/README.md) for the active pipeline, retained
inputs, rejected experiments and remaining likeness limitations.
