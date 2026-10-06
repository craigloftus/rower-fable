"""Check measured pivots against the closed standing source with triangle rays."""
from pathlib import Path
import json
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/ada'
m=trimesh.load(OUT/'authored-body.ply');a=json.loads((ROOT/'art/characters/candidates/ada/anatomy.json').read_text())
t=m.triangles;edge1=t[:,1]-t[:,0];edge2=t[:,2]-t[:,0]
direction=np.array([1,.01231,.00747]);direction/=np.linalg.norm(direction)
h=np.cross(direction,edge2);det=np.sum(edge1*h,axis=1);valid=np.abs(det)>1e-12
f=np.zeros_like(det);f[valid]=1/det[valid]
def inside(p):
 s=np.asarray(p)-t[:,0];u=f*np.sum(s*h,axis=1);q=np.cross(s,edge1)
 v=f*np.sum(q*direction,axis=1);distance=f*np.sum(edge2*q,axis=1)
 return bool(np.count_nonzero(valid&(u>=0)&(v>=0)&(u+v<=1)&(distance>1e-8))%2)
report={}
for k,side in a['sides'].items():
 for name in ['hip','knee','ankle','clavicle','shoulder','elbow','wrist','knuckle','fingerJoint','fingerTip','thumbBase','thumbJoint','thumbTip']:
  report[name+k]={'source':side[name],'inside':inside(side[name])}
(OUT/'landmarks.json').write_text(json.dumps(report,indent=2)+'\n')
print('Outside landmarks:',[name for name,r in report.items() if not r['inside']])
