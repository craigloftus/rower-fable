"""Join Kai's detailed original-reference head to the cleaned body at neck loops."""
from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.interpolate import PchipInterpolator
from trimesh.visual.material import PBRMaterial
from neck_join import clip,section_loops,bridge

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/kai'
body=trimesh.load(OUT/'faceted-surface.ply');head=trimesh.load(OUT/'head-refined-surface.ply')
material=PBRMaterial(name='Kai neutral sculpt',baseColorFactor=[145,126,100,255],metallicFactor=0,roughnessFactor=.9)
for mesh in (body,head):mesh.visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(mesh.vertices),2)),material=material)
scale=.142/(head.bounds[1,0]-head.bounds[0,0])
translation=np.array([0,.501-head.bounds[1,1]*scale,0.])
head.apply_scale(scale);head.apply_translation(translation)
body,body_edges=clip(body,.316,above=False)
head,head_edges=clip(head,.333,above=True)
body_loop=section_loops(body_edges)[0];head_loop=section_loops(head_edges)[0]
shift=body_loop[:,0].mean(axis=0)-head_loop[:,0].mean(axis=0);shift[1]=0
head.apply_translation(shift);head_loop[:,0]+=shift;translation+=shift
# The crop's base normals describe a flared cut, not an anatomical neck.
# Use a monotone bridge, then relax its exact welded boundary locally.
for loop in (body_loop,head_loop):loop[:,1,1]=0
neck=bridge(body_loop,head_loop)
sculpt=trimesh.util.concatenate([body,neck,head]);sculpt.merge_vertices(digits_vertex=7,merge_norm=True,merge_tex=True);sculpt.fix_normals()
p=sculpt.vertices.copy();x,y,z=p.T
def ramp(a,b,v):
 t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
# Fair the neck shaft across the joined source sections. The local ellipses
# follow its measured front/back bounds while narrowing the crop's flared base.
levels=[.290,.310,.333,.355,.380]
rx=PchipInterpolator(levels,[.057,.042,.035,.038,.048])(y)
rz=PchipInterpolator(levels,[.050,.041,.035,.037,.046])(y)
cz=PchipInterpolator(levels,[-.023,-.019,-.014,-.008,-.003])(y)
rx=np.maximum(rx,.02);rz=np.maximum(rz,.02)
angle=np.arctan2((z-cz)/rz,x/rx)
target=p.copy();target[:,0]=rx*np.cos(angle);target[:,2]=cz+rz*np.sin(angle)
w=ramp(.292,.310,y)*(1-ramp(.363,.385,y))
# Keep the projecting chin, mandibular edge and all facial anatomy.
w*=1-ramp(.026,.050,z)*ramp(.340,.353,y)
sculpt.vertices=p+(target-p)*w[:,None]
# Remove the densely sampled cut-loop ridge without moving the jaw silhouette.
relaxed=sculpt.copy();trimesh.smoothing.filter_taubin(relaxed,lamb=.45,nu=.50,iterations=30)
p=sculpt.vertices.copy();x,y,z=p.T
w=ramp(.300,.316,y)*(1-ramp(.335,.352,y))
sculpt.vertices=p+(relaxed.vertices-p)*w[:,None]
sculpt.fix_normals()
assert sculpt.is_watertight,'The assembled neck must close the body and head.'
sculpt.export(OUT/'assembled-surface.ply');sculpt.export(OUT/'assembled-neutral.glb')
(OUT/'head-placement.json').write_text(json.dumps({'scale':scale,'translation':translation.tolist(),
    'bodyCut':.316,'headCut':.333,'bodySectionVertices':len(body_loop),'headSectionVertices':len(head_loop),
    'triangles':len(sculpt.faces),'watertight':sculpt.is_watertight},indent=2)+'\n')
print('Assembled Kai',len(sculpt.faces),'triangles, head scale',scale,flush=True)
