"""Round Ada's retained distal finger edges, without replacing either hand."""
from pathlib import Path
import json
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/ada'
mesh=trimesh.load(OUT/'refined-body.ply');source=mesh.vertices.copy()
anatomy=json.loads((ROOT/'art/characters/candidates/ada/anatomy.json').read_text())
smoothed=mesh.copy();trimesh.smoothing.filter_taubin(smoothed,lamb=.48,nu=.52,iterations=12)
def ramp(a,b,q):
 t=np.clip((q-a)/(b-a),0,1);return t*t*(3-2*t)
def distance(a,b):
 a=np.asarray(a);b=np.asarray(b);d=b-a
 t=np.clip((source-a)@d/(d@d),0,1)
 return np.linalg.norm(source-a-t[:,None]*d,axis=1)
weight=np.zeros(len(source))
for k in ('L','R'):
 a=anatomy['sides'][k]
 finger=distance(a['knuckle'],a['fingerTip']);thumb=distance(a['thumbBase'],a['thumbTip'])
 w=ramp(.003,.010,thumb-finger)*(1-ramp(.013,.027,finger))
 w*=ramp(a['fingerJoint'][1]+.005,a['fingerJoint'][1]-.010,source[:,1])
 weight=np.maximum(weight,w)
change=(smoothed.vertices-source)*weight[:,None]
length=np.linalg.norm(change,axis=1);change*=np.minimum(1,.0011/np.maximum(length,1e-12))[:,None]
mesh.vertices=source+change;assert mesh.is_watertight;mesh.export(OUT/'authored-body.ply')
(OUT/'hand-refinement.json').write_text(json.dumps({'method':'Bounded source-local distal finger rounding; measured thumb branch excluded; original joined-finger topology retained','maximumSourceDisplacement':float(np.linalg.norm(change,axis=1).max()),'maximumRigDisplacement':float(np.linalg.norm(change,axis=1).max()*1.8)},indent=2)+'\n')
