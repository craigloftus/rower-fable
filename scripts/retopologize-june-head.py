"""Retopologise the fine repaired head and project onto its preserved features."""
from pathlib import Path
import bpy
import bmesh
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/june-final'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.ply_import(filepath=str(OUT/'fine-head-solid.ply'),forward_axis='Y',up_axis='Z')
obj=bpy.context.object
bm=bmesh.new();bm.from_mesh(obj.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
surface=BVHTree.FromPolygons([v.co for v in obj.data.vertices],[f.vertices for f in obj.data.polygons],all_triangles=True)
# Work in centimetre-like units to avoid the solver's tiny-edge tolerance.
for v in obj.data.vertices:v.co*=100
obj.data.update()
pre=obj.modifiers.new('Remove grid micro-edges','DECIMATE');pre.ratio=.055
bpy.ops.object.modifier_apply(modifier=pre.name)
print('Head solver input:',len(obj.data.polygons),flush=True)
bpy.ops.object.quadriflow_remesh(target_faces=5200,use_mesh_symmetry=False,use_preserve_sharp=False,use_preserve_boundary=False,smooth_normals=False,seed=24)
assert len(obj.data.polygons)<8000,'Head quad layout failed'
for vert in obj.data.vertices:
    p=vert.co/100;hit,_,_,distance=surface.find_nearest(p)
    vert.co=hit if distance<.005 else p
# Only a light fairing pass; facial folds and the bun remain in the guide.
bm=bmesh.new();bm.from_mesh(obj.data)
bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
bm.to_mesh(obj.data);bm.free()
bpy.ops.wm.ply_export(filepath=str(OUT/'head-topology.ply'),export_selected_objects=True,forward_axis='Y',up_axis='Z')
print('Head topology:',len(obj.data.polygons),flush=True)
