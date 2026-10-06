"""Remove local forehead closure noise while preserving Ada's source topology."""
from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.sparse import coo_matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/ada'
mesh=trimesh.load(OUT/'head-faceted-surface.ply');source=mesh.vertices.copy();x,y,z=source.T

def soft(a,b,t):
 t=np.clip((t-a)/(b-a),0,1);return t*t*(3-2*t)
weight=soft(.09,.125,y)*(1-soft(.235,.27,y))*(1-soft(.15,.24,abs(x)))*soft(.23,.29,z)
e=mesh.edges_unique;r=np.r_[e[:,0],e[:,1]];c=np.r_[e[:,1],e[:,0]]
a=coo_matrix((np.ones(len(r)),(r,c)),shape=(len(source),len(source))).tocsr();degree=np.asarray(a.sum(axis=1)).ravel()
for _ in range(32):
 for factor in [.48,-.49]:
  mesh.vertices+=factor*weight[:,None]*(a@mesh.vertices/degree[:,None]-mesh.vertices)
  delta=mesh.vertices-source;length=np.linalg.norm(delta,axis=1)
  mesh.vertices=source+delta*np.minimum(1,.018/np.maximum(length,1e-12))[:,None]
# The measured forehead samples form a broad crown (.373 at brow, .361
# above centre), turning back toward the temples. Replace only closure ripples;
# the eye creases, cheeks and mouth are outside this mask.
p=mesh.vertices.copy();x,y,z=p.T
fore=soft(.085,.115,y)*(1-soft(.225,.25,y))*(1-soft(.145,.205,abs(x)))*soft(.25,.30,z)
plane=.389-.125*y-.95*x*x-.30*np.maximum(abs(x)-.10,0)
p[:,2]+=fore*np.clip(plane-z,-.025,.025)
# The original has close clustered curls. Reduce the single protruding central
# curl without moving the crown height or changing the surrounding clusters.
curl=np.exp(-((x-.005)/.064)**4)*np.exp(-((y-.294)/.054)**4)*soft(.31,.35,z)
p[:,2]-=.018*curl
p[:,1]+=.010*curl*(1-soft(.275,.31,y))
mesh.vertices=p
assert mesh.is_watertight
mesh.export(OUT/'head-authored-surface.ply')
(OUT/'head-refinement.json').write_text(json.dumps({'method':'Bounded local forehead crown fit and central curl reduction; original cheek creases, nose, lips and jaw retained','maximumSourceDisplacement':float(np.linalg.norm(mesh.vertices-source,axis=1).max()),'triangles':len(mesh.faces)},indent=2)+'\n')
