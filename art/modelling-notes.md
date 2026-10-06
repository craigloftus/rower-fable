# Modelling lessons from June and the rowing shell

The useful sequence was: establish the shape, clean its surfaces, define how it
moves, then test the exported result in the scene. Mixing these jobs made it hard
to distinguish a bad sculpt from a bad rig or misleading lighting.

1. **Keep an authoritative reference and an approved mesh.** The original image
   defines the character, proportions and palette. TRELLIS supplied a much better
   starting volume than assembling anatomical primitives, but reconstruction also
   introduced fuzzy boundaries and lighting baked into colour. Use reconstructed
   geometry as a scaffold, and keep comparing the silhouette, face and clothing
   against the illustration. One image leaves unseen surfaces ambiguous; extra
   views are useful only if they preserve the same design.

2. **Spend polygons where the form changes.** More triangles did not fix broad,
   simplistic shapes. Establish the shoulder, hip, cheek, nose and hair masses
   first. Place facets to describe those masses; remove small, noisy changes that
   do not improve the silhouette. Give faces and clothing boundaries more attention
   than hidden areas. Flat shading cannot supply a missing shape.

3. **Make joins actual geometry.** Clothing edges need deliberate boundaries and
   compatible cross-sections. Overlapping cylinders, caps and substitute hands
   left visible steps and spikes. Preserve the approved simplified hands and their
   wrist transition. For hard objects, use shared edges, thickness and small
   bevels. The boat's blade colour boundary now shares edges; its shaft stops
   inside the handle instead of sharing the handle's end face.

4. **Separate material colour from illumination.** Skin, cloth, hair, wood and
   paint need clean base colours. Do not preserve source-image shadows on legs or
   painted eye reflections as though they were material. Judge the mesh under
   neutral light, rotate it, then review it in the lake scene. Roughness and real
   surface normals should produce the highlights and shading.

5. **Rig the accepted shape without redesigning it.** June now enters the rig
   with one uniform scale and rigid placement. Fixed limb lengths and anatomical
   joint frames replaced stretching limbs and reshaping the torso to reach targets.
   Put shoulder and hip pivots inside their volumes; define knee and elbow bend
   planes explicitly. Dual-quaternion skinning preserves volume, but does not fix
   an incorrect pivot, poor weights or an already-distorted bind mesh.

6. **Define contact frames, not just contact points.** A hand needs a wrist,
   knuckle direction, palm normal and grip centre. Otherwise a solver can put the
   hand at the right position while twisting the whole arm. Fit the retained
   thumb branch, including its tip and web, with limited deformation. A numerical
   contact fit alone produced ugly thumbs: inspect the skin and measure edge
   stretch as well. Seat and foot support must be checked on the exported surface,
   not on a hip or ankle marker.

7. **Design the whole cycle and its velocities.** Separate eased movements can
   still look jerky when each stops before the next starts. June's recovery now
   has continuous handle travel and overlapping hands-away, body swing and slide.
   The two handle-curve segments share velocity and acceleration at their join;
   the crossover lift also loses its sharp velocity reversal. Keep enough knee
   clearance as the movements overlap. Review at the actual drive/recovery timing,
   including the finish and catch boundaries.

8. **Validate the delivered asset, visually and numerically.** Bake deterministic
   poses, export GLB and compare Blender deformation with Three.js. Scrub front,
   side, rear, hand and seat views; inspect a moving cycle and the real app. Sample
   between keyframes for collision, seam, bone-length and contact checks. Preserve
   a before version for honest comparisons. Passing checks establishes measured
   constraints, not artistic quality.

For the boat pass, the same principles meant a lofted shell with a cambered deck,
recessed cockpit, continuous coaming, bevelled seat and footboard, supported rails,
and thin shaped blades. These are authored in `src/boat-shapes.js`; assembly and
motion remain in `src/boat.js`. The seat top stays at 0.3175 m, the footboard keeps
its support plane, and June's handle radius stays at 0.020 m. Visual refinement
must respect these shared physical dimensions.

Review recovery at `validation.html?baseline=native` and the boat alone at
`validation.html?baseline=boat`. The full character pipeline and its retained
experiments are documented in [characters/reference/README.md](characters/reference/README.md).
