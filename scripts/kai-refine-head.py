"""Author broad facial planes on Kai's closed source, keeping landmarks intact."""
from pathlib import Path
import json
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/kai'
m=trimesh.load(OUT/'head-faceted-surface.ply');p=m.vertices.copy();x,y,z=p.T
smooth=m.copy();trimesh.smoothing.filter_taubin(smooth,lamb=.45,nu=.50,iterations=12)
def ramp(a,b,q):
 t=np.clip((q-a)/(b-a),0,1);return t*t*(3-2*t)
face=ramp(.07,.12,z)*(1-ramp(.15,.20,y))
features=np.maximum(np.exp(-((y+.10)/.026)**2)*np.exp(-(x/.07)**2),np.exp(-((y-.015)/.045)**2)*np.exp(-((abs(x)-.082)/.05)**2))
weight=np.maximum(face*(1-.8*features),ramp(.13,.17,y)*.55)
weight=np.maximum(weight,(1-ramp(-.24,-.17,y))*.9)
p+=(smooth.vertices-p)*weight[:,None]
x,y,z=p.T
# Two deliberate cheek planes fill the inferred hollows without replacing
# the source nose, eye rims, mouth or jaw contour.
cheek=ramp(.055,.085,abs(x))*(1-ramp(.165,.19,abs(x)))*ramp(-.165,-.11,y)*(1-ramp(.02,.065,y))*ramp(.06,.11,z)
plane=.235-.48*abs(x)+.08*y
p[:,2]+=cheek*np.maximum(plane-z,0)
# Broad forehead plane; retain the brow ridge and original hairline silhouette.
fore=ramp(.075,.10,y)*(1-ramp(.13,.165,y))*(1-ramp(.145,.18,abs(x)))*ramp(.12,.18,z)
p[:,2]+=fore*((.252-.28*abs(x))-p[:,2])
m.vertices=p;m.fix_normals();assert m.is_watertight
m.export(OUT/'head-authored-surface.ply')
(OUT/'head-authoring.json').write_text(json.dumps({'source':'head-faceted-surface.ply','method':'Local Taubin cleanup, bilateral cheek and forehead planes; retained source features','maximumSourceDisplacement':float(np.linalg.norm(p-trimesh.load(OUT/'head-faceted-surface.ply').vertices,axis=1).max())},indent=2)+'\n')
