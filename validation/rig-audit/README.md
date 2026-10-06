# June rigging review, 25 September 2026

This review describes the previous rig. The fresh implementation is documented
in [the character build notes](../../art/characters/reference/README.md#fresh-rig-september-25)
and can be compared at `validation.html?baseline=native`. It retains the
approved sculpt's simplified hands, as requested after this review.

The current binding pipeline should be replaced. The approved sculpt is a
useful starting point, but the rowing conversion changes its proportions and
substitutes parts from an older character. Better skinning alone cannot recover
the lost shape.

This review adds diagnostic views and measurements. It does not replace the
game asset or claim that the character is fixed.

## Inspect the evidence

- [Unanimated shapes](http://127.0.0.1:5176/rower-fable/validation.html?baseline=bind)
  compares the approved sculpt, uniformly scaled by 1.8, with the current rig
  in its actual bind pose. Use Front and Torso profile. The altered chest,
  longer upper arms, replacement hands and distorted shorts are present before
  any animation runs.
- [Skinning comparison](http://127.0.0.1:5176/rower-fable/validation.html?baseline=skinning)
  uses the same exported mesh, weights and animation on both sides. Only the
  skinning calculation changes. Inspect catch, finish and recovery, including
  recovery 24%, the game's resting pose.

The reviewed production GLB and the existing reconstruction review GLB have
the same SHA-256:
`b929f91bcb332adfa95c407b56394f81824697953fa4c616966af592975fa978`.
This is not a comparison against a stale export.

The numerical and visual experiments below cover June. The other four
characters use `scripts/anatomy.py` and `scripts/build-characters.py`; those
also remap the source body with separate axial/radial scales and attach simple
closed grips. The architectural concern is shared, but these measurements
must not be presented as results for all five characters. Establish the new
binding method on June before applying it to the rest of the cast.

## What the current pipeline does

`scripts/rig-final-june.py` creates different source-to-target transforms for
the trunk, head and each limb. It blends these transforms to reposition the
vertices, then binds the resulting mesh to another set of bone transforms.
It also applies `rowing_shape`, which reduces chest projection and changes
the lumbar profile. These are permanent alterations to the neutral mesh.

The upper-arm landmarks are 26.07 cm apart after a uniform 1.8 scale. The bind
changes that length to 30 cm while retaining the radial scale. This lengthens
the arm by 15.1% relative to its width. The forearm is shortened by 4.4%, and
the trunk's vertical scale is 4.3% greater than its width scale.

Using the existing shoulder and wrist targets, the original arm lengths offer
57.44 cm of reach. The maximum required reach is 55.63 cm. All 482 sampled
left/right targets are reachable without that upper-arm stretch. This checks
reach only; a new rig still needs elbow clearance and joint-limit checks.

The script removes the reconstructed shorts and relaxed hands. It imports
older shorts and closed hands, fits the shorts with `june_garment.py`, and
adds strips across the waistband, cuffs and wrists with `june_fit.py`.
Four extra garment bones retain different inverse bind transforms from the
old body. Sharing their animated poses does not make those rest frames equal.

| Visible problem | Evidence in the pipeline | Required change |
| --- | --- | --- |
| Thin, stretched arms | Unequal axial/radial scaling; broad and position-based weight overrides around joints | Preserve limb dimensions and author weights on topology arranged around the joints |
| Shoulder and elbow distortion | Blending can pull adjacent vertices very differently; there are no clavicle or forearm twist bones | Add anatomical shoulder motion and distribute twist along the forearm |
| Slab-like front | The bind directly compresses chest geometry with `rowing_shape` | Retain the approved chest in the neutral mesh and solve movement through the rig |
| Spiky shorts and widening thighs | An older garment is fitted in catch, then inverse-deformed with a mixture of old and new bind frames | Use one coherent rest pose for the body and its fitted shorts |
| Abrupt wrists and simple hands | The original hands are cut away and replaced with older meshes joined by a strip | Model the grip hands to the same standard and join palm, wrist and forearm topology |

The browser does not add arbitrary morphing. `src/rower.js` only sets the time
of `RowingCycle`. The exported scale tracks are constant, and it has no morph
tracks. The largest deviation of a bone transform's scale from one is
0.000000371, consistent with floating-point rounding.

## The alternative tested

The review includes dual-quaternion skinning, the rigid-transform blending
method used by Blender's Preserve Volume option. Three.js 0.184.0 uses linear
blend skinning in its standard shader, confirmed in the installed
`node_modules/three/src/renderers/shaders/ShaderChunk/skinning_vertex.glsl.js`.
The experiment changes only the review renderer, in
`validation/dual-quaternion.js`.

`check-june-skinning.py` independently compares the diagnostic calculation with
Blender's actual armature modifier at five poses and 2,560 sampled vertices.
The largest position difference is 0.00035 mm. This verifies the CPU
calculation used for measurements. The matching shader renders successfully
in the browser, but its pixels were not used for that numerical comparison.

The result is mixed, not an acceptable replacement. Across 49 poses, the
fraction of measured elbow edges that ever change length by more than 25%
relative to the current bind mesh falls from 52.3% to 43.9%. For shoulder edges,
it rises from 75.0% to 77.2%. Some shorts and shoulder shapes visibly worsen.

These statistics use unique mesh edges at least 5 mm long, grouped by skin
weights. They measure surface distortion, not anatomical volume, silhouette
quality or likeness. Normal bending also changes some edge lengths. The raw
results and definitions are in `deformation.json`.

## Replacement approach

1. Start from the approved sculpt in one neutral pose and apply one uniform
   scale. Record that shape as the reference. Remove the per-bone resizing,
   chest/lumbar shaping and reuse of old shorts from the new binding route.
2. Fit a connected skeleton to that anatomy. Use a pelvis, a short spine chain,
   clavicles, upper arms, forearm twist bones, wrists and finger controls.
   Preserve bone lengths. Fit the stroke to reachable joint targets, with
   explicit elbow and knee bend planes and joint limits.
3. Rework the deformation topology around shoulders, elbows, hips, knees and
   wrists while retaining the approved outer shape. Paint and inspect weights
   on this continuous body. Derive weights at clothing/material boundaries
   from the same surface so a change of material cannot create a change of
   motion. Face and hair need not be rebuilt for this.
4. Model closed grip hands with continuous wrists and properly shaped palms,
   knuckles and fingers. Fit the shorts in the same rest pose and skeleton as
   the thighs, retaining the original garment silhouette.
5. Author and inspect catch, mid-drive, finish, hands-away and recovery poses
   before baking a full cycle. Use small joint-local corrective shapes only
   where the new topology and weights still lose the approved form. A corrective
   shape should have an identified purpose, such as restoring elbow volume,
   rather than flattening an entire chest to hide a rigging error.
6. Export standard skeletal animation plus any necessary baked corrective
   morph targets. Compare the actual GLB in Three.js with the Blender poses.
   Do not assume a Blender modifier setting transfers through glTF. Three.js
   supports combined skeletal and morph animation in its
   [official example](https://threejs.org/examples/webgl_animation_skinning_morph.html).
   Blender documents shape-key animation export in its
   [glTF manual](https://docs.blender.org/manual/id/5.0/addons/import_export/scene_gltf2.html).

Use a good ordinary skinning rig as the export baseline. Decide whether
dual-quaternion deformation or baked volume corrections improve the new rig
after its weights and bind pose are sound. The experiment rejects using a
global DQ switch as a repair for the current asset. A control-rig generator
such as Rigify would not itself repair its geometry or weights.

## Acceptance criteria that were missing

The previous tests proved contact, continuity of bone motion and selected
collision avoidance. They did not establish that the surface looked natural.
In particular, the cuff test measured separation between opening edges. It
could pass while the surrounding thigh widened sharply. The seat test could
pass while the side of the shorts formed a spike.

The replacement needs both numerical checks and visual inspection:

- The neutral body must match the approved shape after one uniform transform.
  Any intentional topology or hand changes must be identified separately.
- Bone lengths must stay fixed. Inspect limb cross-sections and surface-edge
  strain through the cycle, with tolerances chosen for each anatomical region.
- Measure circumference and silhouette on both sides of each cuff and wrist,
  not just the distance between their boundary loops.
- Check rest, catch, finish, hands-away and recovery from front, profile and
  rear under neutral light and in clay. Inspect the in-between motion too.
- Retain the existing grip, foot, knee-axis, seat and collision checks. Add
  torso/arm and hand/body checks where the current suite does not cover them.
- Compare Blender and exported Three.js poses before replacing the game asset.

Reproduce this review with the development server running:

```sh
node scripts/audit-june-deformation.mjs
blender --background --factory-startup --python-exit-code 1 --python scripts/check-june-skinning.py
```

The fresh bind, joint topology, hands and corrective poses described above are
the next implementation stage. They have not been built by this audit.
