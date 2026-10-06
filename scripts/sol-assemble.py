"""Join Sol's detailed original-reference head to the cleaned body at neck loops."""
from pathlib import Path
import json
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial
from scipy.sparse import coo_matrix
from neck_join import clip,section_loops,bridge

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/sol'
body=trimesh.load(OUT/'authored-body.ply');head=trimesh.load(OUT/'head-refined-surface.ply')
material=PBRMaterial(name='Sol neutral sculpt',baseColorFactor=[145,126,100,255],metallicFactor=0,roughnessFactor=.9)
for mesh in (body,head):mesh.visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(mesh.vertices),2)),material=material)
scale=.146/(head.bounds[1,0]-head.bounds[0,0])
translation=np.array([0,.497-head.bounds[1,1]*scale,0.])
head.apply_scale(scale);head.apply_translation(translation)
body,body_edges=clip(body,.318,above=False)
head,head_edges=clip(head,.328,above=True)
body_loop=section_loops(body_edges)[0];head_loop=section_loops(head_edges)[0]
shift=body_loop[:,0].mean(axis=0)-head_loop[:,0].mean(axis=0);shift[1]=0
head.apply_translation(shift);head_loop[:,0]+=shift;translation+=shift
neck=bridge(body_loop,head_loop)
sculpt=trimesh.util.concatenate([body,neck,head]);sculpt.merge_vertices(digits_vertex=7,merge_norm=True,merge_tex=True);sculpt.fix_normals()
# Blend the closed bridge into both measured neck sections. Keep the jaw and
# shoulder silhouette outside this narrow band unchanged.
v=sculpt.vertices.copy();w=np.exp(-((v[:,1]-.327)/.012)**4)
e=sculpt.edges_unique;r=np.r_[e[:,0],e[:,1]];c=np.r_[e[:,1],e[:,0]]
a=coo_matrix((np.ones(len(r)),(r,c)),shape=(len(v),len(v))).tocsr();d=np.asarray(a.sum(axis=1)).ravel()
for _ in range(12):sculpt.vertices+=.45*w[:,None]*(a@sculpt.vertices/d[:,None]-sculpt.vertices)
assert sculpt.is_watertight,'The assembled neck must close the body and head.'
sculpt.export(OUT/'assembled-surface.ply');sculpt.export(OUT/'assembled-neutral.glb')
(OUT/'head-placement.json').write_text(json.dumps({'scale':scale,'translation':translation.tolist(),
    'bodyCut':.318,'headCut':.328,'bodySectionVertices':len(body_loop),'headSectionVertices':len(head_loop),
    'triangles':len(sculpt.faces),'watertight':sculpt.is_watertight},indent=2)+'\n')
print('Assembled Sol',len(sculpt.faces),'triangles, head scale',scale,flush=True)
