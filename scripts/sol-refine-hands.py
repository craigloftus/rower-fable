"""Round the reconstructed outside knuckle locally; retain both complete hands."""
from pathlib import Path
import json
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/sol'
mesh=trimesh.load(OUT/'refined-body.ply');source=mesh.vertices.copy()
smoothed=mesh.copy();trimesh.smoothing.filter_taubin(smoothed,lamb=.48,nu=.52,iterations=12)
centre=np.array([.22279,-.08602,-.00553]);distance=np.linalg.norm((source-centre)/np.array([.013,.014,.013]),axis=1)
weight=np.maximum(0,1-distance**2)**2
change=(smoothed.vertices-source)*weight[:,None]
length=np.linalg.norm(change,axis=1);change*=np.minimum(1,.0011/np.maximum(length,1e-12))[:,None]
mesh.vertices=source+change;assert mesh.is_watertight;mesh.export(OUT/'authored-body.ply')
(OUT/'hand-refinement.json').write_text(json.dumps({'source':'refined-body.ply','region':'Left outside finger joint; original thumb and distal finger tips retained','maximumSourceDisplacement':float(np.linalg.norm(change,axis=1).max()),'maximumRigDisplacement':float(np.linalg.norm(change,axis=1).max()*1.8),'method':'Local Taubin rounding, capped at 1.1mm source / 1.98mm rig; no replacement geometry'},indent=2)+'\n')
