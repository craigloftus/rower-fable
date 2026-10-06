"""Fair micro-ripples while keeping the bun and swept hair's stronger folds."""
from pathlib import Path
import numpy as np
import trimesh
from trimesh.smoothing import filter_taubin
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/june-final'
mesh=trimesh.load(OUT/'retopology.ply')
scalp=mesh.copy()
filter_taubin(scalp,lamb=.5,nu=.53,iterations=8)
filter_taubin(mesh,lamb=.5,nu=.53,iterations=26)
p=mesh.vertices
hair=np.clip((p[:,1]-.425)/.013,0,1)
hair=np.maximum(hair,np.clip((p[:,1]-.401)/.023,0,1)*np.clip((.013-p[:,2])/.025,0,1))
mesh.vertices=mesh.vertices*(1-hair[:,None])+scalp.vertices*hair[:,None]
mesh.export(OUT/'refined-surface.ply')
print('Prepared local sculpt planes',flush=True)
