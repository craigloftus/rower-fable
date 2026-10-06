"""Fit Kai's retained hands with rigid rotations and measured web strain."""
from pathlib import Path
import json,sys
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.optimize import differential_evolution
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/kai'
side=sys.argv[1];data=json.loads((OUT/f'grip-input-{side}.json').read_text())
names=['hand','mitt','mittTip','thumb','thumbTip'];anatomy=data['anatomy']
rest=[np.array(data['bones'][n]).reshape(4,4).T for n in names];inv=[np.linalg.inv(m) for m in rest]
p=np.array([d['p'] for d in data['points']]);src=np.array([d['source'] for d in data['points']])
w=np.array([[d['weights'].get(n,0) for n in names] for d in data['points']]);tri=np.array(data['triangles'])
edges=np.unique(np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1),axis=0)
length=np.linalg.norm(p[edges[:,1]]-p[edges[:,0]],axis=1)
def segment_distance(points,a,b):
    a=np.asarray(anatomy[a]);b=np.asarray(anatomy[b]);d=b-a
    t=np.clip((points-a)@d/np.dot(d,d),0,1)
    return np.linalg.norm(points-a-t[:,None]*d,axis=1)
thumb=(segment_distance(src,'thumbBase','thumbTip')<segment_distance(src,'knuckle','fingerTip'))&(src[:,1]<anatomy['thumbBase'][1])&(src[:,1]>anatomy['thumbTip'][1]-.008)&(abs(src[:,0])<anatomy['thumbOuterX'])
finger=(src[:,1]<anatomy['fingerJoint'][1]+.005)&~thumb
palm=(src[:,1]<anatomy['wrist'][1]-.006)&(src[:,1]>anatomy['knuckle'][1]+.003)&~thumb
# The full validator includes every edge of a triangle touching the thumb.
thumb_faces=tri[thumb[tri].any(axis=1)]
thumb_keys={tuple(e) for e in np.sort(np.concatenate([thumb_faces[:,[0,1]],thumb_faces[:,[1,2]],thumb_faces[:,[2,0]]]),axis=1)}
thumb_edges=np.array([tuple(e) in thumb_keys for e in edges])
def product(a,b):
    return np.concatenate((a[...,3,None]*b[...,:3]+b[...,3,None]*a[...,:3]+np.cross(a[...,:3],b[...,:3]),(a[...,3]*b[...,3]-(a[...,:3]*b[...,:3]).sum(-1))[...,None]),axis=-1)
def pose(x):
    matrices=[np.eye(4)];sign=1 if side=='L' else -1
    rotations=[[-x[0],0,0],[-x[1],0,0],[-x[2],sign*x[4],sign*x[5]],[-x[3],0,0]]
    for i,parent in [(1,0),(2,1),(3,0),(4,3)]:
        rot=np.eye(4);rot[:3,:3]=Rotation.from_euler('XYZ',rotations[i-1]).as_matrix()
        matrices.append(matrices[parent]@rest[i]@rot@inv[i])
    real=np.array([Rotation.from_matrix(m[:3,:3]).as_quat() for m in matrices])
    trans=np.array([np.r_[m[:3,3],0] for m in matrices]);dual=.5*product(trans,real)
    signs=np.where(real[w.argmax(1)]@real.T<0,-1,1);wr=w*signs
    qr=wr@real;qd=wr@dual;norm=np.linalg.norm(qr,axis=1);qr/=norm[:,None];qd/=norm[:,None]
    shift=2*product(qd,qr*np.array([-1,-1,-1,1]))[:,:3]
    return p+2*np.cross(qr[:,:3],np.cross(qr[:,:3],p)+qr[:,3,None]*p)+shift
def clearance(v,centre):
    a=v[tri,1:]-centre;b=np.roll(a,-1,axis=1);edge=b-a
    cross=a[:,:,0]*b[:,:,1]-a[:,:,1]*b[:,:,0]
    inside=np.all(cross>=0,axis=1)|np.all(cross<=0,axis=1)
    t=np.clip(-np.sum(a*edge,axis=2)/np.maximum(np.sum(edge*edge,axis=2),1e-20),0,1)
    distance=np.linalg.norm(a+t[:,:,None]*edge,axis=2).min(1)
    return np.where(inside,0,distance)-.020
centroids=src[tri].mean(1)
ct=(segment_distance(centroids,'thumbBase','thumbTip')<segment_distance(centroids,'knuckle','fingerTip'))&(centroids[:,1]<anatomy['thumbBase'][1])&(centroids[:,1]>anatomy['thumbTip'][1]-.008)&(abs(centroids[:,0])<anatomy['thumbOuterX'])
cp=(centroids[:,1]<anatomy['wrist'][1]-.006)&(centroids[:,1]>anatomy['knuckle'][1]+.003)&~ct
cf=(centroids[:,1]<anatomy['fingerJoint'][1]+.005)&~ct
def objective(x):
    v=pose(x);gap=clearance(v,x[6:8]);loss=1e6*np.sum(np.minimum(gap-.0002,0)**2)
    for mask,angle in [(palm,np.pi/2),(finger,-np.pi/3),(thumb,-5*np.pi/6)]:
        target=x[6:8]+.0205*np.array([np.cos(angle),np.sin(angle)])
        loss+=(3000 if mask is thumb else 25000)*np.min(np.linalg.norm(v[mask,1:]-target,axis=1))**2
        loss+=(150000 if mask is thumb else 1500000)*np.min(np.abs(np.linalg.norm(v[mask,1:]-x[6:8],axis=1)-.0205))**2
    ratio=np.linalg.norm(v[edges[:,1]]-v[edges[:,0]],axis=1)/length
    excess=np.maximum(ratio[thumb_edges]-1.35,0)
    loss+=5000*np.max(excess)**2+50*np.sum(excess**2)
    for mask in (cp,cf,ct):loss+=1e7*(gap[mask].min()-.0004)**2
    loss+=.01*np.sum((x[:6]-[1,1,.4,.4,0,0])**2)
    return loss
bounds=[(.15,1.6),(.15,1.8),(-.5,1.5),(0,1.4),(-.8,.8),(-.8,.8),(.045,.10),(-.085,-.020)]
result=differential_evolution(objective,bounds,seed=12,popsize=10,maxiter=360,tol=.0002,polish=True)
x=result.x;v=pose(x);gap=clearance(v,x[6:8]);ratio=np.linalg.norm(v[edges[:,1]]-v[edges[:,0]],axis=1)/length
report={'side':side,'parameters':x.tolist(),'loss':float(result.fun),'minimumSurfaceClearance':float(gap.min()),
    'maximumThumbEdgeStretch':float(ratio[thumb_edges].max()),'contactTrianglesWithin3mm':int((abs(gap)<.003).sum())}
(OUT/f'grip-fit-{side}.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
