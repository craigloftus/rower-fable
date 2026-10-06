"""Verify the exported neck joins and preservation of the approved sculpt."""
from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

root=Path(__file__).resolve().parents[1]/'validation/reconstruction/trellis-assembled'
scene=trimesh.load(root/'mesh.glb')
before=trimesh.load(root/'before-neck.glb')
neck=scene.geometry['Neck transition']
assert np.isfinite(neck.vertices).all()
assert neck.is_winding_consistent
assert neck.area_faces.min()>1e-12

def edge_key(a,b):return tuple(sorted((tuple(np.round(a,7)),tuple(np.round(b,7)))))
# Every edge at either end of the new tube must have a matching source edge.
counts={}
for mesh in scene.geometry.values():
    for face in mesh.faces:
        p=mesh.vertices[face]
        for a,b in zip(p,np.roll(p,-1,axis=0)):
            if any(abs(a[1]-y)<1e-7 and abs(b[1]-y)<1e-7 for y in (.307,.318)):
                key=edge_key(a,b);counts[key]=counts.get(key,0)+1
joins=[]
for y,name in [(.307,'Skin hair and shoes'),(.318,'Head')]:
    points=neck.vertices[abs(neck.vertices[:,1]-y)<1e-7]
    gap=float(cKDTree(scene.geometry[name].vertices).query(points)[0].max())
    assert gap<1e-7
    keys=set()
    for edge in neck.edges:
        a,b=neck.vertices[edge]
        if abs(a[1]-y)<1e-7 and abs(b[1]-y)<1e-7:keys.add(edge_key(a,b))
    assert all(counts[key]==2 for key in keys),'Unmatched or overlapping join edge'
    joins.append({'height':y,'vertices':len(points),'edges':len(keys),'maximumGap':gap})
body_error=0
for name,old in before.geometry.items():
    if name=='Head':continue
    points=old.vertices[old.vertices[:,1]<.307-1e-7]
    body_error=max(body_error,float(cKDTree(scene.geometry[name].vertices).query(points)[0].max()))
assert body_error<1e-7
old=before.geometry['Head'];points=old.vertices[old.vertices[:,1]>.330+1e-7]+[0,-.012,.006]
head_error=float(cKDTree(scene.geometry['Head'].vertices).query(points)[0].max())
assert head_error<1e-7
report={'joins':joins,'neckWindingConsistent':True,'neckTriangles':len(neck.faces),
        'bodyOutsideJoinMaximumChange':body_error,'headShapeMaximumChangeAfterPlacement':head_error,
        'headPlacementChange':[0,-.012,.006],
        'trianglesBefore':sum(len(m.faces) for m in before.geometry.values()),
        'trianglesAfter':sum(len(m.faces) for m in scene.geometry.values())}
(root/'neck-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
