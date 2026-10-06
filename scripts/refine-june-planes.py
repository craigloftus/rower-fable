"""Remove reconstruction-scale ripples and consolidate readable sculpt planes."""
from pathlib import Path
import bpy
import bmesh
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/june-final'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.ply_import(filepath=str(OUT/'refined-surface.ply'),forward_axis='Y',up_axis='Z')
obj=bpy.context.object
bm=bmesh.new();bm.from_mesh(obj.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(obj.data);bm.free()
# New connectivity already follows the surface. Consolidate its small nearly
# coplanar cells, keeping substantially more of the facial feature geometry.
group=obj.vertex_groups.new(name='Facial structure')
for vert in obj.data.vertices:
    x,y,z=vert.co
    if y>.335 and z>.007:group.add([vert.index],.8,'REPLACE')
modifier=obj.modifiers.new('Consolidate sculpt planes','DECIMATE')
modifier.ratio=.55
bpy.ops.object.modifier_apply(modifier=modifier.name)
obj.vertex_groups.clear()
for poly in obj.data.polygons:poly.use_smooth=False
bpy.ops.wm.ply_export(filepath=str(OUT/'faceted-surface.ply'),export_selected_objects=True,forward_axis='Y',up_axis='Z')
print('Faceted surface:',len(obj.data.polygons),flush=True)
