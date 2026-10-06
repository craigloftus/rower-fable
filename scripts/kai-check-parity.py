"""Compare the exported Three.js skin with Blender's evaluated armature."""
import bpy
import hashlib
import json
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

root=Path(__file__).resolve().parents[1]
out=root/'validation/characters/kai'
master=root/'art/characters/candidates/kai'
bpy.ops.wm.open_mainfile(filepath=str(master/'kai.blend'))
obj=bpy.data.objects['kai']
assert obj.modifiers['Native anatomical skin'].use_deform_preserve_volume
C=Matrix(((1,0,0),(0,0,-1),(0,1,0)))
tree=KDTree(len(obj.data.vertices))
for vertex in obj.data.vertices:tree.insert(vertex.co,vertex.index)
tree.balance()
witness=json.loads((out/'parity-witness.json').read_text())
maximum_rest=0
for row in witness:
    _,index,distance=tree.find(C@Vector(row['rest']))
    row['index']=index;maximum_rest=max(maximum_rest,distance)
assert maximum_rest<1e-5,maximum_rest
maximum_error=0
for time in sorted({row['time'] for row in witness}):
    bpy.context.scene.frame_set(1+round(time*120))
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    for row in witness:
        if row['time']!=time:continue
        expected=C@Vector(row['posed']);actual=mesh.vertices[row['index']].co
        maximum_error=max(maximum_error,(actual-expected).length)
    evaluated.to_mesh_clear()
result={'sha256':hashlib.sha256((master/'kai.glb').read_bytes()).hexdigest(),
    'blendSha256':hashlib.sha256((master/'kai.blend').read_bytes()).hexdigest(),
    'witnessVertices':len(witness),'poses':5,'maximumRestMatchError':maximum_rest,'maximumPositionError':maximum_error}
assert maximum_error<.0001,'Three.js must match Blender within 0.1 mm.'
(out/'blender-parity.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
