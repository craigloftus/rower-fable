"""Reduce cleaned source planes to useful facets, without smoothing normals."""
from pathlib import Path
import bpy,bmesh
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/kai'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.ply_import(filepath=str(OUT/'head-authored-surface.ply'),forward_axis='Y',up_axis='Z')
o=bpy.context.object
mod=o.modifiers.new('Source feature planes','DECIMATE');mod.ratio=3200/len(o.data.polygons)
bpy.ops.object.modifier_apply(modifier=mod.name)
bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);bm.to_mesh(o.data);bm.free()
for p in o.data.polygons:p.use_smooth=False
bpy.ops.wm.ply_export(filepath=str(OUT/'head-refined-surface.ply'),export_selected_objects=True,forward_axis='Y',up_axis='Z')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/characters/candidates/kai/head-authored.blend'))
