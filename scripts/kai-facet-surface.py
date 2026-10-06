"""Remove grid-scale noise from Kai's sealed volume, retaining facial density."""
from pathlib import Path
import bpy, bmesh, json, sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/kai'
prefix='head-' if '--head' in sys.argv else ''
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.ply_import(filepath=str(OUT/(prefix+'solid.ply')),forward_axis='Y',up_axis='Z')
obj=bpy.context.object;obj.name='Kai continuous sculpt'
smooth=obj.modifiers.new('Soften reconstruction micro-edges','SMOOTH');smooth.factor=.5;smooth.iterations=4
bpy.ops.object.modifier_apply(modifier=smooth.name)
mod=obj.modifiers.new('Describe anatomical forms','DECIMATE');mod.ratio=(15000 if prefix else 30000)/len(obj.data.polygons)
bpy.ops.object.modifier_apply(modifier=mod.name)
bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
defects=sum(not e.is_manifold for e in bm.edges);bm.to_mesh(obj.data);bm.free()
assert defects==0,defects
for p in obj.data.polygons:p.use_smooth=False
bpy.ops.wm.ply_export(filepath=str(OUT/(prefix+'faceted-surface.ply')),export_selected_objects=True,forward_axis='Y',up_axis='Z')
(OUT/(prefix+'faceting.json')).write_text(json.dumps({'triangles':len(obj.data.polygons),'nonManifoldEdges':defects,'source':'Sealed original-image reconstruction'},indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/characters/candidates/kai'/(prefix+'topology.blend')))
