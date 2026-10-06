"""Measure the reconstructed source before choosing anatomical landmarks."""
from pathlib import Path
import json
import numpy as np
import trimesh
from trimesh.visual.color import uv_to_color

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/sol'
mesh=trimesh.load(OUT/'reconstructed.glb',force='mesh',process=False)
print('bounds',mesh.bounds,'vertices',len(mesh.vertices),'faces',len(mesh.faces),flush=True)
colors=uv_to_color(mesh.visual.uv,mesh.visual.material.baseColorTexture)
mesh.export(OUT/'source.ply')
p=mesh.vertices
rows=[]
for height in np.arange(-.48,.501,.02):
    bands=[]
    for xlo,xhi in [(-.5,-.12),(-.12,0),(0,.12),(.12,.5)]:
        ids=np.flatnonzero((abs(p[:,1]-height)<.007)&(p[:,0]>=xlo)&(p[:,0]<xhi))
        if len(ids):bands.append({'xRange':[xlo,xhi],'vertices':len(ids),'mean':p[ids].mean(axis=0).tolist(),'bounds':[p[ids].min(axis=0).tolist(),p[ids].max(axis=0).tolist()],'rgb':np.median(colors[ids,:3],axis=0).tolist()})
    rows.append({'height':round(float(height),3),'bands':bands})
topology=trimesh.Trimesh(mesh.vertices,mesh.faces,process=True)
components=topology.split(only_watertight=False)
report={'bounds':mesh.bounds.tolist(),'triangles':len(mesh.faces),'vertices':len(mesh.vertices),
    'watertight':topology.is_watertight,'windingConsistent':topology.is_winding_consistent,'volume':float(topology.volume),
    'components':sorted([len(m.faces) for m in components],reverse=True),'sections':rows}
(OUT/'source-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
np.savez_compressed(OUT/'source-samples.npz',positions=p,colors=colors,faces=mesh.faces)
print({key:value for key,value in report.items() if key!='sections'},flush=True)
