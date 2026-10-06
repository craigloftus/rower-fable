# Character authoring

The active cast is Kai, June, Sol and Ada. Their original generated illustrations
in this directory define identity and supply the opening selector portraits.
Mira is retired; her old editable source is retained as an archive.

All four characters use June's approved body, skeleton, skin weights and exact
rowing animation. Kai, Sol and Ada retain their individually refined heads.
`shared-cast/cast.json` chooses each head, skin tone, top colour and fixed chest
variant. Kai uses the flatter variant; June, Sol and Ada use June's approved
shape. The choice is internal, with no user-facing controls or runtime morphs.

The body geometry stays unchanged outside the small neck join and the selected
chest region. Shared shoulders, hips, limbs, hands and shoes keep the same
validated proportions and deformation. All four use June's boat fit.

## Source to sculpt

Read the reusable [rowing-character skill](../../.agents/skills/rowing-character/SKILL.md)
and [modelling lessons](../modelling-notes.md). The main lessons are:

- Establish closed anatomy from the reconstruction before designing facets.
- Shape cheek, jaw, nose and hair planes deliberately; global decimation cannot
  replace modelling. Compare the same viewing angle as the original.
- Weld and fair the neck join. Inspect standing geometry before blaming a fold
  on the rig.
- Cut clothing boundaries into the surface so adjacent materials share edges.
- Use clean albedo, shallow convex eyes and real lighting. Preserve intentional
  pigment such as freckles; remove baked shadows and reflections.
- Keep the original simplified joined-finger hands and wrist transition.

`shared-cast/` contains the approved body master, compact head-only inputs,
editable assembled characters, raw exports and a hashed manifest. The earlier
`candidates/<id>/` packages document the separately reconstructed bodies and
head refinement work; they are historical studies and head provenance.
New builds need no inference caches or model weights.

## Sculpt to rowing animation

The shared rig uses fixed limb lengths, explicit knee/elbow planes, clavicle
motion and local twist weights. The complete palm frame determines handle
contact. Pelvis and sole contact are inherited from the approved June rig.
The original simplified joined-finger hands remain unchanged.

Blender Preserve Volume matches the app's dual-quaternion skinning. A generic
linear-skinning glTF viewer will deform these assets differently. Every character
has the exact approved two-second `RowingCycle`: drive at `p`, recovery at `1+p`.
Bluetooth cadence and the stroke engine supply timing. Recovery overlaps
hands-away, torso swing and slide, with continuous handle velocity.

`src/rowing-fit.js` supplies the same June handle geometry and slider travel for
every character. Body identity checks compare exported positions, weights and
triangles outside the declared variant regions; animation tracks are compared
exactly with the approved June export.

## Review and delivery

Review neutral colour and clay, then the exact exported asset in the full river
scene. Inspect front, profile, rear and reference-facing three-quarter views,
plus shoulders, armpits, grip, hips, knees, seat and shoes through the whole cycle.
Use headless Chromium and background Blender; no foreground screen takeover.

Native validators sample 1,201 poses, including between keys, for fixed bone
lengths, shared seams, hand targets, supported seat, rigid soles, knee axes and
motion continuity. Separate checks inspect 161 poses for arm/leg and arm/chest
intersections, retained-hand surface contact and thumb/web stretch. Exported
vertices are compared with Blender deformation. Passing these checks does not
replace visual review, nor does it establish every possible self-intersection.

Delivery uses lossless Meshopt buffer compression. It removes no triangles and
changes no decoded geometry, colours, rig transforms or animation samples. The
installer validates the compressed file before copying it into `public/characters/`.
The build versions model URLs from their content hashes so an older cached GLB
cannot be paired with a newer rowing fit. Editable masters remain uncompressed.
Original illustration portraits remain
independent of model-rendered review images.

```sh
npm run characters:build
# Inspect the shared-cast review renders before installing:
npm run characters:install
npm run characters:validate
npm test
npm run build
```

The build runs background Blender and exported-body/animation validation. The
installer compresses and checks all four exports before replacing any app asset.
It also installs editable `.blend` files and records delivered hashes in
`validation/characters/installed/manifest.json`. June's original authoring chain
remains available through `june:build` and `june:install`. Do not run the historical
separate-body or MakeHuman builders to replace the current cast.

Profile each installed model in the full river scene at native pixel density.
The target is 120 fps while rowing; setup and summary screens render at 30 fps.
Desktop headless timings are regression evidence, not proof of sustained Pixel 8
performance or temperature. See [performance evidence](../../validation/performance/README.md).

## Earlier approaches and provenance

The original Quaternius model, the shared MakeHuman body, earlier June sculpts
and rejected face studies remain as development comparisons, not runtime
fallbacks. Runtime bone stretching, point-only hand constraints and replacement
body parts caused the earlier distorted limbs, grips and hip transitions.

MakeHuman graphical source assets are CC0; their unmodified license and hashes
remain in `art/source/`. Its AGPL application code is not used. Original generated
reference prompts are in `prompts.json`. Reconstruction weights and credentials
stay outside the repository. The current cast is a stylized interpretation of
single-image references, not an exact multi-view reconstruction or a rowing
biomechanics simulator.
