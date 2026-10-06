---
name: rowing-character
description: Reconstruct, refine, rig and validate Morning Row characters from their original illustrations using the approved June pipeline. Use for character asset work in rower-fable.
---

# Reference to animated rower

Work from the repository root. Read `art/modelling-notes.md` for the modelling
lessons and `art/characters/reference/README.md` for the experiments and active
June pipeline. The original `art/characters/<id>-concept.png` defines identity,
face, hair and palette. Following the user's October 2026 direction, June is the
approved shared body and rowing rig for the entire cast. Use character-specific
heads, skin tones and singlet colours, with two fixed chest variants selected
in the authoring config. Do not reconstruct or re-rig a separate body for each
character. The active cast is Kai, June, Sol and Ada; Mira is retired.

## Establish a reviewable candidate

Work on one head at a time in `art/characters/candidates/<id>/`. Assemble it
with the shared body in `art/characters/shared-cast/`; keep evidence under
`validation/characters/shared-cast/`. Keep production assets intact until the candidate
passes the checks below. Record source paths, hashes, commands, modelling
choices and measured limitations in a candidate README. `characters:build` rebuilds
shared-body review packages from retained sources; it does not install them. Do not use the legacy `scripts/build-characters.py` to
replace the cast.

1. Inspect the original image and current model. Record distinguishing face,
   hair, silhouette, clothing and colour features. Render a before comparison.
2. Use local TRELLIS.2 MLX for a new head scaffold when its mesh cannot support
   the reference. Keep the approved June body. The installed runtime is
   `~/.local/share/rower-tools/trellis2mlx`; its Python invokes
   `scripts/reconstruct-trellis-local.py`. Check its CLI before execution.
   DINOv3 is ViT-L/16 LVD-1689M; weights and credentials stay outside this repo.
   A 1024/12-step reconstruction previously took about 17 minutes on this Mac.
   Do not provision a cloud GPU or repeat the rejected TripoSR route by default.
3. Additional head/turnaround images can clarify form but must retain the
   original identity. Inspect them before reconstruction. Never treat a new
   attractive illustration as proof that the exported mesh improved.
4. Clean the geometry in background Blender, retaining an editable `.blend`.
   Establish closed, connected anatomy before retopology. Shape facets around
   changes of form: cheek, jaw, nose, shoulder, hip, hair masses. More polygons
   on generic forms and aggressive decimation of noisy geometry both failed.
   Reconstruct the original head crop separately when the whole-body head lacks
   detail. Weld and locally fair its neck join; inspect for a shelf in profile.
   Author shallow convex eyes and lid occlusion, keeping the reference's iris
   colour and expression. Check lip projection from the side before rigging.
5. Cut clothing boundaries into a conforming surface. Keep stripe edges level,
   continuous neckline/armholes, and matched shorts/thigh cross-sections. Retain
   simplified joined-finger hands and the natural wrist transition.
6. Separate albedo from light. Remove baked limb shadows and eye reflections;
   use material roughness and actual lighting. Freckles and cheek pigment are
   intentional colour. Judge neutral clay, clean materials and scene lighting.

## Fit motion to anatomy

Use the approved standing mesh unchanged except for one uniform scale and rigid
placement. Do not reshape the chest, inflate hips, stretch limbs, or replace hands
to reach a bad pose. Reuse June's approved anatomical pivots, weights, exact
RowingCycle and boat fit for all characters. Keep its limbs, hips, shorts, shoes
and simplified hands unchanged. Author the flatter chest only as a bounded
static source variant, retaining rounded ribcage planes; never morph during rowing.
Align new heads by chin/eye/neck landmarks, not total hair height, and weld a
local neck bridge. Verify shared body positions and weights outside that bridge
and the selected chest region against approved June.

The approved rig is `validation/reconstruction/fresh-rig/june.blend`. Reuse its
action and skin weights directly. Earlier separate-body Kai/Sol/Ada packages
are retained studies and head sources, not the production body pipeline. Shared runtime constraints live in
`src/rowing-fit.js`, `src/oar-pose.js` and `src/stroke.js`.

- Fixed limb lengths, explicit knee/elbow bend planes, clavicle motion, local
  shoulder weights and gradual forearm twist. No animated bone scales or morphs.
- Identical weights at shared material seams. Keep thigh influence off the waist.
- Define each hand's wrist, knuckle axis, palm normal and grip centre. Grip
  position alone allows whole-arm twist. Keep the complete thumb branch and tip
  weighted correctly; don't include the wrong finger-web vertices.
- Fit the oars and stroke to the character. Maintain torso and knee clearance.
  Recovery must overlap hands-away, body swing and slide without separate stops.
- Fit actual seat/sole contact surfaces, not just bone markers.
- Use Blender Preserve Volume and the corresponding Three.js dual-quaternion
  path (`src/volume-skinning.js`, GLB extras `skinning: dualQuaternion`). A generic
  linear-skinning glTF viewer is not a valid comparison.
- Export one two-second `RowingCycle`: drive at t=p, recovery at t=1+p. Actual
  rowing cadence comes from Stroke/FTMS, not a second animation clock.

## Acceptance and delivery

Inspect front, side, rear and three-quarter views of the exported standing model
beside the original. Inspect moving catch, drive, finish and recovery plus close
views of shoulders, armpits, hands, waist, shorts, knees, seat and feet. Headless
Chromium only: don't open a foreground browser or Blender window for testing.

Run `npm run characters:build`, review the exports, then
`npm run characters:install` and `npm run characters:validate`. The shared build
checks protected body geometry and exact animation identity. Use June's
native/grip/body validators for motion and contact checks. Sample between keys (June
uses 1,201 numerical poses and 161 collision poses), verify no scale/morph
animation, constant limb lengths, seam closure, grip location/orientation,
thumb/web stretch, surface collisions, planted soles and seat contact. Compare
Blender deformation with exported Three.js. Validate under a transformed boat
parent. Tests must measure source-defined regions, not redefine anatomy from
whatever the weights currently claim.

Record triangle count, file size, draw calls and native-DPR frame costs against
June and the previous character. Preserve native device pixel density and the
120 fps rowing target; do not trade clarity for a passing benchmark. Desktop
headless results do not prove Pixel 8 thermal performance.

For delivery, use `scripts/compress-character.mjs`: lossless Meshopt encoding,
without quantization, decimation or animation resampling. It verifies decoded
attributes, transforms, materials and triangle winding. Run the native validator
on the compressed file in a separate report directory. Retain the uncompressed
editable export. All shared bodies must use `JUNE_ROWING_FIT` and the exact
approved RowingCycle. The chest variant is fixed per character; do not add a
user-facing chest control.
Use `PROFILE_CHARACTER`, `PROFILE_ASSET` and `PROFILE_POSE_MODULE` with
`scripts/profile-headless.mjs` to benchmark a candidate in the full river scene.
Repeat without overrides once installed, recording the exact delivered hash.

Install only after both visual review and numerical checks support an improvement.
If likeness is worse, retain the candidate for review and report it honestly;
numerical passes are not artistic approval. The September June face studies were
rejected and must not be reinstated. Keep original-illustration selector portraits
separate from model-rendered validation portraits. Commit the editable master,
export, authoring code and concise validation evidence; exclude caches, logs and
duplicate experimental builds. Never commit access tokens or model-weight caches.
