"""Reduce the authored broad planes, retaining the source facial features."""
from pathlib import Path
import bpy,bmesh,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/sol'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.ply_import(filepath=str(OUT/'head-authored-surface.ply'),forward_axis='Y',up_axis='Z')
o=bpy.context.object;o.name='Sol authored source head'
m=o.modifiers.new('Broad source face and swept hair planes','DECIMATE');m.ratio=4500/len(o.data.polygons)
bpy.ops.object.modifier_apply(modifier=m.name)
bm=bmesh.new();bm.from_mesh(o.data);assert all(e.is_manifold for e in bm.edges);bm.free()
bpy.ops.wm.ply_export(filepath=str(OUT/'head-refined-surface.ply'),export_selected_objects=True,forward_axis='Y',up_axis='Z')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/characters/candidates/sol/head-authored.blend'))
(OUT/'head-retopology.json').write_text(json.dumps({'triangles':len(o.data.polygons),'manifold':True,'method':'Quadric reduction after broad plane authoring'},indent=2)+'\n')
