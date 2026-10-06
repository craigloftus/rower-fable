"""Save the editable finished sculpt with the approved geometry as a guide."""
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'validation/reconstruction/june-final/mesh.glb'))
finished=bpy.data.collections.new('June · final faceted sculpt')
bpy.context.scene.collection.children.link(finished)
for obj in list(bpy.context.scene.objects):
    for collection in list(obj.users_collection):collection.objects.unlink(obj)
    finished.objects.link(obj)
before=set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'validation/reconstruction/trellis-assembled/mesh.glb'))
guide=bpy.data.collections.new('Approved geometry · comparison guide')
bpy.context.scene.collection.children.link(guide)
for obj in set(bpy.context.scene.objects)-before:
    for collection in list(obj.users_collection):collection.objects.unlink(obj)
    guide.objects.link(obj)
guide.hide_render=True;guide.hide_viewport=True
design=bpy.data.images.load(str(ROOT/'art/characters/june-concept.png'),check_existing=True)
design.pack()
bpy.context.scene['design_reference']='june-concept.png — original design, packed in this file'
bpy.context.scene['geometry_reference']='TRELLIS.2 approved assembly; hidden comparison collection'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/characters/reference/june-final-sculpt.blend'))
