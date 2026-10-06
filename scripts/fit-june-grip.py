"""Fit a handle inside the original mitten using only rigid joint rotations."""
import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
from scipy.optimize import differential_evolution, minimize
ROOT=Path(__file__).resolve().parents[1]/'validation/reconstruction/fresh-rig'
data=json.loads((ROOT/'grip-input.json').read_text());names=['hand','mitt','mittTip','thumb','thumbTip']
rest=[np.array(data['bones'][n]).reshape(4,4).T for n in names];inv=[np.linalg.inv(m) for m in rest]
p=np.array([d['p'] for d in data['points']]);w=np.array([[d['weights'].get(n,0) for n in names] for d in data['points']]);src=np.array([d['source'] for d in data['points']])
def product(a,b):
 return np.concatenate((a[...,3,None]*b[...,:3]+b[...,3,None]*a[...,:3]+np.cross(a[...,:3],b[...,:3]),(a[...,3]*b[...,3]-(a[...,:3]*b[...,:3]).sum(-1))[...,None]),axis=-1)
def pose(x):
 matrices=[np.eye(4)]
 for i,parent in [(1,0),(2,1),(3,0),(4,3)]:
  rot=np.eye(4);rot[:3,:3]=Rotation.from_euler('XYZ',[-x[2],x[3],x[4]]).as_matrix() if i==3 else Rotation.from_rotvec([-1.137025 if i==4 else -x[i-1],0,0]).as_matrix()
  matrices.append(matrices[parent]@rest[i]@rot@inv[i])
 real=np.array([Rotation.from_matrix(m[:3,:3]).as_quat() for m in matrices]);trans=np.array([np.r_[m[:3,3],0] for m in matrices]);dual=.5*product(trans,real)
 signs=np.where(real[w.argmax(1)]@real.T<0,-1,1);wr=w*signs
 qr=wr@real;qd=wr@dual;length=np.linalg.norm(qr,axis=1);qr/=length[:,None];qd/=length[:,None]
 shift=2*product(qd,qr*np.array([-1,-1,-1,1]))[:,:3]
 return p+2*np.cross(qr[:,:3],np.cross(qr[:,:3],p)+qr[:,3,None]*p)+shift
# The resting hand faces inward. Local Z is the back of the hand; X
# runs across the knuckles. Contact sets refer to that anatomy, not front Z.
palm=(src[:,1]>-.040)&(src[:,1]<-.020)&(src[:,0]<.198)&(src[:,2]<.028)
finger=(src[:,1]<-.085);thumb=(src[:,0]<.196)&(src[:,1]<-.045)&(src[:,2]>.023)
tri=np.array(data['triangles']);radius=.020

def clearance(v,centre):
 a=v[tri,1:]-centre;b=np.roll(a,-1,axis=1);edge=b-a
 cross=a[:,:,0]*b[:,:,1]-a[:,:,1]*b[:,:,0]
 inside=(np.all(cross>=0,axis=1)|np.all(cross<=0,axis=1))
 t=np.clip(-np.sum(a*edge,axis=2)/np.maximum(np.sum(edge*edge,axis=2),1e-20),0,1)
 distance=np.linalg.norm(a+t[:,:,None]*edge,axis=2).min(1)
 return np.where(inside,0,distance)-radius

def objective(x):
 v=pose(x);d=v[:,1:]-x[5:7]
 penetration=np.minimum(clearance(v,x[5:7])-.0008,0)
 loss=5e5*np.sum(penetration**2)
 for mask,angle in [(palm,np.pi/2),(finger,-np.pi/3),(thumb,-5*np.pi/6)]:
  target=(radius+.001)*np.array([np.cos(angle),np.sin(angle)])
  dist=np.linalg.norm(d[mask]-target,axis=1)
  loss+=10000*np.min(dist)**2
 loss+=.05*np.sum((x[:5]-[1.1,1.1,.5,0,0])**2)
 return loss

if __name__=='__main__':
 bounds=[(.5,1.45),(.3,1.75),(-.5,1.5),(-1.3,1.3),(-1.3,1.3),(.096,.115),(-.060,-.020)]
 r=differential_evolution(objective,bounds,seed=3,popsize=12,maxiter=280,tol=.0001,polish=True)
 x=r.x;v=pose(x);gap=clearance(v,x[5:7])
 report={'parameters':x.tolist(),'loss':r.fun,'minimumSurfaceClearance':float(gap.min()),'contactTrianglesWithin3mm':int((abs(gap)<.003).sum()),'vertices':len(p)}
 (ROOT/'grip-fit.json').write_text(json.dumps(report,indent=2));print(report)
