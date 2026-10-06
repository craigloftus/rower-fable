"""Repair the approved head without voxelising or smoothing its facial form."""
from pathlib import Path
import json
import numpy as np
import trimesh
import pymeshfix
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/june-final'
source=trimesh.load(ROOT/'validation/reconstruction/trellis-assembled/mesh.glb').geometry['Head']
source=trimesh.Trimesh(source.vertices,source.faces,process=True)
print('Repairing native head:',len(source.faces),'triangles',flush=True)
v,f=pymeshfix.clean_from_arrays(np.asarray(source.vertices,dtype=np.float64),np.asarray(source.faces,dtype=np.int32),joincomp=True,remove_smallest_components=True)
mesh=trimesh.Trimesh(v,f,process=True)
print('Repaired:',len(mesh.faces),'watertight',mesh.is_watertight,'volume',mesh.volume,flush=True)
mesh.export(OUT/'repaired-head.ply')
(OUT/'head-repair-report.json').write_text(json.dumps({'triangles':len(mesh.faces),'watertight':mesh.is_watertight,'volume':mesh.volume},indent=2))
