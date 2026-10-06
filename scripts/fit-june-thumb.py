"""Fit the retained thumb around a fixed grip without spreading its skin.
Run fit-june-grip.mjs after binding to refresh the anatomical hand sample.
The palm, joined fingers, wrist pose and handle location stay fixed here.
"""
import json
import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
from scipy.optimize import differential_evolution

ROOT=Path(__file__).resolve().parents[1]/'validation/reconstruction/fresh-rig'
data=json.loads((ROOT/'grip-input.json').read_text())
names=['hand','mitt','mittTip','thumb','thumbTip']
rest=[np.array(data['bones'][n]).reshape(4,4).T for n in names]
inv=[np.linalg.inv(m) for m in rest]
p=np.array([d['p'] for d in data['points']])
w=np.array([[d['weights'].get(n,0) for n in names] for d in data['points']])
src=np.array([d['source'] for d in data['points']])
tri=np.array(data['triangles'])
centre=np.array([0,.099,-.04988]);radius=.020
thumb=(src[:,0]<.199)&(src[:,1]<-.042)&(src[:,2]>.023)
tip=thumb&(src[:,1]<-.058)
edges=np.unique(np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1),axis=0)
edges=edges[np.any(w[edges,3:].sum(2)>.01,axis=1)]
length=np.linalg.norm(p[edges[:,1]]-p[edges[:,0]],axis=1)

def product(a,b):
 return np.concatenate((a[...,3,None]*b[...,:3]+b[...,3,None]*a[...,:3]+np.cross(a[...,:3],b[...,:3]),(a[...,3]*b[...,3]-(a[...,:3]*b[...,:3]).sum(-1))[...,None]),axis=-1)

def pose(x):
 matrices=[np.eye(4)]
 rotations=[[-.600969,0,0],[-.71866,0,0],[-x[0],x[1],x[2]],[-x[3],0,0]]
 for i,parent in [(1,0),(2,1),(3,0),(4,3)]:
  rot=np.eye(4);rot[:3,:3]=Rotation.from_euler('XYZ',rotations[i-1]).as_matrix()
  matrices.append(matrices[parent]@rest[i]@rot@inv[i])
 real=np.array([Rotation.from_matrix(m[:3,:3]).as_quat() for m in matrices])
 trans=np.array([np.r_[m[:3,3],0] for m in matrices]);dual=.5*product(trans,real)
 signs=np.where(real[w.argmax(1)]@real.T<0,-1,1);wr=w*signs
 qr=wr@real;qd=wr@dual;norm=np.linalg.norm(qr,axis=1);qr/=norm[:,None];qd/=norm[:,None]
 shift=2*product(qd,qr*np.array([-1,-1,-1,1]))[:,:3]
 return p+2*np.cross(qr[:,:3],np.cross(qr[:,:3],p)+qr[:,3,None]*p)+shift

def clearance(v):
 a=v[tri,1:]-centre[1:];b=np.roll(a,-1,axis=1);edge=b-a
 cross=a[:,:,0]*b[:,:,1]-a[:,:,1]*b[:,:,0]
 inside=np.all(cross>=0,axis=1)|np.all(cross<=0,axis=1)
 t=np.clip(-np.sum(a*edge,axis=2)/np.maximum(np.sum(edge*edge,axis=2),1e-20),0,1)
 distance=np.linalg.norm(a+t[:,:,None]*edge,axis=2).min(1)
 return np.where(inside,0,distance)-radius

def objective(x):
 v=pose(x)
 penetration=np.minimum(clearance(v)-.0002,0)
 loss=1e6*np.sum(penetration**2)
 target=centre+np.array([.038,-.013,-.017])
 loss+=15000*np.min(np.linalg.norm(v[tip]-target,axis=1))**2
 # A point of contact is insufficient if the web becomes a stretched flap.
 ratio=np.linalg.norm(v[edges[:,1]]-v[edges[:,0]],axis=1)/length
 loss+=15*np.sum(np.maximum(ratio-1.25,0)**2+np.minimum(ratio-.75,0)**2)
 loss+=.15*np.sum((x-[.8,0,0,.7])**2)
 return loss

if __name__=='__main__':
 result=differential_evolution(objective,[(0,1.6),(-.7,.7),(-.8,.8),(0,1.5)],seed=7,popsize=12,maxiter=220,tol=.0001,polish=True)
 x=result.x;v=pose(x)
 report={'parameters':x.tolist(),'loss':result.fun,'minimumSurfaceClearance':float(clearance(v).min()),'maximumThumbEdgeStretch':float((np.linalg.norm(v[edges[:,1]]-v[edges[:,0]],axis=1)/length).max())}
 (ROOT/'thumb-fit.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
