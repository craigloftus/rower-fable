"""Author quiet cheek and forehead planes on Sol's closed source geometry."""
from pathlib import Path
import json,sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/sol'
mesh=trimesh.load(OUT/'head-faceted-surface.ply');source=mesh.vertices.copy();x,y,z=source.T
if '--pack-mask' in sys.argv:
 samples=np.load(OUT/'head-colour-samples.npz');_,ids=cKDTree(samples['positions']).query(source,k=5)
 skin=samples['colors'][ids,0].mean(axis=1)>110
 np.savez_compressed(OUT/'head-plane-mask.npz',skin=skin)
else:
 skin=np.load(OUT/'head-plane-mask.npz')['skin']
assert len(skin)==len(source)

def ramp(a,b,q):
 t=np.clip((q-a)/(b-a),0,1);return t*t*(3-2*t)

smoothed=mesh.copy();trimesh.smoothing.filter_taubin(smoothed,lamb=.42,nu=.48,iterations=8)
face=ramp(.12,.20,z)*skin
features=np.maximum(np.exp(-((y+.165)/.035)**2)*np.exp(-((x-.01)/.09)**2),
 np.exp(-((y-.05)/.055)**2)*np.exp(-((abs(x-.01)-.10)/.07)**2))
features=np.maximum(features,np.exp(-((x-.01)/.055)**2)*np.exp(-((y+.07)/.10)**2))
weight=face*(1-.85*features)*.75
p=source+(smoothed.vertices-source)*weight[:,None]
x,y,z=p.T
# Measured source cheek medians are ~.22–.24, with a .33 nose. Broad diagonal
# planes keep the cheeks distinct from the retained nose and tapered jaw.
cheek=ramp(.085,.125,abs(x-.009))*(1-ramp(.20,.245,abs(x-.009)))*ramp(-.22,-.16,y)*(1-ramp(-.015,.035,y))*ramp(.16,.22,z)*skin
plane=.330-.55*abs(x-.009)+.13*y
p[:,2]+=cheek*.80*np.clip(plane-z,-.020,.025)
fore=ramp(.12,.155,y)*(1-ramp(.22,.26,y))*(1-ramp(.14,.19,abs(x-.009)))*ramp(.23,.28,z)*skin
p[:,2]+=fore*.8*((.316-.25*abs(x-.009))-p[:,2])
mesh.vertices=p;mesh.fix_normals();assert mesh.is_watertight
mesh.export(OUT/'head-authored-surface.ply')
(OUT/'head-refinement.json').write_text(json.dumps({'method':'Measured cheek/forehead planes and local Taubin cleanup; retained source nose, rims, mouth, jaw and hair silhouette','maximumSourceDisplacement':float(np.linalg.norm(p-source,axis=1).max())},indent=2)+'\n')
