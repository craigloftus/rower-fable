"""Remove reconstruction chatter and lay out broad facial and hair planes."""
from pathlib import Path
import bpy
import bmesh

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'validation/reconstruction/june-final'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.wm.ply_import(filepath=str(OUT / 'head-topology.ply'), forward_axis='Y', up_axis='Z')
head = bpy.context.object
bm = bmesh.new()
bm.from_mesh(head.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-8)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(head.data)
bm.free()
# Volume-preserving fairing removes sub-millimetre reconstruction bumps before
# the quadric solver selects the larger planes. The silhouette stays the guide.
fair = head.modifiers.new('Fair small surface ripples', 'LAPLACIANSMOOTH')
fair.lambda_factor = .28
fair.iterations = 5
fair.use_volume_preserve = True
fairing=head.vertex_groups.new(name='FaceFairing')
for vertex in head.data.vertices:
    x,y,z=vertex.co
    fairing.add([vertex.index],1 if y<.407 and z>.009 else .12,'REPLACE')
fair.vertex_group=fairing.name
bpy.ops.object.modifier_apply(modifier=fair.name)
planes = head.modifiers.new('Broad sculpt planes', 'DECIMATE')
planes.ratio = .25
bpy.ops.object.modifier_apply(modifier=planes.name)
head.vertex_groups.clear()
bpy.ops.wm.ply_export(filepath=str(OUT / 'sculpted-head.ply'), export_selected_objects=True, forward_axis='Y', up_axis='Z')
print('Sculpted head:', len(head.data.polygons), 'triangles', flush=True)
