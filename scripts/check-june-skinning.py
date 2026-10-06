"""Check the review's DQ calculation against Blender's Preserve Volume output."""
import bpy
import json
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

root=Path(__file__).resolve().parents[1]
out=root/'validation/rig-audit'
bpy.ops.wm.open_mainfile(filepath=str(root/'art/characters/reference/june-final-rig.blend'))
obj=bpy.data.objects['june'];modifier=obj.modifiers['Rowing deform']
C=Matrix(((1,0,0),(0,0,-1),(0,1,0)))
tree=KDTree(len(obj.data.vertices))
for vertex in obj.data.vertices:tree.insert(vertex.co,vertex.index)
tree.balance()
witness=json.loads((out/'witness.json').read_text())
maximum_rest=0
for row in witness:
    _,index,distance=tree.find(C@Vector(row['rest']))
    row['index']=index;maximum_rest=max(maximum_rest,distance)
assert maximum_rest<1e-5,maximum_rest
errors={'linear':0.,'dualQuaternion':0.}
for time in sorted({row['time'] for row in witness}):
    bpy.context.scene.frame_set(1+round(time*120))
    rows=[row for row in witness if row['time']==time]
    for name,key,preserve in [('linear','lbs',False),('dualQuaternion','dq',True)]:
        modifier.use_deform_preserve_volume=preserve
        bpy.context.view_layer.update()
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
        for row in rows:
            expected=C@Vector(row[key]);actual=mesh.vertices[row['index']].co
            errors[name]=max(errors[name],(actual-expected).length)
        evaluated.to_mesh_clear()
result={'witnessVertices':len(witness),'poses':5,'maximumRestMatchError':maximum_rest,'maximumPositionError':errors}
(out/'blender-parity.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
assert max(errors.values())<.0001,'The diagnostic renderer must match Blender within 0.1 mm.'
