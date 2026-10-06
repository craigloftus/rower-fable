"""Save the approved assembly as an editable Blender template with welded neck edges."""
from pathlib import Path
import bpy
import bmesh

root=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(root/'validation/reconstruction/trellis-assembled/mesh.glb'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for obj in meshes:obj.select_set(True)
bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join()
obj=bpy.context.object;obj.name='June assembly — faceted rebuild template'
bm=bmesh.new();bm.from_mesh(obj.data)
seam=[v for v in bm.verts if min(abs(v.co.z-.307),abs(v.co.z-.318))<1e-7]
bmesh.ops.remove_doubles(bm,verts=seam,dist=1e-7)
bm.to_mesh(obj.data);bm.free()
obj['purpose']='Approved shape template; neck joined and head placement corrected. Preserve silhouette during retopology.'
bpy.ops.wm.save_as_mainfile(filepath=str(root/'art/characters/reference/june-assembled-template.blend'))
