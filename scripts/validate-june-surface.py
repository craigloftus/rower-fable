"""Check that the final sculpt preserves the approved guide's anatomy."""
from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/june-final'
body=trimesh.load(OUT/'faceted-surface.ply')
sculpt=trimesh.load(OUT/'sculpt-surface.ply')
guide=trimesh.load(OUT/'solid.ply')
assert body.is_watertight and body.is_winding_consistent
assert sculpt.is_watertight and sculpt.is_winding_consistent
finished=trimesh.load(OUT/'mesh.glb')
skin=finished.geometry['Skin'];p=skin.triangles_center
# The inner upper arms reach X=0.087 at this height. Keep this check inside
# the measured torso envelope so their exposed skin is not called a waist gap.
waist=(p[:,1]>.078)&(p[:,1]<.17)&(np.abs(p[:,0])<.080)&(skin.area_faces>1e-7)
assert not waist.any(),'The singlet/shorts pattern exposes the waist'
cloth=finished.geometry['Charcoal shorts'].triangles_center
assert not ((cloth[:,1]>.06)&(np.abs(cloth[:,0])>.105)).any(),'The shorts pattern reaches a forearm'

# Every source elbow point must still have skin over it after material cutting.
elbows=sculpt.vertices[(sculpt.vertices[:,1]>.06)&(sculpt.vertices[:,1]<.18)&(np.abs(sculpt.vertices[:,0])>.105)]
_,near=cKDTree(skin.triangles_center).query(elbows,k=24)
repeated=np.repeat(elbows,24,axis=0)
closest=trimesh.triangles.closest_point(skin.triangles[near].reshape(-1,3,3),repeated)
elbow_gap=np.linalg.norm(closest-repeated,axis=1).reshape(-1,24).min(axis=1).max()
assert elbow_gap<1e-6,f'The elbow skin has a gap: {elbow_gap}'

# Inspect actual exported albedo, independently of normals and scene lighting.
colors=skin.visual.vertex_attributes['color']
limbs=(skin.vertices[:,1]<-.10)|((skin.vertices[:,1]>.02)&(skin.vertices[:,1]<.23)&(np.abs(skin.vertices[:,0])>.085))
limb_colors=np.unique(colors[limbs],axis=0)
assert len(limb_colors)==1,'Light/shadow colours have been painted onto the arms or legs'
assert 'Eye glint' not in finished.geometry,'A painted eye highlight remains'
for name in ['Eye ivory','Iris','Pupil']:
    assert finished.geometry[name].visual.material.roughnessFactor<=.25,'Eyes need light-driven specular highlights'

# The central stripe's exposed edges must lie on its horizontal cut planes.
# The ends follow the singlet's armholes, so exclude those curved side edges.
stripe=finished.geometry['Cream stripe'].copy();stripe.merge_vertices(digits_vertex=6)
edges,count=np.unique(stripe.edges_sorted,axis=0,return_counts=True)
boundary=stripe.vertices[np.unique(edges[count==1])]
boundary=boundary[np.abs(boundary[:,0])<.06]
stripe_error=np.minimum(np.abs(boundary[:,1]-.200),np.abs(boundary[:,1]-.218)).max()
assert stripe_error<1e-6,f'The chest stripe edge is uneven: {stripe_error}'

sections=[]
for y in np.linspace(-.30,-.10,11):
    measurements=[]
    for mesh in [guide,body]:
        paths=mesh.section([0,1,0],[0,y,0]).discrete
        assert len(paths)==2,f'Expected two closed leg sections at {y}: {len(paths)}'
        paths.sort(key=lambda p:p[:,0].mean())
        measurements.append(np.array([np.ptp(p,axis=0)[[0,2]] for p in paths]))
    error=np.abs(measurements[1]-measurements[0])
    assert error.max()<.006,f'Leg silhouette changed at {y}: {error}'
    sections.append({'height':float(y),'maximumDiameterError':float(error.max())})

# Nearest surface points rather than vertex distance, which overstates error
# when a large clean triangle replaces many small source triangles.
np.random.seed(24)
samples,_=trimesh.sample.sample_surface(sculpt,16000)
source=trimesh.load(ROOT/'validation/reconstruction/trellis-assembled/mesh.glb')
source=trimesh.util.concatenate(list(source.geometry.values()))
tree=cKDTree(source.triangles_center)
_,ids=tree.query(samples,k=20)
closest=trimesh.triangles.closest_point(source.triangles[ids].reshape(-1,3,3),np.repeat(samples,20,axis=0))
distance=np.sqrt(np.sum((closest-np.repeat(samples,20,axis=0))**2,axis=1)).reshape(-1,20).min(axis=1)
report={'watertightBody':body.is_watertight,'watertightSculpt':sculpt.is_watertight,
    'sculptTriangles':len(sculpt.faces),'sourceTriangles':len(source.faces),
    'sourceDistance':{'median':float(np.median(distance)),'p95':float(np.percentile(distance,95)),'maximum':float(distance.max())},
    'legSections':sections,'elbowSkinMaximumGap':float(elbow_gap),
    'limbBaseColourCount':len(limb_colors),'stripeEdgeMaximumError':float(stripe_error),
    'paintedEyeHighlight':False}
(OUT/'geometry-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
