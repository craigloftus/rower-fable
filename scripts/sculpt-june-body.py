"""Lay out a closed faceted body over the approved silhouette.

QuadriFlow introduced a pinched knee in its quad layout. Use the sealed volume
directly, fair its sampling ripple, and reduce it with topology-preserving
edge collapses instead. Every intermediate surface remains closed.
"""
from pathlib import Path
import bpy
import bmesh

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/june-final'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.ply_import(filepath=str(OUT/'solid.ply'),forward_axis='Y',up_axis='Z')
obj=bpy.context.object
obj.name='June continuous sculpt'
pre=obj.modifiers.new('Remove grid-scale edges','DECIMATE');pre.ratio=.02
bpy.ops.object.modifier_apply(modifier=pre.name)
fair=obj.modifiers.new('Fair reconstruction ripple','LAPLACIANSMOOTH')
fair.lambda_factor=.22;fair.iterations=5;fair.use_volume_preserve=True
bpy.ops.object.modifier_apply(modifier=fair.name)
reduce=obj.modifiers.new('Anatomical planes','DECIMATE');reduce.ratio=.19
bpy.ops.object.modifier_apply(modifier=reduce.name)
bm=bmesh.new();bm.from_mesh(obj.data)
assert all(e.is_manifold for e in bm.edges),'The sculpt must remain closed'
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
bpy.ops.wm.ply_export(filepath=str(OUT/'faceted-surface.ply'),export_selected_objects=True,forward_axis='Y',up_axis='Z')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/characters/reference/june-final-topology.blend'))
print('Closed body sculpt:',len(obj.data.polygons),'triangles',flush=True)
