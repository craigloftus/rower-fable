"""Join the rebuilt body and fine head with shared continuous neck boundaries."""
from pathlib import Path
import numpy as np
import trimesh
from neck_join import clip,section_loops,bridge
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/june-final'
body=trimesh.load(OUT/'faceted-surface.ply');head=trimesh.load(OUT/'sculpted-head.ply')
for mesh in [body,head]:
    mesh.visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(mesh.vertices),2)),material=trimesh.visual.material.PBRMaterial(baseColorFactor=[255,255,255,255]))
body,lower=clip(body,.307,False)
head,upper=clip(head,.322,True)
neck=bridge(section_loops(lower)[0],section_loops(upper)[0])
mesh=trimesh.util.concatenate([body,head,neck])
mesh=trimesh.Trimesh(mesh.vertices,mesh.faces,process=True)
mesh.export(OUT/'sculpt-surface.ply')
print('Joined rebuilt sculpt:',len(mesh.faces),'triangles',flush=True)
