"""Save the editable standing Ada sculpt with its authoritative image packed."""
from pathlib import Path
import bpy,hashlib
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[1];MASTER=ROOT/'art/characters/candidates/ada'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(MASTER/'standing.glb'))
for obj in bpy.context.scene.objects:
    if obj.type=='MESH':
        obj['source']='Ada original concept, local body/head reconstruction and source-fitted surface cleanup'
        obj['standingSha256']=hashlib.sha256((MASTER/'standing.glb').read_bytes()).hexdigest()
# Keep the connected closed surface alongside the coloured export for sculpting.
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.ply_import(filepath=str(ROOT/'validation/characters/ada/assembled-surface.ply'),forward_axis='Y',up_axis='Z')
source=bpy.context.object;source.name='Ada closed authoring surface'
source.data.transform(Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1))))
guide=bpy.data.collections.new('Closed sculpt source, unhide to edit');bpy.context.scene.collection.children.link(guide)
for collection in list(source.users_collection):collection.objects.unlink(source)
guide.objects.link(source);source.hide_render=True;source.hide_set(True)
source['description']='Connected closed surface before conforming material cuts and eye patches'
image=bpy.data.images.load(str(ROOT/'art/characters/ada-concept.png'));image.pack()
bpy.context.scene['reference']='ada-concept.png is authoritative. This candidate is not installed.'
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER/'sculpt.blend'))
