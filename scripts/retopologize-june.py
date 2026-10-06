"""New quad topology over the approved June silhouette, with facial density.

blender -b --python-exit-code 1 --python scripts/retopologize-june.py
"""
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'validation/reconstruction/june-final'
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.wm.ply_import(filepath=str(OUT/'solid.ply'), forward_axis='Y', up_axis='Z')
obj = bpy.context.object
# PLY is explicitly source-space Y-up. Keep these coordinates until export.
obj.name = 'June — rebuilt continuous surface'
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# Resolve ambiguous marching-cubes corner contacts before QuadriFlow.
bm = bmesh.new(); bm.from_mesh(obj.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
print('Source topology defects:', sum(not e.is_manifold for e in bm.edges),
      sum(not v.is_manifold for v in bm.verts), flush=True)
bm.to_mesh(obj.data); bm.free()
# Store the continuous guide so the new topology projects onto the same surface.
guide = obj.copy(); guide.data = obj.data.copy(); bpy.context.collection.objects.link(guide)
guide.name = 'Approved shape — sealed projection guide'
verts = [v.co.copy() for v in obj.data.vertices]
faces = [tuple(f.vertices) for f in obj.data.polygons]
surface = BVHTree.FromPolygons(verts, faces, all_triangles=True)

# Stretch only the sampling space, then undo it. The face/hair receive about
# half of the topology budget without enlarging the final head or changing it.
def warp_y(y):
    t = max(0, min(1, (y-.28)/.06))
    integral = .06*(t**3-.5*t**4) + max(0, y-.34)
    return y+2*integral

def scale_at(y):
    t = max(0, min(1, (y-.28)/.06))
    return 1+2*t*t*(3-2*t)

for vert in obj.data.vertices:
    x,y,z = vert.co; s = scale_at(y)
    vert.co = (x*s, warp_y(y), (z+.02)*s-.02)
bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active=obj
obj.data.update()
# Remove the marching-cubes micro-edges before the quad solver. This is only
# its input conditioning; the final surface has entirely new connectivity.
conditioning=obj.modifiers.new('Solver input conditioning', 'DECIMATE')
conditioning.ratio=.07
bpy.ops.object.modifier_apply(modifier=conditioning.name)
print('Starting facial-density quad layout:',len(obj.data.polygons),'input faces', flush=True)
bpy.ops.object.quadriflow_remesh(target_faces=11500, use_mesh_symmetry=False,
    use_preserve_sharp=False, use_preserve_boundary=False, smooth_normals=False, seed=24)
print('Quad layout:', len(obj.data.polygons), flush=True)
assert len(obj.data.polygons)<16000, 'QuadriFlow did not produce a new mesh'
for vert in obj.data.vertices:
    x,wy,z = vert.co; y=wy
    for _ in range(12): y -= (warp_y(y)-wy)/scale_at(y)
    s = scale_at(y); p=Vector((x/s,y,(z+.02)/s-.02))
    hit,_,_,distance=surface.find_nearest(p)
    vert.co = hit if distance < .008 else p
# Keep a quad authoring master. Triangle choices are made during garment cuts.
for poly in obj.data.polygons: poly.use_smooth=False
bpy.ops.wm.ply_export(filepath=str(OUT/'retopology.ply'),export_selected_objects=True,forward_axis='Y',up_axis='Z')
guide.hide_render=True; guide.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/characters/reference/june-final-topology.blend'))
print('Saved new topology', flush=True)
