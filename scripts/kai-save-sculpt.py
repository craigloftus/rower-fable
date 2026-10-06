"""Save the editable standing Kai sculpt with its authoritative image packed."""
from pathlib import Path
import bpy,hashlib
ROOT=Path(__file__).resolve().parents[1];MASTER=ROOT/'art/characters/candidates/kai'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(MASTER/'standing.glb'))
for obj in bpy.context.scene.objects:
    if obj.type=='MESH':
        obj['source']='Kai original concept, local body/head reconstruction and source-fitted surface cleanup'
        obj['standingSha256']=hashlib.sha256((MASTER/'standing.glb').read_bytes()).hexdigest()
image=bpy.data.images.load(str(ROOT/'art/characters/kai-concept.png'));image.pack()
bpy.context.scene['reference']='kai-concept.png is authoritative. This candidate is not installed.'
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER/'sculpt.blend'))
